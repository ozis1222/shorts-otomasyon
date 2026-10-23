# -*- coding: utf-8 -*-
"""
Otomatik kalite kontrolu. Her madde GECTI / UYARI / KALDI olarak raporlanir.
Gorsel olarak olculemeyen seyler (ornegin 'hareket dogal mi') burada GECTI sayilmaz;
rapor bunu acikca 'insan kontrolu gerekir' diye belirtir.
"""
import json
import math
import re
import subprocess

from .render import ffmpeg_yolu

SICRAMA_ESIGI = 55.0   # px/kare (30 fps'e gore); kok hareketinden bagimsiz uzuv sicramasi


def _ffprobe(video):
    ff = ffmpeg_yolu()
    probe = ff.replace("ffmpeg", "ffprobe") if "ffmpeg" in ff else "ffprobe"
    try:
        cikti = subprocess.run([probe, "-v", "error", "-show_streams", "-show_format", "-of", "json", video],
                               capture_output=True, text=True, check=True).stdout
        return json.loads(cikti)
    except Exception:
        # imageio-ffmpeg ffprobe getirmez: ffmpeg -i ciktisindan ayikla
        r = subprocess.run([ff, "-hide_banner", "-i", video], capture_output=True, text=True)
        txt = r.stderr
        sure = re.search(r"Duration: (\d+):(\d+):([\d.]+)", txt)
        v = re.search(r"Video: (\w+).*?, (\d+)x(\d+).*?, ([\d.]+) fps", txt)
        a = re.search(r"Audio: (\w+)", txt)
        akis = []
        if v:
            akis.append({"codec_type": "video", "codec_name": v.group(1), "width": int(v.group(2)),
                         "height": int(v.group(3)), "r_frame_rate": f"{v.group(4)}/1"})
        if a:
            akis.append({"codec_type": "audio", "codec_name": a.group(1)})
        s = int(sure.group(1)) * 3600 + int(sure.group(2)) * 60 + float(sure.group(3)) if sure else 0
        return {"streams": akis, "format": {"duration": str(s)}}


def _siyah_kareler(video):
    r = subprocess.run([ffmpeg_yolu(), "-hide_banner", "-i", video, "-vf", "blackdetect=d=0.15:pix_th=0.06",
                        "-an", "-f", "null", "-"], capture_output=True, text=True)
    return [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)]


def _ses_seviyesi(video):
    r = subprocess.run([ffmpeg_yolu(), "-hide_banner", "-i", video, "-vn", "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"mean_volume: (-?[\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else None


def kontrol(video, beklenen_sure, fps, cozunurluk, olcumler, sahneler, ses_olaylari, izinli_siyah=()):
    rapor = []

    def ekle(ad, durum, detay):
        rapor.append({"kontrol": ad, "durum": durum, "detay": detay})

    import os
    if not os.path.exists(video) or os.path.getsize(video) < 10_000:
        ekle("dosya", "KALDI", "video dosyasi olusmadi veya bos")
        return rapor
    ekle("dosya", "GECTI", f"{os.path.getsize(video) / 1e6:.1f} MB")

    bilgi = _ffprobe(video)
    vs = [s for s in bilgi["streams"] if s.get("codec_type") == "video"]
    aus = [s for s in bilgi["streams"] if s.get("codec_type") == "audio"]
    sure = float(bilgi["format"].get("duration", 0))
    ekle("sure", "GECTI" if abs(sure - beklenen_sure) < 0.15 else "KALDI",
         f"{sure:.2f} sn (beklenen {beklenen_sure:.2f})")
    if vs:
        v = vs[0]
        num, den = (v.get("r_frame_rate", "0/1").split("/") + ["1"])[:2]
        gercek_fps = float(num) / float(den or 1)
        ekle("fps", "GECTI" if abs(gercek_fps - fps) < 0.5 else "KALDI", f"{gercek_fps:.2f}")
        cz = (v.get("width"), v.get("height"))
        ekle("cozunurluk", "GECTI" if cz == cozunurluk else "KALDI", f"{cz[0]}x{cz[1]}")
        ekle("video codec", "GECTI" if v.get("codec_name") == "h264" else "KALDI", v.get("codec_name"))
    else:
        ekle("video akisi", "KALDI", "video akisi yok")
    if aus:
        sv = _ses_seviyesi(video)
        ekle("ses", "GECTI" if (aus[0].get("codec_name") == "aac" and sv is not None and sv > -45) else "KALDI",
             f"{aus[0].get('codec_name')}, ortalama {sv} dB")
    else:
        ekle("ses", "KALDI", "ses akisi yok")

    siyah = _siyah_kareler(video)
    beklenmeyen = [s for s in siyah if not any(a - 0.2 <= s[0] and s[1] <= b + 0.2 for a, b in izinli_siyah)]
    ekle("siyah kare", "GECTI" if not beklenmeyen else "KALDI",
         f"izinli (kararma) {len(siyah) - len(beklenmeyen)}, beklenmeyen {beklenmeyen}")

    # --- iskelet / kare analizleri (render sirasinda toplanan olcumler)
    en_kemik = 0.0
    sicramalar, kafa_kesik = [], []
    onceki = None
    olcek_fps = 30.0 / fps
    for o in olcumler:
        for ad, k in o["kalite"].items():
            en_kemik = max(en_kemik, k["kemik_hata"])
            x0, y0, x1, y1 = k["ekran_kutu"]
            if y0 < -20 and x1 > 0 and x0 < 1080:
                kafa_kesik.append((round(o["t"], 2), ad))
            if onceki and onceki["sahne"] == o["sahne"] and ad in onceki["kalite"]:
                ok = onceki["kalite"][ad]
                if ok["yon"] == k["yon"]:
                    dk = (k["kok"][0] - ok["kok"][0], k["kok"][1] - ok["kok"][1])
                    for e, p in k["eklem"].items():
                        q = ok["eklem"][e]
                        goreli = math.hypot(p[0] - q[0] - dk[0], p[1] - q[1] - dk[1]) * olcek_fps
                        if goreli > SICRAMA_ESIGI:
                            sicramalar.append((round(o["t"], 2), ad, e, round(goreli)))
        onceki = o
    ekle("uzuv baglantisi", "GECTI" if en_kemik < 0.5 else "KALDI", f"en buyuk kemik uzunluk sapmasi {en_kemik:.3f} px")
    ekle("ani uzuv sicramasi", "GECTI" if not sicramalar else "UYARI",
         f"{len(sicramalar)} kare" + (f", ilk ornekler: {sicramalar[:6]}" if sicramalar else ""))
    ekle("kafa ekran disi", "GECTI" if not kafa_kesik else "UYARI",
         f"{len(kafa_kesik)} kare" + (f": {kafa_kesik[:5]}" if kafa_kesik else ""))

    # --- diyalog / olay senkronu (senaryo tutarliligi)
    uyumsuz = []
    t_bas = 0.0
    for s in sahneler:
        for t0, t1, ad, metin in s.get("balonlar", []):
            iz = next((kd["iz"] for kd in s["karakterler"] if kd["karakter"].ad == ad), None)
            konusuyor = iz and any(a["hareket"] in ("konus", "isaret", "kos", "kork", "geri_cekil") and a["t0"] <= t1 and a["t1"] >= t0
                                   for a in iz.a)
            if not konusuyor:
                uyumsuz.append(f"{ad}: '{metin}'")
        for ad, ses_t, gorsel_t in s.get("eslesmeler", []):
            if abs(ses_t - gorsel_t) > 0.1:
                uyumsuz.append(f"{ad}: ses {ses_t:.2f} / goruntu {gorsel_t:.2f}")
        t_bas += s["sure"]
    disarida = [o for o in ses_olaylari if o[0] < 0 or o[0] > beklenen_sure]
    ekle("diyalog/olay senkronu", "GECTI" if not uyumsuz and not disarida else "KALDI",
         "uyumlu" if not uyumsuz and not disarida else f"uyumsuz: {uyumsuz} {disarida}")
    ekle("gorsel degerlendirme", "INSAN", "hareketlerin dogalligi ve sahne okunurlugu otomatik olculemez: "
         "onizleme videolarini izleyin")
    return rapor


def ozet(rapor):
    sayac = {}
    for r in rapor:
        sayac[r["durum"]] = sayac.get(r["durum"], 0) + 1
    return sayac
