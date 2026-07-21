# -*- coding: utf-8 -*-
"""
===================================================================
   TAM OTOMATİK YOUTUBE SHORTS OTOMASYONU
   Niş: Unsolved Mysteries & Creepy Facts (İngilizce / küresel)
===================================================================
Akış (hepsi otomatik):
  1) İçerik üretimi (Gemini, ÜCRETSİZ) -> konu + senaryo + başlık + açıklama + etiket
  2) Seslendirme (edge-tts, ÜCRETSİZ)  -> ses.mp3 (İngilizce doğal erkek ses)
  3) Kurgu + sarı altyazı (MoviePy)    -> shorts_hazir.mp4
  4) YouTube'a "Gizli" yükleme         -> YouTube Data API v3

Sen sadece çalıştırırsın. Konuyu, senaryoyu, başlığı sistem kendi bulur.
edge-tts her kelimenin zamanını verdiği için altyazılar sesle BİREBİR senkron olur.
===================================================================
"""

import os
import sys
import glob
import json
import random
import shutil
import asyncio
import urllib.parse
import urllib.request

import edge_tts
import numpy as np
from moviepy import (
    VideoFileClip,
    VideoClip,
    ImageClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
)

from google import genai
from google.genai import types

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# ==================================================================
#  AYARLAR  ->  BURAYI KENDİNE GÖRE DÜZENLE
# ==================================================================

# --- 1) GEMINI (senaryo üreten ücretsiz yapay zeka) ---

# Ücretsiz API anahtarını buradan al: https://aistudio.google.com/apikey
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or "AQ.Ab8RN6IE55HA57S9m5hpM42Iyr_Ct0_b6n2z5wSWGQ2dhr5x-Q"

# "auto" = kod, senin hesabında ÇALIŞAN en güncel Gemini modelini kendi bulur.
# İstersen elle bir model adı da yazabilirsin (örn. "gemini-2.0-flash").
GEMINI_MODEL = "auto"

# İSTERSEN belirli bir konu zorla (örn. "The Dyatlov Pass incident").
# Boş bırakırsan sistem niş içinde her seferinde farklı bir konu seçer.
KONU_IPUCU = ""


# --- 1b) GÖRSELLER (konuya uygun fotoğraflar) ---

# Sistem şu SIRAYLA dener: PIXABAY -> PEXELS -> OPENVERSE (anahtarsız).
# İkisini de boş bıraksan bile Openverse ANAHTAR İSTEMEDEN çalışır, görsel gelir.

# Pixabay ücretsiz anahtar: https://pixabay.com/api/docs/
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY") or "56752910-1e70a403809949c23e6637cf1"

# Pexels ücretsiz anahtar (isteğe bağlı): https://www.pexels.com/api/
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY") or ""


# --- 2) Klasör ve dosya yolları ---

# Telifsiz arka plan (stok) videolarının bulunduğu klasör.
# Gizem nişi için karanlık/atmosferik, sisli, gece, uzay gibi fonlar iyi durur.
STOK_VIDEO_KLASORU = r"C:\Users\Ozan\Desktop\ozzan\stok_videolar"

# Altyazıda kullanılacak KALIN font dosyası (yol bilgisayarına göre değişir).
#   Windows (Arial Bold):  C:\Windows\Fonts\arialbd.ttf
#   Mac    (Arial Bold) :  /System/Library/Fonts/Supplemental/Arial Bold.ttf
FONT_PATH = r"C:\Windows\Fonts\arialbd.ttf"


# --- 3) Seslendirme ayarları (İngilizce erkek ses) ---

# Gizem nişine yakışan derin/ölçülü İngilizce erkek sesleri:
#   "en-US-ChristopherNeural"  (derin, otoriter - önerilir)
#   "en-US-GuyNeural"          (doğal, dengeli)
#   "en-US-BrianNeural"        (sıcak, anlatıcı)
#   "en-US-EricNeural" / "en-US-AndrewNeural"
SES = "en-US-ChristopherNeural"

SES_DOSYASI = "ses.mp3"           # üretilecek ses dosyası
CIKTI_VIDEO = "shorts_hazir.mp4"  # üretilecek nihai video


# --- 4) Altyazı görünümü ---

HER_EKRANDA_KELIME = 3   # her altyazıda kaç kelime görünsün (2 veya 3 önerilir)
YAZI_BOYUTU = 90         # altyazı punto
YAZI_RENGI = "yellow"    # altyazı rengi (sarı)
KENARLIK_RENGI = "black" # yazının etrafındaki kenarlık (okunurluk için)
KENARLIK_KALINLIGI = 6

# Altyazının dikey konumu (0.0 = en üst, 1.0 = en alt). Viral tarz için ~0.72 idealdir.
ALTYAZI_DIKEY = 0.72


# --- 5) Video boyutu (Shorts = dikey 9:16) ---

HEDEF_GENISLIK = 1080
HEDEF_YUKSEKLIK = 1920


# --- 6) YouTube ayarı ---

# 24 = Entertainment (gizem/hikâye için uygun). Alternatif: 27=Education, 22=People & Blogs
YOUTUBE_KATEGORI = "24"


# ==================================================================
#  ADIM 1: İÇERİK ÜRETİMİ (Gemini)
# ==================================================================

# Niş içinde çeşitlilik için farklı açılar. Her çalıştırmada biri seçilir,
# böylece videolar birbirinin kopyası olmaz.
ACILAR = [
    "a mysterious disappearance that was never solved",
    "an unexplained sound, signal, or transmission",
    "an eerie abandoned place with a strange history",
    "a baffling historical event with no clear explanation",
    "a strange artifact or object that shouldn't exist",
    "an unsettling deep-sea or ocean mystery",
    "a chilling unsolved case from the past",
    "a bizarre coincidence that still puzzles experts",
    "a declassified or once-secret file",
    "an unexplained natural phenomenon",
    "a creepy fact about the human body or mind",
    "a lost civilization or vanished group of people",
]


def _model_sec(client):
    """Hesabında ÇALIŞAN, içerik üretebilen bir Gemini modeli seçer ('auto' için)."""
    mevcut = []
    for m in client.models.list():
        eylemler = (getattr(m, "supported_actions", None)
                    or getattr(m, "supported_generation_methods", None) or [])
        if eylemler and "generateContent" not in eylemler:
            continue
        mevcut.append(m.name.replace("models/", ""))

    tercih = [
        "gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash",
        "gemini-flash-lite-latest", "gemini-2.5-flash-lite",
    ]
    for t in tercih:
        if t in mevcut:
            return t
    for ad in mevcut:                       # tercih listesinde yoksa herhangi bir 'flash'
        if "flash" in ad.lower():
            return ad
    if mevcut:                              # o da yoksa üretebilen ilk model
        return mevcut[0]
    raise RuntimeError("Hesabında içerik üretebilen bir Gemini modeli bulunamadı.")


def icerik_uret():
    """Gemini ile konu + senaryo + başlık + açıklama + etiketleri üretir."""
    client = genai.Client(api_key=GEMINI_API_KEY)

    if GEMINI_MODEL.strip().lower() in ("", "auto"):
        model = _model_sec(client)
    else:
        model = GEMINI_MODEL
    print(f"    (Kullanılan model: {model})")

    if KONU_IPUCU.strip():
        konu_talimati = f'Use this exact topic: "{KONU_IPUCU.strip()}".'
    else:
        aci = random.choice(ACILAR)
        konu_talimati = (
            f"Pick ONE specific, real, well-documented topic in this direction: {aci}. "
            "Choose something genuinely intriguing but avoid the most overused clickbait cases."
        )

    prompt = f"""You are the writer for a faceless YouTube Shorts channel about UNSOLVED MYSTERIES and CREEPY-BUT-TRUE facts, for a global English-speaking audience.

{konu_talimati}

Write a single Short and return ONLY valid JSON with these exact keys:
- "topic": short label of the chosen topic.
- "script": the narration to be read aloud. Rules: English, 110-140 words (about 45-50 seconds spoken), a powerful hook in the FIRST sentence, build suspense, and end on an eerie or open "what really happened?" style line. Plain spoken sentences only. NO stage directions, NO emojis, NO hashtags, NO sound-effect notes, NO headings.
- "title": a highly clickable, curiosity-driven title optimized for YouTube Shorts search, max 70 characters. Lead with the strongest hook or main keyword. No fake/false claims.
- "description": a 2-3 sentence hooky summary that naturally includes searchable keywords, then a new line with 6-8 relevant hashtags (include #Shorts and #mystery).
- "tags": an array of 15 lowercase strings that MIX broad high-traffic terms (e.g. "unsolved mystery", "creepy", "scary", "unexplained", "true stories", "documentary") with terms specific to THIS topic. No "#" symbol.
- "image_queries": an array of 6-8 short, concrete English stock-photo search phrases that visually match the story's setting, objects, and mood (e.g. "foggy pine forest", "old abandoned ship", "snowy mountain pass at night", "vintage newspaper"). No people's names, no on-image text, no logos. Concrete, searchable visuals only.

Important:
- Base it on real, documented mysteries. Do NOT invent fake events and present them as fact. If a detail is uncertain, phrase it as "some believe" or "it is said".
- Keep it advertiser-friendly (PG-13): mysterious and eerie, but no gore, no graphic violence.
- Make each video feel fresh and different.

Return JSON only, nothing else."""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=1.1,
        ),
    )

    ham = response.text.strip()
    # Nadiren ```json ... ``` sarmalı gelirse temizle
    if ham.startswith("```"):
        ham = ham.strip("`")
        ham = ham[ham.find("{"): ham.rfind("}") + 1]

    data = json.loads(ham)

    # Etiketleri temizle (baştaki # ve boşlukları at)
    etiketler = [str(t).lstrip("#").strip() for t in data.get("tags", []) if str(t).strip()]
    gorsel_sorgulari = [str(q).strip() for q in data.get("image_queries", []) if str(q).strip()]

    return {
        "konu": data["topic"],
        "senaryo": data["script"].strip(),
        "baslik": data["title"].strip(),
        "aciklama": data["description"].strip(),
        "etiketler": etiketler,
        "gorsel_sorgulari": gorsel_sorgulari,
    }


# ==================================================================
#  ADIM 2: SESLENDİRME (edge-tts) + KELİME ZAMANLAMASI
# ==================================================================

async def _seslendir_ve_zamanla(metin, ses, ses_dosyasi):
    """
    Metni seslendirip ses.mp3 olarak kaydeder ve her kelimenin
    başlangıç anını + süresini toplar (altyazı senkronu için).
    edge-tts zaman birimi '100 nanosaniye' -> 10.000.000'a bölünce saniye.
    """
    communicate = edge_tts.Communicate(metin, ses)
    kelimeler = []

    with open(ses_dosyasi, "wb") as f:
        async for parca in communicate.stream():
            if parca["type"] == "audio":
                f.write(parca["data"])
            elif parca["type"] == "WordBoundary":
                kelimeler.append({
                    "kelime": parca["text"],
                    "baslangic": parca["offset"] / 10_000_000,
                    "sure": parca["duration"] / 10_000_000,
                })

    return kelimeler


def seslendir(metin, ses, ses_dosyasi):
    """Async fonksiyonu normal (senkron) şekilde çalıştırır."""
    return asyncio.run(_seslendir_ve_zamanla(metin, ses, ses_dosyasi))


# ==================================================================
#  ADIM 3: KURGU + ALTYAZI (MoviePy)
# ==================================================================

def kelime_gruplari(kelimeler, grup_boyutu, toplam_sure):
    """Kelimeleri 2-3'erli gruplara böler, zamanlamalarını hesaplar."""
    gruplar = []
    for i in range(0, len(kelimeler), grup_boyutu):
        parca = kelimeler[i:i + grup_boyutu]
        metin = " ".join(k["kelime"] for k in parca)
        baslangic = parca[0]["baslangic"]
        gruplar.append({"metin": metin, "baslangic": baslangic})

    # Boşluk kalmasın diye her grup sonrakine kadar ekranda kalır
    for i, g in enumerate(gruplar):
        if i < len(gruplar) - 1:
            g["sure"] = gruplar[i + 1]["baslangic"] - g["baslangic"]
        else:
            g["sure"] = max(0.5, toplam_sure - g["baslangic"])

    return gruplar


def dikey_yap(clip):
    """Videoyu 1080x1920 (dikey) olacak şekilde ölçekleyip ortadan kırpar."""
    oran = max(HEDEF_GENISLIK / clip.w, HEDEF_YUKSEKLIK / clip.h)
    clip = clip.resized((int(clip.w * oran), int(clip.h * oran)))
    x1 = (clip.w - HEDEF_GENISLIK) / 2
    y1 = (clip.h - HEDEF_YUKSEKLIK) / 2
    return clip.cropped(x1=x1, y1=y1, width=HEDEF_GENISLIK, height=HEDEF_YUKSEKLIK)


def _uygun_font():
    """Kullanılabilir KALIN bir font bulur (Windows / Mac / Linux uyumlu)."""
    for a in [FONT_PATH,
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial Bold.ttf"]:
        if a and os.path.exists(a):
            return a
    return FONT_PATH


def _metinden_gruplar(senaryo, grup_boyutu, sure):
    """Kelime zamanlaması gelmezse: senaryoyu kelime gruplarına bölüp süreyi eşit dağıtır."""
    kelimeler = senaryo.split()
    gruplar = []
    for i in range(0, len(kelimeler), grup_boyutu):
        gruplar.append({"metin": " ".join(kelimeler[i:i + grup_boyutu])})
    if not gruplar:
        return []
    pay = sure / len(gruplar)
    for j, g in enumerate(gruplar):
        g["baslangic"] = j * pay
        g["sure"] = pay
    return gruplar


def altyazi_klip(metin, baslangic, sure):
    """Tek bir altyazı parçasını (sarı, kalın, kenarlıklı) oluşturur."""
    kutu_h = int(HEDEF_YUKSEKLIK * 0.22)
    txt = TextClip(
        font=_uygun_font(),
        text=metin,
        font_size=YAZI_BOYUTU,
        color=YAZI_RENGI,
        stroke_color=KENARLIK_RENGI,
        stroke_width=KENARLIK_KALINLIGI,
        method="caption",
        size=(int(HEDEF_GENISLIK * 0.9), kutu_h),
        text_align="center",
    )
    # Altyazı kutusunu alt tarafa yerleştir (yazının ortası ALTYAZI_DIKEY hizasına gelsin)
    ust = int(HEDEF_YUKSEKLIK * ALTYAZI_DIKEY - kutu_h / 2)
    return (
        txt.with_start(baslangic)
           .with_duration(sure)
           .with_position(("center", ust))
    )


def uret_arka_plan(sure):
    """
    Stok video YOKSA: karanlık, mavimsi, içinde yavaşça gezen bir ışık/sis olan
    atmosferik arka planı SIFIRDAN üretir. Hiçbir dosya indirmen gerekmez.
    Hız için düşük çözünürlükte üretilip 1080x1920'ye büyütülür.
    """
    kW, kH = 540, 960
    yy = np.linspace(0, 1, kH)[:, None]
    xx = np.linspace(0, 1, kW)[None, :]
    taban = 0.04 + 0.10 * yy   # üstten alta hafif açılan koyu zemin

    def kare(t):
        # yavaşça gezen yumuşak ışık merkezi (gizemli "sis" hissi)
        cx = 0.5 + 0.30 * np.sin(t * 0.18)
        cy = 0.45 + 0.30 * np.cos(t * 0.13)
        d2 = (xx - cx) ** 2 + (yy - cy) ** 2
        glow = np.exp(-d2 / 0.05) * 0.22
        v = np.clip(taban + glow, 0, 1)
        rgb = np.empty((kH, kW, 3), dtype="uint8")
        rgb[..., 0] = (v * 55).astype("uint8")     # R
        rgb[..., 1] = (v * 65).astype("uint8")     # G
        rgb[..., 2] = (v * 110).astype("uint8")    # B (soğuk, karanlık mavi)
        return rgb

    return (
        VideoClip(kare, duration=sure)
        .with_fps(30)
        .resized((HEDEF_GENISLIK, HEDEF_YUKSEKLIK))
    )


_TARAYICI_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _dosya_indir(url, hedef):
    """Görseli tarayıcı kimliğiyle indirir (bazı siteler UA'sız isteği 403 ile reddeder)."""
    req = urllib.request.Request(url, headers={"User-Agent": _TARAYICI_UA})
    with urllib.request.urlopen(req, timeout=30) as r, open(hedef, "wb") as f:
        shutil.copyfileobj(r, f)


KULLANILAN_DOSYA = "kullanilan_gorseller.txt"   # geçmiş videolarda kullanılan görsellerin hafızası


def _kullanilanlari_yukle():
    s = set()
    if os.path.exists(KULLANILAN_DOSYA):
        try:
            with open(KULLANILAN_DOSYA, encoding="utf-8") as f:
                for satir in f:
                    satir = satir.strip()
                    if satir:
                        s.add(satir)
        except Exception:
            pass
    return s


def _kullanilanlari_kaydet(kullanilmis):
    try:
        with open(KULLANILAN_DOSYA, "w", encoding="utf-8") as f:
            for k in sorted(kullanilmis):
                f.write(k + "\n")
    except Exception as e:
        print(f"   [uyarı] görsel hafızası kaydedilemedi: {e}")


def _pexels_foto_url(sorgu, kullanilmis):
    for sayfa in (random.randint(1, 5), 1):
        try:
            url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode(
                {"query": sorgu, "per_page": 30, "page": sayfa, "orientation": "portrait"})
            req = urllib.request.Request(url, headers={"Authorization": PEXELS_API_KEY,
                                                       "User-Agent": _TARAYICI_UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception:
            continue
        fotolar = data.get("photos", [])
        if not fotolar:
            continue
        random.shuffle(fotolar)
        for foto in fotolar:
            anahtar = f"pex:{foto.get('id')}"
            if anahtar in kullanilmis:
                continue
            src = foto.get("src", {})
            u = src.get("portrait") or src.get("large2x") or src.get("original")
            if u:
                kullanilmis.add(anahtar)
                return u
    return None


def _pixabay_foto_url(sorgu, kullanilmis):
    # Rastgele DERİN sayfa + karıştır + daha önce KULLANILMAMIŞ görsel seç
    for sayfa in (random.randint(1, 10), random.randint(1, 4), 1):
        try:
            url = "https://pixabay.com/api/?" + urllib.parse.urlencode(
                {"key": PIXABAY_API_KEY, "q": sorgu, "image_type": "photo",
                 "orientation": "vertical", "per_page": 30, "page": sayfa, "safesearch": "true"})
            req = urllib.request.Request(url, headers={"User-Agent": _TARAYICI_UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception:
            continue
        hits = data.get("hits", [])
        if not hits:
            continue
        random.shuffle(hits)
        for h in hits:
            anahtar = f"px:{h.get('id')}"
            if anahtar in kullanilmis:
                continue
            u = h.get("largeImageURL") or h.get("webformatURL")
            if u:
                kullanilmis.add(anahtar)
                return u
    return None


def _openverse_ara(sorgu, kullanilmis):
    for sayfa in (random.randint(1, 5), random.randint(1, 2), 1):
        try:
            url = "https://api.openverse.org/v1/images/?" + urllib.parse.urlencode(
                {"q": sorgu, "license": "cc0,pdm,by", "page_size": 20, "page": sayfa, "mature": "false"})
            req = urllib.request.Request(url, headers={"User-Agent": _TARAYICI_UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception:
            continue
        res = data.get("results", [])
        if not res:
            continue
        random.shuffle(res)
        for it in res:
            u = it.get("url")
            anahtar = f"ov:{u}"
            if not u or anahtar in kullanilmis:
                continue
            kullanilmis.add(anahtar)
            return {"url": u, "creator": it.get("creator") or "Unknown",
                    "license": (it.get("license") or "").upper()}
    return None


def gorselleri_indir(sorgular, klasor="gecici_gorseller"):
    """
    Konuya uygun fotoğrafları indirir. Sıra: Pixabay -> Pexels -> Openverse (anahtarsız).
    Her video FARKLI görseller kullanır (geçmiş videolarda kullanılanları hatırlar).
    """
    if os.path.isdir(klasor):
        shutil.rmtree(klasor, ignore_errors=True)
    os.makedirs(klasor, exist_ok=True)

    pixabay_var = bool(PIXABAY_API_KEY.strip()) and "BURAYA_" not in PIXABAY_API_KEY
    pexels_var = bool(PEXELS_API_KEY.strip()) and "BURAYA_" not in PEXELS_API_KEY
    kaynak = "Pixabay" if pixabay_var else ("Pexels" if pexels_var else "Openverse")
    print(f"   (Görsel kaynağı: {kaynak})")

    kullanilmis = _kullanilanlari_yukle()   # geçmiş videolarda kullanılanları yükle
    onceki = len(kullanilmis)
    yollar, krediler = [], []
    for i, sorgu in enumerate(sorgular):
        try:
            kredi = None
            if pixabay_var:
                foto_url = _pixabay_foto_url(sorgu, kullanilmis)
            elif pexels_var:
                foto_url = _pexels_foto_url(sorgu, kullanilmis)
            else:
                bilgi = _openverse_ara(sorgu, kullanilmis)
                foto_url = bilgi["url"] if bilgi else None
                kredi = f"{bilgi['creator']} ({bilgi['license']})" if bilgi else None

            if not foto_url:
                continue
            hedef = os.path.join(klasor, f"gorsel_{i:02d}.jpg")
            _dosya_indir(foto_url, hedef)
            yollar.append(hedef)
            if kredi:
                krediler.append(kredi)
            print(f"   [görsel indi] {sorgu}")
        except Exception as e:
            print(f"   [görsel atlandı] {sorgu} -> {e}")

    if pixabay_var and yollar:
        krediler = ["Images via Pixabay (pixabay.com)"]
    elif pexels_var and yollar:
        krediler = ["Photos via Pexels (pexels.com)"]

    # Birincil kaynaktan hiç görsel gelmezse, ANAHTARSIZ Openverse'e düş
    if not yollar and kaynak != "Openverse":
        print("   (Birincil kaynak boş döndü -> Openverse deneniyor)")
        for i, sorgu in enumerate(sorgular):
            try:
                bilgi = _openverse_ara(sorgu, kullanilmis)
                if not bilgi or not bilgi.get("url"):
                    continue
                hedef = os.path.join(klasor, f"gorsel_{i:02d}.jpg")
                _dosya_indir(bilgi["url"], hedef)
                yollar.append(hedef)
                krediler.append(f"{bilgi['creator']} ({bilgi['license']})")
                print(f"   [görsel indi] {sorgu}")
            except Exception as e:
                print(f"   [görsel atlandı] {sorgu} -> {e}")

    _kullanilanlari_kaydet(kullanilmis)   # bu videodakileri de hafızaya ekle
    print(f"   (Görsel hafızası: {onceki} -> {len(kullanilmis)} görsel)")
    return yollar, krediler


def slayt_yap(gorseller, toplam_sure):
    """Fotoğrafları, yavaşça yakınlaşan (Ken Burns) sinematik bir slayta çevirir."""
    n = len(gorseller)
    pay = toplam_sure / n
    klipler = []
    for i, yol in enumerate(gorseller):
        d = pay if i < n - 1 else (toplam_sure - pay * (n - 1))
        img = dikey_yap(ImageClip(yol)).with_duration(d)
        # zamanla hafif yakınlaş (d'yi default argümanla sabitliyoruz - closure hatası olmasın)
        img = img.resized(lambda t, d=d: 1 + 0.06 * (t / d))
        img = img.with_position(("center", "center"))
        seg = CompositeVideoClip(
            [img], size=(HEDEF_GENISLIK, HEDEF_YUKSEKLIK)
        ).with_duration(d)
        klipler.append(seg)
    return concatenate_videoclips(klipler)


def video_hazirla(ses_dosyasi, kelimeler, senaryo, gorseller=None):
    """Arka planı hazırla (görsel varsa slayt, yoksa stok video, o da yoksa karanlık fon)."""
    ses_klip = AudioFileClip(ses_dosyasi)
    sure = ses_klip.duration
    print(f"[Kurgu] Ses süresi: {sure:.1f} sn")

    videolar = []
    for uzanti in ("*.mp4", "*.mov", "*.mkv", "*.webm", "*.avi"):
        videolar += glob.glob(os.path.join(STOK_VIDEO_KLASORU, uzanti))

    if gorseller:
        print(f"[Kurgu] {len(gorseller)} fotoğraf ile slayt gösterisi yapılıyor...")
        bg = slayt_yap(gorseller, sure)
    elif videolar:
        secilen = random.choice(videolar)
        print(f"[Kurgu] Arka plan (stok): {os.path.basename(secilen)}")
        bg = VideoFileClip(secilen).without_audio()
        bg = dikey_yap(bg)
        if bg.duration < sure:
            tekrar = int(sure // bg.duration) + 1
            bg = concatenate_videoclips([bg] * tekrar)
        bg = bg.subclipped(0, sure)
    else:
        print("[Kurgu] Görsel/stok yok -> karanlik atmosferik arka plan uretiliyor...")
        bg = uret_arka_plan(sure)

    if kelimeler:
        gruplar = kelime_gruplari(kelimeler, HER_EKRANDA_KELIME, sure)
    else:
        print("[Kurgu] Kelime zamanlaması yok -> altyazılar metinden dağıtılıyor")
        gruplar = _metinden_gruplar(senaryo, HER_EKRANDA_KELIME, sure)
    altyazilar = [altyazi_klip(g["metin"], g["baslangic"], g["sure"]) for g in gruplar]
    print(f"[Kurgu] {len(altyazilar)} altyazı parçası oluşturuldu")

    final = CompositeVideoClip([bg, *altyazilar]).with_audio(ses_klip)
    final = final.with_duration(sure)

    print("[Kurgu] Video işleniyor... (birkaç dakika sürebilir)")
    final.write_videofile(
        CIKTI_VIDEO,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
    )
    print(f"[Kurgu] Hazır: {CIKTI_VIDEO}")


# ==================================================================
#  ADIM 4: YOUTUBE'A YÜKLEME (YouTube Data API v3)
# ==================================================================

# Niş için yüksek trafikli temel etiketler (Gemini'nin ürettikleriyle birleştirilir)
TEMEL_ETIKETLER = [
    "shorts", "shortsfeed", "unsolved mystery", "unsolved mysteries",
    "creepy", "creepy facts", "scary", "mystery", "unexplained",
    "strange", "paranormal", "true stories", "did you know", "facts",
    "documentary",
]


def etiketleri_hazirla(gemini_etiketleri):
    """Gemini etiketleri + temel etiketleri birleştirir, tekrarları atar, sınırlar."""
    birlesik, gorulen = [], set()
    for t in list(gemini_etiketleri) + TEMEL_ETIKETLER:
        t = t.strip().lstrip("#")
        if t and t.lower() not in gorulen:
            gorulen.add(t.lower())
            birlesik.append(t)
    # YouTube toplam etiket uzunluğu ~500 karakter; güvenli tarafta kalalım
    son, toplam = [], 0
    for t in birlesik:
        if toplam + len(t) + 1 > 460:
            break
        son.append(t)
        toplam += len(t) + 1
    return son[:20]


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def youtube_servisi():
    """İlk seferde tarayıcıda bir kez izin verirsin; sonra token.json ile hatırlar."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # client_secret dosyasını otomatik bul (adı tam 'client_secret.json' olmasa da)
            adaylar = (["client_secret.json"]
                       + glob.glob("client_secret*.json")
                       + glob.glob("*apps.googleusercontent.com.json"))
            secret = next((a for a in adaylar if os.path.exists(a)), None)
            if not secret:
                raise FileNotFoundError(
                    "OAuth dosyası bulunamadı! Google'dan indirdiğin JSON dosyasını "
                    f"şu klasöre koy: {os.getcwd()}\n"
                    "(Genelde 'İndirilenler' klasöründe, adı client_secret... ile başlar.)"
                )
            print(f"[YouTube] OAuth dosyası: {secret}")
            flow = InstalledAppFlow.from_client_secrets_file(secret, SCOPES)
            # access_type=offline + prompt=consent -> token.json içine "refresh_token" gelir
            # (sunucuda tarayıcısız yenileme için ŞART)
            creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def youtube_yukle(dosya, baslik, aciklama, etiketler):
    """Videoyu HERKESE AÇIK (public) ve dil/hedef İngilizce olarak yükler."""
    youtube = youtube_servisi()

    body = {
        "snippet": {
            "title": baslik,
            "description": aciklama,
            "tags": etiketler,
            "categoryId": YOUTUBE_KATEGORI,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",        # HERKESE AÇIK (kontrol etmeden yayınla)
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(dosya, chunksize=-1, resumable=True, mimetype="video/mp4")
    istek = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print("[YouTube] Yükleme başladı...")
    yanit = istek.execute()
    video_id = yanit.get("id")
    print(f"[YouTube] Yüklendi (HERKESE AÇIK): https://youtu.be/{video_id}")
    return video_id


# ==================================================================
#  ANA AKIŞ
# ==================================================================

def main():
    if "BURAYA_GEMINI" in GEMINI_API_KEY:
        print("HATA: GEMINI_API_KEY boş. https://aistudio.google.com/apikey adresinden ücretsiz al.")
        return
    if not os.path.exists(_uygun_font()):
        print(f"HATA: Font bulunamadı: {_uygun_font()}  (FONT_PATH'i düzelt)")
        return

    print("=== 1/4  İçerik üretiliyor (Gemini)...")
    try:
        icerik = icerik_uret()
    except Exception as e:
        print("\n!!! GEMINI ADIMINDA HATA. Tam mesaj:")
        print("   ", str(e))
        print("\nOlası çözümler (sırayla dene):")
        print("  1) Kütüphaneyi güncelle:  python -m pip install -U google-genai")
        print('  2) Model adını değiştir:  kodda GEMINI_MODEL = "gemini-2.0-flash" yap')
        print("  3) Anahtarı yeniden oluştur: https://aistudio.google.com/apikey")
        return
    print(f"    Konu   : {icerik['konu']}")
    print(f"    Başlık : {icerik['baslik']}")
    print(f"    Etiket : {', '.join(icerik['etiketler'][:8])} ...")
    print("    --- SENARYO ---")
    print("    " + icerik["senaryo"].replace("\n", "\n    "))

    print("=== 2/4  Seslendirme (edge-tts)...")
    kelimeler = seslendir(icerik["senaryo"], SES, SES_DOSYASI)
    print(f"    Ses kaydedildi: {SES_DOSYASI}  ({len(kelimeler)} kelime zamanlandı)")

    print("=== 3/4  Görseller indiriliyor + video kurgulanıyor...")
    gorseller, krediler = gorselleri_indir(icerik.get("gorsel_sorgulari", []))
    if not gorseller:
        print("    (Görsel indirilemedi -> karanlık fon kullanılacak)")
    video_hazirla(SES_DOSYASI, kelimeler, icerik["senaryo"], gorseller)

    print("=== 4/4  YouTube'a yükleniyor (HERKESE AÇIK)...")
    # SEO: başlığa #Shorts ekle, açıklamaya görsel kredisi, etiketleri güçlendir
    baslik = icerik["baslik"]
    if "#short" not in baslik.lower() and len(baslik) <= 88:
        baslik += " #Shorts"
    aciklama = icerik["aciklama"]
    if krediler:
        aciklama += "\n\nImage credits: " + "; ".join(dict.fromkeys(krediler))
    etiketler = etiketleri_hazirla(icerik["etiketler"])
    youtube_yukle(CIKTI_VIDEO, baslik, aciklama, etiketler)

    print("=== Bitti! Video kanalına HERKESE AÇIK olarak yüklendi.")


if __name__ == "__main__":
    main()
