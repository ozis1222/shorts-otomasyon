# -*- coding: utf-8 -*-
"""
YAYIN ONCESI KALITE + UYGUNLUK KONTROLU

Uretilen her video bu kontrollerden GECMEDEN yayin paketine "gecti" yazilmaz ve
yayinla.py onu yuklemez. Her madde ayri raporlanir; olculemeyen bir sey GECTI sayilmaz.

Teknik kontroller (FFmpeg ile, dosyanin kendisi uzerinde):
  - dosya var ve bos degil, bastan sona hatasiz cozulebiliyor (oynatilabilir)
  - sure Shorts sinirlari icinde, 1080x1920 dikey, H.264 + AAC
  - ses akisi var ve sessiz degil
  - beklenmeyen siyah/bos kare yok
Icerik / politika kontrolleri (metadata uzerinde):
  - baslik / aciklama uzunlugu, spam etiket ve tekrar eden anahtar kelime
  - kurgu hikayelerde "kurgu" etiketi var (gercek olay gibi sunulmaz)
  - gercek vakalarda dogrulanmis kaynak var
  - yalnizca lisansi bilinen (sentetik / kendi uretimimiz) medya kullanildi

Calistirma:  python kalite_kontrol.py video.mp4 meta.json
"""
import json
import os
import re
import subprocess
import sys

SHORTS_MIN_SN = 15.0
SHORTS_MAX_SN = 60.0     # YouTube Shorts 3 dk'ya kadar izin veriyor; kanal hedefi 35-60 sn
HEDEF_BOYUT = (1080, 1920)
SESSIZ_DB = -45.0        # ortalama ses seviyesi bunun altindaysa "sessiz video"


def ffmpeg_yolu():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _calistir(args, zaman_asimi=300):
    return subprocess.run([ffmpeg_yolu(), "-hide_banner", *args], capture_output=True, text=True,
                          timeout=zaman_asimi)


def video_bilgisi(yol):
    """ffprobe olmadan (imageio-ffmpeg getirmez) ffmpeg -i ciktisindan akis bilgisi."""
    r = _calistir(["-i", yol], 60)
    txt = r.stderr
    bilgi = {"sure": None, "video": None, "ses": None}
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", txt)
    if m:
        bilgi["sure"] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    v = re.search(r"Stream #\S+.*?Video: (\w+)[^\n]*?, (\d{2,5})x(\d{2,5})[^\n]*?, ([\d.]+) fps", txt)
    if v:
        bilgi["video"] = {"codec": v.group(1), "boyut": (int(v.group(2)), int(v.group(3))), "fps": float(v.group(4))}
    a = re.search(r"Stream #\S+.*?Audio: (\w+)", txt)
    if a:
        bilgi["ses"] = {"codec": a.group(1)}
    return bilgi


def _siyah_araliklar(yol):
    r = _calistir(["-i", yol, "-vf", "blackdetect=d=0.25:pix_th=0.06", "-an", "-f", "null", "-"])
    return [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)]


def _ortalama_ses(yol):
    r = _calistir(["-i", yol, "-vn", "-af", "volumedetect", "-f", "null", "-"])
    m = re.search(r"mean_volume: (-?[\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else None


def _cozulebilir(yol):
    """Tum dosyayi cozer; bozuk paket / kesik dosya hata olarak doner."""
    r = _calistir(["-v", "error", "-i", yol, "-f", "null", "-"], 600)
    hatalar = [s for s in r.stderr.splitlines() if s.strip()]
    return r.returncode == 0 and not hatalar, hatalar[:3]


def teknik_kontrol(yol, izinli_siyah=()):
    """Video dosyasi uzerinde teknik kontroller. Donus: [{kontrol, durum, detay}]"""
    rapor = []

    def ekle(ad, gecti, detay):
        rapor.append({"kontrol": ad, "durum": "GECTI" if gecti else "KALDI", "detay": detay})

    if not yol or not os.path.exists(yol) or os.path.getsize(yol) < 50_000:
        ekle("dosya", False, "video dosyasi yok ya da bos")
        return rapor
    ekle("dosya", True, f"{os.path.getsize(yol) / 1e6:.1f} MB")

    ok, hatalar = _cozulebilir(yol)
    ekle("oynatilabilir", ok, "bastan sona hatasiz cozuldu" if ok else f"cozme hatasi: {hatalar}")

    b = video_bilgisi(yol)
    sure = b["sure"] or 0
    ekle("sure", SHORTS_MIN_SN <= sure <= SHORTS_MAX_SN, f"{sure:.1f} sn (izinli {SHORTS_MIN_SN:.0f}-{SHORTS_MAX_SN:.0f})")
    v = b["video"]
    ekle("cozunurluk", bool(v) and v["boyut"] == HEDEF_BOYUT, f"{v['boyut'][0]}x{v['boyut'][1]}" if v else "video akisi yok")
    ekle("video codec", bool(v) and v["codec"] == "h264", v["codec"] if v else "-")
    ekle("ses akisi", bool(b["ses"]) and b["ses"]["codec"] == "aac", b["ses"]["codec"] if b["ses"] else "ses yok")
    if b["ses"]:
        db = _ortalama_ses(yol)
        ekle("ses seviyesi", db is not None and db > SESSIZ_DB, f"ortalama {db} dB")

    siyah = _siyah_araliklar(yol)
    beklenmeyen = [s for s in siyah if not any(a - 0.2 <= s[0] and s[1] <= b2 + 0.2 for a, b2 in izinli_siyah)]
    ekle("siyah/bos kare", not beklenmeyen, "yok" if not beklenmeyen else f"siyah araliklar: {beklenmeyen[:4]}")
    return rapor


# ------------------------------------------------------------------ icerik / politika
_SPAM_ETIKET = re.compile(r"(sub4sub|subscribe for subscribe|free money|giveaway|xxx)", re.I)


def icerik_kontrol(meta):
    """Baslik/aciklama/etiket ve politika kontrolleri (meta: yayin paketi sozlugu)."""
    rapor = []

    def ekle(ad, gecti, detay, uyari=False):
        durum = "GECTI" if gecti else ("UYARI" if uyari else "KALDI")
        rapor.append({"kontrol": ad, "durum": durum, "detay": detay})

    baslik = (meta.get("baslik") or "").strip()
    aciklama = (meta.get("aciklama") or "").strip()
    etiketler = meta.get("etiketler") or []
    ekle("baslik", 10 <= len(baslik) <= 100, f"{len(baslik)} karakter")
    ekle("aciklama", 40 <= len(aciklama) <= 4900, f"{len(aciklama)} karakter")

    # Ayni kelimenin aciklamada asiri tekrari (anahtar kelime doldurma)
    kelimeler = [k for k in re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]{4,}", aciklama.lower())]
    en_cok = max((kelimeler.count(k) for k in set(kelimeler)), default=0)
    ekle("anahtar kelime doldurma", en_cok <= 6, f"en sik kelime {en_cok} kez")
    hashtag = len(re.findall(r"#\w+", aciklama))
    ekle("hashtag sayisi", hashtag <= 15, f"{hashtag} hashtag (YouTube 15 ustunu yok sayar)")
    ekle("spam etiket", not any(_SPAM_ETIKET.search(str(e)) for e in etiketler) and len(etiketler) <= 30,
         f"{len(etiketler)} etiket")

    aile = meta.get("aile")
    if aile in ("hayatta_kalma", "ozgun_korku"):
        # Kurgu, gercek olay gibi sunulamaz
        etiketli = "kurgu" in aciklama.lower() or "fiction" in aciklama.lower()
        ekle("kurgu etiketi", etiketli, "aciklamada kurgu oldugu belirtiliyor" if etiketli else "kurgu etiketi YOK")
    elif aile == "gercek_vaka":
        kaynak = meta.get("kaynak") or {}
        ekle("kaynak dogrulama", bool(kaynak.get("dogrulandi")),
             kaynak.get("url") or "dogrulanmis kaynak yok")

    medya = meta.get("medya_kaynagi") or []
    izinli = {"cloudflare-flux", "kod-cizim", "pollinations", "sentetik-ses", "edge-tts", "pexels", "pixabay"}
    bilinmeyen = [m for m in medya if m not in izinli]
    ekle("medya lisansi", not bilinmeyen, "yalnizca lisansi bilinen kaynaklar" if not bilinmeyen
         else f"lisansi bilinmeyen kaynak: {bilinmeyen}")
    return rapor


def kontrol_et(video_yolu, meta, izinli_siyah=()):
    """Tum kontroller. Donus: {'gecti': bool, 'kontroller': [...]} (UYARI gecmeyi engellemez)."""
    kontroller = teknik_kontrol(video_yolu, izinli_siyah) + icerik_kontrol(meta)
    gecti = all(k["durum"] in ("GECTI", "UYARI") for k in kontroller)
    return {"gecti": gecti, "kontroller": kontroller}


def ozet_yazdir(sonuc):
    for k in sonuc["kontroller"]:
        isaret = {"GECTI": "OK ", "UYARI": "!! ", "KALDI": "XX "}[k["durum"]]
        print(f"   {isaret} {k['kontrol']:<24} {k['detay']}")
    print("   SONUC:", "GECTI" if sonuc["gecti"] else "KALDI (yayinlanmayacak)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("kullanim: python kalite_kontrol.py video.mp4 meta.json")
        sys.exit(2)
    with open(sys.argv[2], encoding="utf-8") as f:
        m = json.load(f)
    s = kontrol_et(sys.argv[1], m)
    ozet_yazdir(s)
    sys.exit(0 if s["gecti"] else 1)
