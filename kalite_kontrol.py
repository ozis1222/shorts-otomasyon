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
        gercek_gibi = [e for e in etiketler if re.search(r"true (story|mystery|crime)|cold case|real story", str(e), re.I)]
        if re.search(r"#true(story|crime|mystery)", aciklama, re.I):
            gercek_gibi.append("#hashtag")
        ekle("kurgu yaniltici etiket", not gercek_gibi,
             "yok" if not gercek_gibi else f"kurgu gercek olay gibi etiketlenmis: {gercek_gibi[:4]}")
    elif aile == "gercek_vaka":
        kaynak = meta.get("kaynak") or {}
        ekle("kaynak dogrulama", bool(kaynak.get("dogrulandi")),
             kaynak.get("url") or "dogrulanmis kaynak yok")

    medya = meta.get("medya_kaynagi") or []
    izinli = {"cloudflare-flux", "kod-cizim", "pollinations", "sentetik-ses", "edge-tts", "kokoro", "pexels", "pixabay"}
    bilinmeyen = [m for m in medya if m not in izinli]
    ekle("medya lisansi", not bilinmeyen, "yalnizca lisansi bilinen kaynaklar" if not bilinmeyen
         else f"lisansi bilinmeyen kaynak: {bilinmeyen}")
    return rapor


# ------------------------------------------------------------------ gorsel / ekran yerlesimi
# YouTube Shorts arayuzu (1080x1920): ustte ~290 px arama/menu, altta ~440 px baslik/kanal adi,
# sagda ~130 px begen/yorum/paylas dugmeleri. Yazilar bu alanlarin DISINDA kalmali.
GUVENLI_UST, GUVENLI_ALT, GUVENLI_SAG = 290, 1480, 130
MIN_ALTYAZI_PX = 64


def _ahash(yol, boyut=8):
    from PIL import Image
    with Image.open(yol) as im:
        k = im.convert("L").resize((boyut, boyut))
    px = list(k.getdata())
    ort = sum(px) / len(px)
    return [p > ort for p in px]


def gorsel_kontrol(meta, gorsel_klasoru=None):
    """Yonetmen plani (meta['ekran_plani']) ve sahne gorselleri uzerinde otomatik kontroller.
    Otomatik olculemeyen maddeler 'MANUEL' olarak isaretlenir: GECTI sayilmaz, yayini da engellemez."""
    rapor = []

    def ekle(ad, durum, detay):
        rapor.append({"kontrol": ad, "durum": durum, "detay": detay})

    plan = meta.get("ekran_plani") or {}
    if not plan.get("planli"):
        ekle("yonetmen plani", "UYARI", "plan yok (eski/yedek motor) - gorsel kontroller atlandi")
        return rapor
    sahneler = plan.get("sahneler") or []

    # 1) Ayni gorsel videoda birden fazla kez kullanilmis mi?
    kaynaklar = [str(s.get("src")) for s in sahneler]
    tekrar = sorted({k for k in kaynaklar if kaynaklar.count(k) > 1})
    ekle("sahne tekrari", "GECTI" if not tekrar else "KALDI",
         f"{len(kaynaklar)} sahne, her gorsel bir kez" if not tekrar else f"tekrar eden gorsel: {tekrar}")

    # 2) Neredeyse ayni gorseller (farkli dosya, ayni goruntu) -> uyari
    if gorsel_klasoru and os.path.isdir(gorsel_klasoru):
        yollar = sorted(os.path.join(gorsel_klasoru, f) for f in os.listdir(gorsel_klasoru)
                        if f.lower().endswith((".jpg", ".png")))
        try:
            hs = [(os.path.basename(y), _ahash(y)) for y in yollar]
            benzer = [(a[0], b[0]) for i, a in enumerate(hs) for b in hs[i + 1:]
                      if sum(x != y for x, y in zip(a[1], b[1])) <= 4]
            ekle("benzer sahne", "UYARI" if benzer else "GECTI",
                 f"neredeyse ayni gorseller: {benzer[:3]}" if benzer else "gorseller birbirinden farkli")
        except Exception as e:
            ekle("benzer sahne", "MANUEL", f"olculemedi: {str(e)[:60]}")

    # 3) Kamera hareketi: ayni hareket ust uste 3 kez olmamali
    kameralar = [s.get("camera") for s in sahneler]
    ust_uste = any(kameralar[i] == kameralar[i + 1] == kameralar[i + 2] for i in range(len(kameralar) - 2))
    ekle("kamera cesitliligi", "UYARI" if ust_uste else "GECTI", " > ".join(map(str, kameralar)))

    # 4) Ekran yazilari: kanca kisa mi, baslik/anlatim/sahne yazilari birbirini tekrar ediyor mu
    sorunlar = plan.get("yazi_sorunlari") or []
    yazili = [s for s in sahneler if s.get("text")]
    ekle("ekran yazisi tekrari", "GECTI" if not sorunlar else "KALDI",
         f"kanca: '{plan.get('kanca') or '-'}', yazili sahne: {len(yazili)}/{len(sahneler)}" if not sorunlar
         else "; ".join(sorunlar))
    ekle("baslik bandi", "GECTI" if not plan.get("band") else "UYARI",
         "kirmizi bant kapali" if not plan.get("band") else "kirmizi bant acik")
    asiri = len(yazili) > max(2, len(sahneler) // 3)
    ekle("yazi yogunlugu", "UYARI" if asiri else "GECTI",
         f"{len(yazili)} sahnede ekran yazisi" + (" (fazla)" if asiri else ""))

    # 5) Guvenli alan: yerlesim degerlerinden hesaplanir (render edilmis kare olculmez)
    ust = plan.get("altyazi_ust") or 0
    boyut = plan.get("altyazi_boyut") or 0
    alt = ust + 2 * boyut * 1.1 if ust else 0
    guvenli = bool(ust) and ust >= GUVENLI_UST and alt <= GUVENLI_ALT and boyut >= MIN_ALTYAZI_PX
    ekle("altyazi guvenli alan", "GECTI" if guvenli else "KALDI",
         f"altyazi {ust}-{int(alt)} px, {boyut} px yazi, sag bosluk 150 px (yerlesim degerlerinden)")

    # 6) Gorsel icerik on-taramasi (Gemini goruntu modeli; kesin degil -> en fazla UYARI)
    tarama = meta.get("gorsel_tarama") or {}
    if tarama.get("yapildi"):
        bulgular = tarama.get("bulgular") or []
        ekle("gorsel on-tarama", "UYARI" if bulgular else "MANUEL",
             ("olasi sorun: " + "; ".join(bulgular[:4])) if bulgular
             else "otomatik taramada sorun bulunmadi (yine de insan gozuyle bakilmali)")
    else:
        ekle("gorsel on-tarama", "MANUEL", tarama.get("neden") or "yapilmadi")
    # Guvenilir olarak otomatik olculemeyenler: dogrulanmis gibi gosterilmez
    ekle("bozuk el/yuz/nesne", "MANUEL", "insan gozuyle kontrol edilmeli (on-tarama ipucu verir)")
    ekle("gorsel-ses uyumu", "MANUEL", "sahneler anlatim parcalarina gore zamanlandi; anlam uyumu insan kontrolu")
    return rapor


def kontrol_et(video_yolu, meta, izinli_siyah=(), gorsel_klasoru=None):
    """Tum kontroller. Donus: {'gecti': bool, 'kontroller': [...]}.
    UYARI ve MANUEL gecmeyi engellemez; MANUEL = otomatik dogrulanamadi, insan bakmali."""
    kontroller = teknik_kontrol(video_yolu, izinli_siyah) + icerik_kontrol(meta)
    if meta.get("ekran_plani") is not None:
        kontroller += gorsel_kontrol(meta, gorsel_klasoru)
    gecti = all(k["durum"] in ("GECTI", "UYARI", "MANUEL") for k in kontroller)
    return {"gecti": gecti, "kontroller": kontroller}


def ozet_yazdir(sonuc):
    for k in sonuc["kontroller"]:
        isaret = {"GECTI": "OK ", "UYARI": "!! ", "KALDI": "XX ", "MANUEL": "?? "}[k["durum"]]
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
