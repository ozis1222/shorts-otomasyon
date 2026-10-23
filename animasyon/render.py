# -*- coding: utf-8 -*-
"""
Kare uretimi ve video kodlama.

Her kare icin zaman t = kare / fps hesaplanir; tum hareketler t'nin fonksiyonudur ->
islemci hizi ve FPS ne olursa olsun ayni zamanlama. Kareler sikistirilmadan (BGRA) dogrudan
FFmpeg'e borulanir (diskte kare dosyasi birikmez). Render sirasinda kalite verisi toplanir:
kemik uzunlugu sapmasi, uzuv sicramasi, ekran disi kalma, adim anlari (ses efektleri icin).
"""
import logging
import math
import os
import subprocess

import skia

from . import efekt
from . import kamera as kam
from .iskelet import kemik_hatasi, kinematik
from .karakter import ciz as karakter_ciz
from .karakter import golge, sinir_kutusu
from .temel import H, W, kis

log = logging.getLogger("animasyon")

EKLEMLER = ("kafa", "el_on", "el_arka", "dirsek_on", "dirsek_arka", "diz_on", "diz_arka", "bilek_on", "bilek_arka")


def ffmpeg_yolu():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _z(deger, t):
    """z sabit sayi ya da [(t, z), ...] olabilir (karakter kapinin arkasindan one gecer)."""
    if isinstance(deger, (int, float)):
        return deger
    z = deger[0][1]
    for t0, zz in deger:
        if t >= t0:
            z = zz
    return z


def _ekran(nokta, durum):
    x, y, z, _ = durum
    return ((nokta[0] - x) * z + kam.MERKEZ[0], (nokta[1] - y) * z + kam.MERKEZ[1])


def sahne_ciz(c, sahne, t, kalite=None, onceki=None):
    """Tek bir sahne karesini cizer. kalite: bu kare icin olcumlerin yazilacagi sozluk."""
    durum = sahne["kamera"].durum(t)
    ortam = sahne["ortam"]
    zemin = ortam.zemin_y
    ogeler = [(z, p, fn) for z, p, fn in ortam.katmanlar()]
    karakter_durum = {}
    for kd in sahne["karakterler"]:
        if t < kd.get("giris", -1) or t > kd.get("cikis", 1e9):
            continue
        poz, x, yon, adim = kd["iz"].durum(t)
        n = kinematik(poz, x, zemin, yon, kd["karakter"].olcek)
        hareket_ad = kd["iz"].a[adim[0]]["hareket"] if kd["iz"].a else "bekle"
        karakter_durum[kd["karakter"].ad] = (poz, n, yon, adim, hareket_ad)

        def _ciz(cv, tt, kd=kd, poz=poz, n=n):
            golge(cv, n, zemin, poz)
            karakter_ciz(cv, kd["karakter"], n, poz, tt)
        ogeler.append((_z(kd.get("z", 10), t), 1.0, _ciz))

    gecis_bulanik = 0.0
    g_cikis = sahne.get("gecis_cikis")
    if g_cikis and t > sahne["sure"] - g_cikis:
        gecis_bulanik = kis((t - (sahne["sure"] - g_cikis)) / g_cikis)
    g_giris = sahne.get("gecis_giris")
    if g_giris and t < g_giris:
        gecis_bulanik = max(gecis_bulanik, 1 - kis(t / g_giris))

    if gecis_bulanik > 0.01:
        # hizli kamera savrulmasi hissi: yatay hareket bulanikligi
        f = skia.ImageFilters.Blur(60 * gecis_bulanik, 4 * gecis_bulanik)
        c.saveLayer(paint=skia.Paint(ImageFilter=f))
    for z, p, fn in sorted(ogeler, key=lambda o: o[0]):
        c.save()
        kam.uygula(c, durum, p)
        fn(c, t)
        c.restore()
    if gecis_bulanik > 0.01:
        c.restore()

    ef = sahne.get("efektler", {})
    if ef.get("toz"):
        efekt.parcaciklar(c, t, 36, "#ffe9c4", alfa=90, tohum=1)
    if ef.get("kul"):
        efekt.parcaciklar(c, t, 60, "#c9c2b8", yukari=False, alfa=120, tohum=2)
    if ef.get("renk"):
        efekt.renk_ortu(c, *ef["renk"])
    efekt.vinyet(c, ef.get("vinyet", 0.7))

    for t0, sure in sahne.get("flas", []):
        if t0 <= t <= t0 + sure:
            efekt.flas(c, 0.85 * (1 - (t - t0) / sure))

    # Konusma balonlari: konusan karakterin kafasinin ustunde (ekran uzayinda)
    for t0, t1, ad, metin in sahne.get("balonlar", []):
        if t0 <= t <= t1 and ad in karakter_durum:
            _, n, yon, _, _ = karakter_durum[ad]
            hx, hy = _ekran(n["kafa"], durum)
            efekt.konusma_balonu(c, hx + 60 * yon, hy - 150 * durum[2], metin, (t - t0) / 0.6,
                                 boyut=62, sol_kuyruk=yon > 0)

    for t0, t1, metin, y in sahne.get("yazilar", []):
        if t0 <= t <= t1:
            a = kis((t - t0) / 0.25) * kis((t1 - t) / 0.25)
            efekt.baslik(c, metin, y, 130, alfa=int(255 * a))

    for t0, t1, a0, a1 in sahne.get("kararma", []):
        if t0 <= t <= t1:
            efekt.kararma(c, a0 + (a1 - a0) * kis((t - t0) / max(1e-6, t1 - t0)))
        elif t > t1 and a1 >= 1:
            efekt.kararma(c, 1.0)

    # --- kalite olcumleri
    if kalite is not None:
        for ad, (poz, n, yon, adim, hareket_ad) in karakter_durum.items():
            k = kalite.setdefault(ad, {})
            k["kemik_hata"] = kemik_hatasi(n)
            x0, y0, x1, y1 = sinir_kutusu(n)
            a0, b0 = _ekran((x0, y0), durum)
            a1, b1 = _ekran((x1, y1), durum)
            k["ekran_kutu"] = (a0, b0, a1, b1)
            k["eklem"] = {e: _ekran(n[e], durum) for e in EKLEMLER}
            k["kok"] = _ekran(n["kalca"], durum)
            k["yon"] = yon
            k["adim"] = adim
            k["hareket"] = hareket_ad
    return karakter_durum


def video_render(sahneler, cikis_mp4, fps=30, olcek=1.0, ilerleme=None):
    """
    Sahneleri sirayla render eder, sessiz MP4 yazar.
    Donus: (olcum_listesi, adim_olaylari)  — olcum: kare bazinda kalite verisi.
    """
    gen, yuk = int(W * olcek) // 2 * 2, int(H * olcek) // 2 * 2
    komut = [ffmpeg_yolu(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
             "-s", f"{gen}x{yuk}", "-r", str(fps), "-i", "-",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18" if olcek >= 1 else "24",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", cikis_mp4]
    surec = subprocess.Popen(komut, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    yuzey = skia.Surface(gen, yuk)
    c = yuzey.getCanvas()
    olcumler, adimlar = [], []
    t_bas = 0.0
    kare_no = 0
    try:
        for si, sahne in enumerate(sahneler):
            kare_sayisi = int(round(sahne["sure"] * fps))
            onceki_adim = {}
            for i in range(kare_sayisi):
                t = i / fps
                c.clear(skia.ColorBLACK)
                c.save()
                c.scale(gen / W, yuk / H)
                kalite = {}
                sahne_ciz(c, sahne, t, kalite)
                c.restore()
                piksel = yuzey.makeImageSnapshot().toarray()
                surec.stdin.write(piksel.tobytes())
                # adim sesleri: iskeletin adim sayaci degistiginde
                for ad, k in kalite.items():
                    a = k.get("adim")
                    if a and a[1] >= 0 and onceki_adim.get(ad) not in (None, a) and onceki_adim[ad][0] == a[0]:
                        sert = {"kos": 1.3, "zombi_yuru": 0.8, "geri_cekil": 0.7}.get(k.get("hareket"), 0.9)
                        adimlar.append((t_bas + t, ad, sert))
                    onceki_adim[ad] = a
                olcumler.append({"t": t_bas + t, "sahne": si, "kare": i, "kalite": kalite})
                kare_no += 1
                if ilerleme and kare_no % 30 == 0:
                    ilerleme(kare_no)
            t_bas += kare_sayisi / fps
        surec.stdin.close()
        hata = surec.stderr.read().decode("utf-8", "ignore")
        if surec.wait() != 0:
            raise RuntimeError("FFmpeg kodlama hatasi: " + hata[-400:])
    except Exception:
        surec.kill()
        raise
    return olcumler, adimlar


def ses_ekle(video, wav, cikis):
    komut = [ffmpeg_yolu(), "-y", "-loglevel", "error", "-i", video, "-i", wav, "-map", "0:v", "-map", "1:a",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", cikis]
    subprocess.run(komut, check=True)


def toplam_sure(sahneler, fps):
    return sum(int(round(s["sure"] * fps)) for s in sahneler) / fps
