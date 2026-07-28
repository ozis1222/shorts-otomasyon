# -*- coding: utf-8 -*-
"""
============================================================
   ÜCRETSİZ YOUTUBE SHORTS OTOMASYONU  (Tam Otomatik)
============================================================
Hiçbir ücretli/üyelikli servis KULLANILMAZ.

Akış (her calistirmada sirayla, elle hicbir sey yapmadan):
  1) Gemini (ucretsiz)   -> konu + senaryo + baslik + aciklama + etiket
                            + KONUYA UYGUN gorsel arama kelimeleri uretir
  2) edge-tts (ucretsiz) -> senaryoyu Ingilizce dogal sesle okur -> ses.mp3
  3) Pixabay/Pexels/Openverse (ucretsiz) -> KONUYA GORE otomatik arka plan
                            VIDEO (yoksa FOTOGRAF) indirir  <-- ARTIK OTOMATIK
  4) MoviePy (ucretsiz)  -> 1080x1920 dikey montaj + SENKRON sari altyazi
  5) YouTube Data API v3 -> videoyu "public" (herkese acik) olarak yukler

Calistirmak icin:  python main.py
Hem yerel Windows'ta hem GitHub Actions (bulut/Linux) uzerinde calisir.
Anahtarlar ortam degiskeninden (secret) okunur; yoksa asagidaki degerler kullanilir.
"""

import os
import re
import sys
import json
import random
import asyncio
import warnings

# Windows konsolu/log dosyasi emoji veya Turkce karakterde PATLAMASIN diye stdout'u UTF-8 yap
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# MoviePy'nin zararsiz "son kare okunamadi" uyarisini gizle (video yine de dogru uretilir)
warnings.filterwarnings("ignore", message=r".*bytes wanted but.*")

# Bu dosyanin bulundugu klasor -> tum yollar buna gore (Windows'ta da Linux/bulut'ta da calisir)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================================================
#  1) AYARLAR  ->  Sadece bu bolumu duzenlemen yeterli
# =========================================================

# --- Gemini (ÜCRETSİZ: https://aistudio.google.com/apikey ) ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or "AQ.Ab8RN6IE55HA57S9m5hpM42Iyr_Ct0_b6n2z5wSWGQ2dhr5x-Q"
GEMINI_MODEL   = os.environ.get("GEMINI_MODEL") or "gemini-flash-latest"   # calisiyor. Alt: "gemini-3.5-flash", "gemini-3-flash-preview"

# --- Kanalin konusu (Gemini buradan konu + gorsel kelimelerini uretir, hep INGILIZCE) ---
NICHE = ("real unsolved mysteries, unexplained events, mysterious disappearances, "
         "strange historical cases, cold cases and eerie unexplained phenomena")

# --- Arka plan gorselleri icin ANAHTARLAR (hepsi ucretsiz) ---
#  * Pixabay (ONERILIR - VIDEO indirmek icin sart): https://pixabay.com/api/docs/
#  * Pexels  (opsiyonel yedek, video+foto):         https://www.pexels.com/api/
#  Ikisini de bos birakirsan gorseller anahtar GEREKTIRMEYEN Openverse'ten (foto) gelir.
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY") or "56752910-1e70a403809949c23e6637cf1"   # video icin gerekli
PEXELS_API_KEY  = os.environ.get("PEXELS_API_KEY") or ""                                        # opsiyonel

# --- Seslendirme (Ingilizce dogal erkek sesleri) ---
VOICE = "en-US-ChristopherNeural"   # gizem nisi - derin/otoriter anlatici

# --- Altyazi ayarlari ---
FONT_PATH       = os.path.join(BASE_DIR, "fonts", "Anton-Regular.ttf")  # modern caption fontu (repoda gomulu)
WORDS_PER_CHUNK = 3          # ekranda ayni anda kac kelime gorunsun (2-3 ideal)
FONT_SIZE       = 115        # Anton sikisik/uzun bir font -> 3 kelime tek satira sigar
TEXT_COLOR      = "yellow"
STROKE_COLOR    = "black"
STROKE_WIDTH    = 8          # kalin siyah kenarlik -> her arka planda net okunur
SUBTITLE_Y      = 0.72       # dikey konum (viral tarz ~0.72)

# --- Video boyutu (Shorts = dikey) ---
W, H = 1080, 1920

# --- Otomatik indirilen medyalarin gecici klasoru ---
MEDYA_KLASORU = os.path.join(BASE_DIR, "medya_gecici")
# --- (YEDEK) Internetten hic gorsel gelmezse buradaki videolardan secer (opsiyonel) ---
YEDEK_VIDEO_KLASORU = os.path.join(BASE_DIR, "arka_plan_videolar")

# --- MANUEL MOD (True yaparsan Gemini kullanmaz, asagidakileri kullanir) ---
MANUAL_MODE      = False
senaryo_metni    = """Buraya kendi senaryonu yapistirabilirsin (yalnizca MANUAL_MODE = True ise kullanilir)."""
video_basligi    = "My Video Title #Shorts"
video_aciklamasi = "My description here. #Shorts"
etiketler        = ["shorts", "facts"]
gorsel_sorgulari = ["dark foggy forest night", "abandoned building at night", "old mysterious documents", "snowy mountains blizzard", "empty dark road at night", "misty graveyard night"]

# --- YouTube ---
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")
TOKEN_FILE         = os.path.join(BASE_DIR, "token.json")
CATEGORY_ID        = "27"       # 27=Education, 24=Entertainment, 22=People & Blogs
PRIVACY            = os.environ.get("PRIVACY") or "public"   # "public" / "unlisted" / "private"
# Bulutta varsayilan ACIK; yerelde sadece video uretmek icin: set UPLOAD_TO_YOUTUBE=0
UPLOAD_TO_YOUTUBE  = os.environ.get("UPLOAD_TO_YOUTUBE", "1") != "0"

# --- Marka / Abone ol ---
LOGO_PATH        = os.path.join(BASE_DIR, "assets", "logo.png")   # kanal logosu (kose + abone cagrisi)
ABONE_YAZI       = "SUBSCRIBE"                                     # abone cagrisinda gorunen yazi

# --- Cikti dosyalari ---
AUDIO_FILE       = os.path.join(BASE_DIR, "ses.mp3")
OUTPUT_FILE      = os.path.join(BASE_DIR, "shorts_hazir.mp4")
USED_TOPICS_FILE = os.path.join(BASE_DIR, "kullanilan_konular.txt")

# Tarayici gibi gorunelim (Pixabay bazen 403 verir)
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")


# =========================================================
#  2) GEMINI ile konu + senaryo + gorsel kelimeleri uret
# =========================================================
def gemini_uret():
    from google import genai

    client = genai.Client(api_key=GEMINI_API_KEY)

    onceki = ""
    if os.path.exists(USED_TOPICS_FILE):
        with open(USED_TOPICS_FILE, "r", encoding="utf-8") as f:
            onceki = f.read().strip()

    prompt = f"""You are the writer for a HIGH-QUALITY, curiosity-driven ENGLISH YouTube Shorts channel.
Channel niche: {NICHE}

--- STAY IN YOUR LANE (this channel must NEVER overlap our other channels) ---
This channel is ONLY about real UNSOLVED MYSTERIES and unexplained events: mysterious disappearances
(people, ships, planes, expeditions), strange unsolved historical cases (like the Dyatlov Pass), eerie
unexplained phenomena, famous cold cases, and dark true mysteries that were never solved.
Keep it eerie and suspenseful, based on REAL documented cases (present unproven theories AS theories, not fact).
SIGNATURE HOOK STYLE: open with a chilling unanswered question or a stark unexplained fact, and vary it every
time. Examples of the vibe (do NOT reuse verbatim): "Nine hikers ran into the snow, barefoot, and never came back."
/ "The ship was found sailing itself, the entire crew simply gone." / "To this day, no one can explain that night."

Create ONE brand-new Short about a SINGLE gripping real unsolved mystery or unexplained case.
Every video must cover a DIFFERENT, specific topic. Do NOT repeat or closely resemble any of these
already-used topics:
{onceki if onceki else "(none yet)"}

Pick a fresh angle. Rotate across ideas like: mysterious disappearances (people, ships, planes, whole
expeditions), unsolved historical mysteries, eerie unexplained phenomena, famous cold cases, lost cities
or treasures, strange events witnessed by many, unexplained discoveries, and "what really happened" cases.
Be specific, not generic.

Rules for the "script" (spoken narration):
- Language: English.
- Length: 100-150 words (about 40-55 seconds when spoken).
- The FIRST sentence MUST be a strong scroll-stopping HOOK, and it MUST be DIFFERENT every video --
  never reuse the same opening word or phrase. Do NOT start with "Imagine" (overused). Rotate the style:
  a shocking fact, a bold claim, a surprising number, a "What if...", or a direct question.
- Content must be SCIENTIFICALLY ACCURATE and based on real astronomy. Do NOT invent fake facts or numbers.
  It is fine to explore real open questions and mysteries, but present speculation clearly as speculation.
- Awe-inspiring, vivid but simple spoken style. Short sentences. Build tension toward a "wow" moment.
- NO stage directions, NO emojis, NO "[music]".
- End with one short line that invites the viewer to follow for more cosmic mysteries.

RETENTION RULES (this decides whether the video blows up -- target 70%+ average view duration):
- The first 1-2 seconds are EVERYTHING. The FIRST sentence is the hook: MAX ~12 words, front-load the single
  most shocking element FIRST, and open a curiosity GAP the viewer NEEDS resolved. No throat-clearing, no
  "Today"/"Welcome"/"Imagine", no slow build. Keep every sentence short and punchy to hold attention.
- End with a line that pays off or twists that gap, so viewers stay to the very end (this lifts retention).
- VISUAL SYNC (very important): list "visual_queries" IN THE SAME ORDER as the narration -- query 1 must show
  EXACTLY what the opening line describes, and each next query must match the next thing said, evenly from
  start to finish, so the on-screen image ALWAYS matches the words at that moment. Give 7-8 queries.

Return ONLY valid JSON (no markdown, no ```), EXACTLY this shape:
{{
  "topic": "short specific topic label",
  "script": "the full narration text as one paragraph",
  "title": "catchy, curiosity-driven YouTube title under 90 characters, include #Shorts",
  "description": "2-3 sentence description, then a few relevant hashtags",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"],
  "visual_queries": ["query1", "query2", "query3", "query4", "query5", "query6"]
}}

About "visual_queries" -- THIS IS A DARK MYSTERY channel, footage MUST look eerie and cinematic:
- Provide 6 to 8 SPECIFIC Pixabay search phrases (3 to 6 words each) for REAL footage matching DISTINCT parts
  of THIS exact topic. Be specific and concrete (not "mystery" but "dark foggy forest at night"; not "old" but
  "old abandoned wooden cabin").
- EVERY phrase should feel dark, eerie and cinematic: night, fog, shadows, abandoned places, storms, snow,
  dim light, empty roads, old documents, cold isolated locations.
- Each phrase MUST be clearly DIFFERENT and describe a different concrete real scene of the topic.
- STRICTLY FORBIDDEN: flowers, insects, cute animals, happy people, weddings, food, offices, bright sunny nature.
- Good examples: "dark foggy forest night", "abandoned building interior", "snowy mountains blizzard",
  "empty dark road at night", "old handwritten documents", "stormy ocean waves dark", "misty graveyard night".
"""

    # GECICI hatalar (503 asiri yuk / 429 kota / 500 / timeout) icin tekrar dene + yedek modele gec
    import time
    modeller, gorulen = [], set()
    for md in [GEMINI_MODEL, "gemini-3.5-flash", "gemini-3-flash-preview"]:
        if md and md not in gorulen:
            gorulen.add(md); modeller.append(md)

    son_hata = None
    for model in modeller:
        for deneme in range(1, 5):
            try:
                resp = client.models.generate_content(model=model, contents=prompt)
                text = (resp.text or "").strip()
                bulunan = re.search(r"\{.*\}", text, re.S)
                if not bulunan:
                    raise RuntimeError("Gemini gecerli JSON dondurmedi: " + text[:120])
                data = json.loads(bulunan.group(0))
                with open(USED_TOPICS_FILE, "a", encoding="utf-8") as f:
                    f.write((data.get("topic", "").strip()) + "\n")
                print(f"      (Gemini model: {model})")
                return data
            except Exception as e:
                son_hata = e
                mesaj = str(e).lower()
                gecici = any(k in mesaj for k in ("503", "429", "500", "unavailable",
                             "overloaded", "resource_exhausted", "high demand", "timeout", "deadline"))
                if gecici and deneme < 4:
                    bekle = 5 * deneme      # 5s, 10s, 15s artan bekleme
                    print(f"      Gemini gecici hata ({model}, deneme {deneme}): {bekle}s bekle...")
                    time.sleep(bekle)
                    continue
                print(f"      Model '{model}' olmadi ({str(e)[:70]}), sonraki modele...")
                break
    raise RuntimeError(f"Gemini hicbir modelle uretemedi. Son hata: {son_hata}")


# =========================================================
#  3) edge-tts ile seslendir + KELIME ZAMANLAMASI
# =========================================================
async def seslendir_ve_zamanla(text, voice, out_path):
    import edge_tts

    # edge-tts 7.x: kelime senkronu icin boundary="WordBoundary" SART (varsayilan SentenceBoundary)
    try:
        communicate = edge_tts.Communicate(text, voice, boundary="WordBoundary")
    except TypeError:   # cok eski edge-tts: 'boundary' argumani yok
        communicate = edge_tts.Communicate(text, voice)

    words, sentences, audio_bytes = [], [], 0
    with open(out_path, "wb") as f:
        async for chunk in communicate.stream():
            tur = chunk["type"]
            if tur == "audio":
                f.write(chunk["data"])
                audio_bytes += len(chunk["data"])
            elif tur == "WordBoundary":
                s = chunk["offset"] / 10_000_000          # 100ns -> saniye
                d = chunk["duration"] / 10_000_000
                words.append({"word": chunk["text"], "start": s, "end": s + d})
            elif tur == "SentenceBoundary":
                s = chunk["offset"] / 10_000_000
                d = chunk["duration"] / 10_000_000
                sentences.append({"text": chunk["text"], "start": s, "end": s + d})

    if audio_bytes < 1024:
        raise RuntimeError("edge-tts ses uretemedi (internet ya da servis sorunu olabilir).")

    if words:                                             # en iyi: birebir kelime senkronu
        return words
    if sentences:                                         # yedek: cumle zamanindan kelime turet
        return _cumleden_kelime_zamani(sentences)
    return _sese_esit_dagit(text, out_path)               # son care: ses suresine esit dagit


def _cumleden_kelime_zamani(sentences):
    """Cumle sinirlarindan, kelime uzunluguna gore orantili kelime zamanlamasi uretir."""
    out = []
    for c in sentences:
        parcalar = c["text"].split()
        if not parcalar:
            continue
        toplam = sum(len(p) for p in parcalar) or 1
        t = c["start"]
        for p in parcalar:
            d = (c["end"] - c["start"]) * (len(p) / toplam)
            out.append({"word": p, "start": t, "end": t + d})
            t += d
    return out


def _sese_esit_dagit(text, audio_path):
    """Hicbir zamanlama gelmezse: kelimeleri ses suresine esit boler (son care)."""
    from moviepy import AudioFileClip
    with AudioFileClip(audio_path) as a:
        dur = a.duration
    parcalar = text.split()
    n = max(1, len(parcalar))
    return [{"word": p, "start": dur * i / n, "end": dur * (i + 1) / n}
            for i, p in enumerate(parcalar)]


# Altyazi bu kelimelerle BITMEZ (yarim kalmis izlenimi verir, okunurlugu bozar)
_ZAYIF_SON = {"a", "an", "the", "of", "and", "to", "in", "for", "with", "that", "is", "was",
              "were", "are", "on", "at", "by", "from", "as", "but", "or", "his", "her", "its",
              "their", "this", "these", "it", "he", "she", "they", "we", "you", "not", "no"}


def kelime_gruplari(words, n):
    """AKILLI parcalama: noktalamada temiz keser, zayif kelimeyle (a/the/of) BITIRMEZ.
    Eskiden kor n'li bolme 'ENGINEERS CARVED A' gibi yarim altyazi uretiyordu -> okunurluk dusuk.
    Artik 2-4 kelime arasi esnek, anlamli parcalar -> daha rahat okunur, retention'a olumlu."""
    enaz = max(2, n - 1)
    encok = n + 1
    gruplar, i, N = [], 0, len(words)
    while i < N:
        parca = []
        while i < N and len(parca) < encok:
            w = words[i]
            parca.append(w)
            i += 1
            ham = (w.get("word") or "").strip()
            if len(parca) < enaz:
                continue
            if ham.endswith((".", ",", "!", "?", ";", ":")):
                break                                   # cumle/ifade sonu -> en temiz kesim
            son = ham.strip('.,!?;:"\'').lower()
            if len(parca) >= n and son not in _ZAYIF_SON:
                break                                   # normal kesim (zayif kelimeyle bitmez)
        if not parca:
            break
        gruplar.append({
            "text":  " ".join(w["word"] for w in parca).upper(),
            "start": parca[0]["start"],
            "end":   parca[-1]["end"],
        })
    return gruplar


# =========================================================
#  4) KONUYA GORE OTOMATIK ARKA PLAN INDIRME
#     Pixabay VIDEO -> Pexels VIDEO -> Pixabay FOTO -> Pexels FOTO -> Openverse FOTO
# =========================================================
def _http_get(url, headers=None, params=None, stream=False, timeout=40):
    import requests
    h = {"User-Agent": USER_AGENT}
    if headers:
        h.update(headers)
    return requests.get(url, headers=h, params=params, stream=stream, timeout=timeout)


def _dosya_indir(url, hedef):
    try:
        r = _http_get(url, stream=True)
        if r.status_code != 200:
            return False
        beklenen = int(r.headers.get("Content-Length", 0) or 0)   # sunucunun soyledigi boyut
        with open(hedef, "wb") as f:
            for parca in r.iter_content(chunk_size=1 << 16):
                if parca:
                    f.write(parca)
        boyut = os.path.getsize(hedef)
        if boyut < 2048:
            return False
        if beklenen and boyut < beklenen * 0.98:   # dosya YARIM indi -> kullanma (donma yapar)
            print("    (dosya yarim indi, atlaniyor)")
            os.remove(hedef)
            return False
        return True
    except Exception as e:
        print("    (indirme hatasi:", e, ")")
        if os.path.exists(hedef):
            os.remove(hedef)
        return False


def _pixabay_video(q):
    if not PIXABAY_API_KEY or PIXABAY_API_KEY.startswith("BURAYA"):
        return None
    try:
        r = _http_get("https://pixabay.com/api/videos/", params={
            "key": PIXABAY_API_KEY, "q": q, "per_page": 80, "safesearch": "true"})
        hits = _temiz_hits(r.json().get("hits", []), q)   # sorguya en yakin, alakasiz ATILDI
        adaylar = []
        for h in hits:
            v = h.get("videos", {})
            for boyut in ("large", "medium", "small", "tiny"):
                url = v.get(boyut, {}).get("url")
                if url:
                    if url not in _KULLANILAN_MEDYA:   # DAHA ONCE KULLANILDIYSA ALMA (tekrar yok)
                        adaylar.append(url)
                    break
        if adaylar:
            return random.choice(adaylar)
    except Exception as e:
        print("    (pixabay video hatasi:", e, ")")
    return None


def _pexels_video(q):
    if not PEXELS_API_KEY:
        return None
    try:
        r = _http_get("https://api.pexels.com/videos/search",
                      headers={"Authorization": PEXELS_API_KEY},
                      params={"query": q, "orientation": "portrait", "per_page": 6})
        vids = r.json().get("videos", [])
        if vids:
            files = random.choice(vids[:5]).get("video_files", [])
            dikey = [f for f in files if f.get("height", 0) >= f.get("width", 0)] or files
            dikey.sort(key=lambda f: f.get("width", 0))
            for f in dikey:
                if f.get("link"):
                    return f["link"]
    except Exception as e:
        print("    (pexels video hatasi:", e, ")")
    return None


def _pixabay_foto(q):
    if not PIXABAY_API_KEY or PIXABAY_API_KEY.startswith("BURAYA"):
        return None
    try:
        r = _http_get("https://pixabay.com/api/", params={
            "key": PIXABAY_API_KEY, "q": q, "image_type": "photo",
            "orientation": "vertical", "safesearch": "true", "per_page": 80, "order": "popular"})
        hits = _temiz_hits(r.json().get("hits", []), q)   # sorguya en yakin, alakasiz ATILDI
        adaylar = [u for u in ((h.get("largeImageURL") or h.get("webformatURL")) for h in hits)
                   if u and u not in _KULLANILAN_MEDYA]      # kullanilmislar ELENDI -> tekrar yok
        if adaylar:
            return random.choice(adaylar)
    except Exception as e:
        print("    (pixabay foto hatasi:", e, ")")
    return None


def _pexels_foto(q):
    if not PEXELS_API_KEY:
        return None
    try:
        r = _http_get("https://api.pexels.com/v1/search",
                      headers={"Authorization": PEXELS_API_KEY},
                      params={"query": q, "orientation": "portrait", "per_page": 6})
        foto = r.json().get("photos", [])
        if foto:
            src = random.choice(foto[:5]).get("src", {})
            return src.get("portrait") or src.get("large2x") or src.get("large")
    except Exception as e:
        print("    (pexels foto hatasi:", e, ")")
    return None


def _openverse_foto(q):
    """Anahtar GEREKMEZ - telifsiz (CC0/PDM) yedek foto kaynagi."""
    try:
        r = _http_get("https://api.openverse.org/v1/images/", params={
            "q": q, "license": "cc0,pdm", "page_size": 20, "mature": "false"})
        for s in r.json().get("results", []):
            blob = ((s.get("title") or "") + " " +
                    " ".join((t.get("name") or "") for t in (s.get("tags") or []))).lower()
            if _yasak_mi(blob):
                continue                      # cicek/bocek/alakasiz -> atla (yedek kaynak da filtreli)
            u = s.get("url") or s.get("thumbnail")
            if u:
                return u
    except Exception as e:
        print("    (openverse hatasi:", e, ")")
    return None


# --- KONU FILTRESI (GIZEM/KARANLIK): nese/gunduz/cicek gibi ALAKASIZ stok girmesin ---
_YASAK_ETIKET = (
    "flower", "floral", "blossom", "insect", "bug", "butterfly", "bee", "dragonfly",
    "garden", "sunny", "sunshine", "sunflower", "meadow", "spring", "summer", "beach", "tropical",
    "wedding", "baby", "kids", "child", "smiling", "happy", "party", "food", "fruit", "cake",
    "business", "office", "yoga", "fitness", "sport", "colorful", "rainbow", "cute", "puppy", "kitten",
)
# --- AI GORSEL STILI (Pollinations ucretsiz AI -> videonun konusunu BIREBIR cizer, garantili konuya ozgu) ---
_AI_STIL  = "dark mysterious, eerie, cinematic, moody dramatic lighting, realistic, highly detailed, suspenseful atmosphere"
_AI_MODEL = "flux"
# Aramaya eklenecek KANALA OZGU atmosfer (Pixabay STOK yedeginde siralamayi konuya yaklastirir)
_ATMOSFER = "dark mysterious eerie cinematic"
_TEMA_KELIMELER = ("dark", "night", "fog", "mist", "shadow", "abandoned", "forest", "storm", "snow",
                   "mountain", "ocean", "cave", "old", "ruins", "graveyard", "document", "road", "eerie",
                   "mysterious", "winter", "rain", "cliff", "wreck")


def _yasak_mi(tags):
    t = (tags or "").lower()
    return any(y in t for y in _YASAK_ETIKET)


def _atmosfer_ekle(q):
    """Her aramaya kanalin temasini ekle -> alakasiz (cicek/bocek/gunduz doga) gorsel gelmesin."""
    ql = (q or "").lower()
    if any(w in ql for w in _TEMA_KELIMELER):
        return q + " cinematic"               # zaten tema var -> hafif pekistir
    return q + " " + _ATMOSFER                  # nötr sorgu -> tam tema atmosferi ekle


# ULTRA-GENEL kelimeler tek basina alakasiz sonuc getirir -> ikincil sayilir
_COK_GENEL = set("stone light water gold golden nature landscape scenery background texture wallpaper "
                 "abstract sunset sunrise cloud clouds grass tree trees field river lake ocean sea beach coast coastal cliff shore waves wave island seaside harbor "
                 "sky sun rock rocks mountain hill wall dust smoke".split())

_KONU_FILLER = set("cinematic close aerial slow motion shot footage view scene epic dramatic dark night "
                   "moody light lighting high detailed realistic photorealistic".split()) | set(_ATMOSFER.lower().split())


def _konu_kelimeleri(q):
    """RAW sorgudaki KONU kelimeleri (adam ne anlatiyorsa). Ultra-genel kelimeler ikincil."""
    kel = [w for w in re.findall(r"[a-z]{4,}", (q or "").lower()) if w not in _KONU_FILLER]
    ozel = [w for w in kel if w not in _COK_GENEL]
    return ozel if ozel else kel


_AKTIF_KONU = []   # o an aranan sahnenin KONU kelimeleri (STRICT eslesme)


def _temiz_hits(hits, q=""):
    """KONU varsa SADECE o konuyla eslesen stok'u kabul et; yoksa BOS -> caller AI'ya gecer."""
    temiz = [h for h in hits if not _yasak_mi(h.get("tags", ""))]
    if _AKTIF_KONU:
        # 1) EN SPESIFIK kelime (sorgunun ilki = anlatilan asil nesne) tag'lerde geciyor mu?
        ana = _AKTIF_KONU[0]
        tam = [h for h in temiz if ana in (h.get("tags", "") or "").lower()]
        if tam:
            return tam[:25]
        # 2) yoksa EN AZ 2 konu kelimesi tutmali (tek zayif kelimeyle alakasiz gorsel GELMESIN)
        cok = [h for h in temiz
               if sum(1 for w in _AKTIF_KONU if w in (h.get("tags", "") or "").lower()) >= 2]
        return cok[:25]   # o da yoksa BOS -> AI konuyu birebir cizer
    if not temiz:
        temiz = hits
    uygun = [h for h in temiz if any(w in (h.get("tags", "") or "").lower() for w in _TEMA_KELIMELER)]
    return (uygun or temiz)[:25]


_KULLANILAN_MEDYA = set()   # bu kosuda + gecmiste kullanilan medya url'leri (tekrar onleme)


def _tekrarsiz_url(fn, q):
    """DAHA ONCE KULLANILMIS url ASLA donmez. Hepsi kullanilmissa None -> caller AI'ya gecer.
    (Eskiden 8 deneme sonunda kullanilmis url donuyordu; ayni klip 3-4 video sonra TEKRAR ediyordu.)"""
    for _ in range(6):
        u = fn(q)
        if not u:
            return None
        if u not in _KULLANILAN_MEDYA:
            return u
    return None   # havuzdaki her sey kullanilmis -> TEKRAR ETME, AI cizsin


def _ai_gorsel(query, hedef):
    """Pollinations (ucretsiz AI) ile sorguyu BIREBIR cizen dikey 1080x1920 gorsel uretir.
    Konuya %100 ozel -> alakasiz stok (cicek/bocek/sacma manzara) IMKANSIZ. Basarisizsa None."""
    import urllib.parse
    prompt = f"{query}, {_AI_STIL}"
    for deneme in range(2):                       # 2 deneme (ara sira gec/yogun olabilir)
        seed = random.randint(1, 999999)
        url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt) +
               f"?width=1080&height=1920&nologo=true&seed={seed}&model={_AI_MODEL}")
        try:
            r = _http_get(url, timeout=90)
            ct = r.headers.get("Content-Type", "")
            if r.status_code == 200 and ct.startswith("image"):
                with open(hedef, "wb") as f:
                    f.write(r.content)
                if os.path.getsize(hedef) > 12000:   # gecerli gorsel
                    return hedef
                os.remove(hedef)
        except Exception as e:
            print("    (ai gorsel denemesi basarisiz:", e, ")")
    return None


def arka_plan_indir(sorgular):
    """
    Her sorgu icin ONCE AI ile konuyu BIREBIR cizer (Pollinations); olmazsa STOK'a duser
    (Pixabay video/foto -> filtreli). Konuya ozgu gorsel GARANTI. [(yol, tur), ...] dondurur.
    """
    global _KULLANILAN_MEDYA, _AKTIF_KONU
    umf = os.path.join(BASE_DIR, "kullanilan_gorseller.txt")
    _KULLANILAN_MEDYA = set()
    if os.path.exists(umf):
        try:
            with open(umf, "r", encoding="utf-8") as f:
                _KULLANILAN_MEDYA = {ln.strip() for ln in f if ln.strip()}
        except OSError:
            pass

    os.makedirs(MEDYA_KLASORU, exist_ok=True)
    for eski in os.listdir(MEDYA_KLASORU):
        try:
            os.remove(os.path.join(MEDYA_KLASORU, eski))
        except OSError:
            pass

    medya = []
    for i, q in enumerate(sorgular):
        _AKTIF_KONU = _konu_kelimeleri(q)        # bu sahnenin KONUSU
        qa = _atmosfer_ekle(q)
        hedef_ai = os.path.join(MEDYA_KLASORU, f"m_{i:02d}.jpg")
        print(f"  Gorsel [{i+1}/{len(sorgular)}]: '{q}'  (konu: {' '.join(_AKTIF_KONU) or '-'})")
        # ILK sahne = ana konu -> AI birebir ciz (isimli nesne MUTLAKA gorunsun)
        if i == 0 and _ai_gorsel(q, hedef_ai):
            medya.append((hedef_ai, "foto"))
            print("    -> AI (ana konu birebir cizildi)")
            continue
        # SADECE konuya BIREBIR eslesen stok VIDEO (alakasiz manzara/insan gelmez)
        # 1) KONUYA BIREBIR uygun gercek HAREKETLI KLIP (en profesyonel gorunum)
        url = _tekrarsiz_url(_pixabay_video, qa) or _tekrarsiz_url(_pexels_video, qa)
        if url:
            hedef = os.path.join(MEDYA_KLASORU, f"m_{i:02d}.mp4")
            if _dosya_indir(url, hedef):
                medya.append((hedef, "video"))
                _KULLANILAN_MEDYA.add(url)
                try:
                    with open(umf, "a", encoding="utf-8") as f:
                        f.write(url + "\n")
                except OSError:
                    pass
                print("    -> KLIP (konuya BIREBIR uygun hareketli video)")
                continue
        # 2) uygun klip YOKSA -> AI konuyu BIREBIR cizer (sinematik zoom+kaydirma ile klip gibi akar)
        _AKTIF_KONU = []
        if _ai_gorsel(q, hedef_ai):
            medya.append((hedef_ai, "foto"))
            print("    -> AI gorsel (konuya ozel, sinematik hareketli)")
            continue
        # 3) SON CARE: konuya uygun stok foto
        _AKTIF_KONU = _konu_kelimeleri(q)
        url = _tekrarsiz_url(_pixabay_foto, qa) or _tekrarsiz_url(_pexels_foto, qa)
        if url:
            hedef = os.path.join(MEDYA_KLASORU, f"m_{i:02d}.jpg")
            if _dosya_indir(url, hedef):
                medya.append((hedef, "foto"))
                _KULLANILAN_MEDYA.add(url)
                try:
                    with open(umf, "a", encoding="utf-8") as f:
                        f.write(url + "\n")
                except OSError:
                    pass
                print("    -> STOK FOTO (son care)")
                continue
        print("    -> bulunamadi, atlaniyor")

    print(f"  Toplam {len(medya)} arka plan medyasi hazir.")
    return medya


# =========================================================
#  5) MoviePy ile video kurgusu + altyazi
# =========================================================
def _fit_dikey(clip):
    """Klibi 1080x1920 cerceveyi tamamen kaplayacak sekilde buyutup ortadan kirpar."""
    hedef = W / H
    oran = clip.w / clip.h
    if oran > hedef:
        clip = clip.resized(height=H)
        clip = clip.cropped(x_center=clip.w / 2, width=W)
    else:
        clip = clip.resized(width=W)
        clip = clip.cropped(y_center=clip.h / 2, height=H)
    return clip


def _video_klip(path, sure):
    from moviepy import VideoFileClip, concatenate_videoclips
    v = VideoFileClip(path).without_audio()
    if v.duration < sure:                       # kisa ise dongule
        n = int(sure // v.duration) + 1
        v = concatenate_videoclips([v] * n).subclipped(0, sure)
    else:                                       # uzun ise rastgele bir yerinden kes
        s = random.uniform(0, v.duration - sure)
        v = v.subclipped(s, s + sure)
    return _fit_dikey(v).with_duration(sure)


def _foto_klip(path, sure):
    from moviepy import ImageClip, CompositeVideoClip
    base = _fit_dikey(ImageClip(path).with_duration(sure))
    try:
        # ONEMLI: cerceveden BUYUK basla (H*1.35) -> Ken Burns zoom marji olur ve klip boyutu
        # crossfade bindirmesinde ASLA cerceve altina/0'a dusmez ("height and width must be > 0" cozuldu).
        buyuk = base.resized(height=int(H * 1.45))     # genis marj -> zoom + kaydirma alani
        def _o(t):
            return max(0.0, min(1.0, t / max(sure, 0.1)))
        yon = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1)])  # her sahne farkli yon
        kay = 100                                       # kaydirma miktari (piksel)
        def _poz(t):
            o = _o(t); s = 1.0 + 0.22 * o               # belirgin sinematik zoom -> KLIP gibi hareket
            gw, gh = buyuk.w * s, buyuk.h * s
            return (W / 2 - gw / 2 + yon[0] * kay * o, H / 2 - gh / 2 + yon[1] * kay * o)
        c = buyuk.resized(lambda t: 1.0 + 0.22 * _o(t)).with_position(_poz)
        return CompositeVideoClip([c], size=(W, H)).with_duration(sure)
    except Exception:
        return base


def _yedek_arka_plan(sure):
    """Internetten hic medya gelmezse: yerel klasordeki video, o da yoksa duz koyu ekran."""
    from moviepy import VideoFileClip, concatenate_videoclips, ColorClip
    if os.path.isdir(YEDEK_VIDEO_KLASORU):
        vids = [os.path.join(YEDEK_VIDEO_KLASORU, f) for f in os.listdir(YEDEK_VIDEO_KLASORU)
                if f.lower().endswith((".mp4", ".mov", ".mkv", ".webm", ".avi"))]
        if vids:
            print("  (internet medyasi yok -> yerel yedek video kullaniliyor)")
            return _video_klip(random.choice(vids), sure)
    print("  (hic gorsel yok -> duz koyu arka plan kullaniliyor)")
    return ColorClip(size=(W, H), color=(15, 15, 20)).with_duration(sure)


def _arka_plan_montaj(medya, sure):
    from moviepy import concatenate_videoclips, vfx
    if not medya:
        return _yedek_arka_plan(sure)

    medya = medya[:8]                           # cok fazla olmasin
    n = len(medya)
    gecis = 0.5                                 # sahneler arasi yumusak crossfade (sinematik)

    if n == 1:
        path, tur = medya[0]
        return _video_klip(path, sure) if tur == "video" else _foto_klip(path, sure)

    her = max(1.8, (sure + (n - 1) * gecis) / n)   # crossfade cakismasini hesaba kat

    sahneler = []
    for path, tur in medya:
        try:
            sahneler.append(_video_klip(path, her) if tur == "video" else _foto_klip(path, her))
        except Exception as e:
            print("  (bir medya atlandi:", e, ")")

    if not sahneler:
        return _yedek_arka_plan(sure)
    if len(sahneler) == 1:
        return sahneler[0].with_duration(sure)

    try:
        # ilk sahne olduğu gibi, sonrakiler yumusak crossfade ile girsin
        sahneler = [sahneler[0]] + [s.with_effects([vfx.CrossFadeIn(gecis)]) for s in sahneler[1:]]
        bg = concatenate_videoclips(sahneler, method="compose", padding=-gecis)
    except Exception as e:
        print("  (crossfade kurulamadi, duz birlestirme:", e, ")")
        bg = concatenate_videoclips(sahneler, method="compose")

    # tam sese esitle: kisa ise dongule, uzun ise kes
    if bg.duration < sure:
        tekrar = int(sure // bg.duration) + 1
        bg = concatenate_videoclips([bg] * tekrar, method="compose")
    return bg.subclipped(0, sure)


def _altyazi_klipleri(words, font_path):
    from moviepy import TextClip
    kutu_g = int(W * 0.9)
    kutu_y = 420                                # SABIT yukseklik -> harf/kenarlik KIRPILMAZ (yarim cikma sorunu cozuldu)
    x0 = (W - kutu_g) // 2                       # yatayda ortala
    y0 = int(H * SUBTITLE_Y - kutu_y / 2)        # kutuyu SUBTITLE_Y oranina gore dikeyde ortala
    klipler = []
    for g in kelime_gruplari(words, WORDS_PER_CHUNK):
        sure = max(0.15, g["end"] - g["start"])
        # HOOK VURGUSU: ilk 2.5 sn (hook) daha BUYUK punto -> ilk 2 saniye guclu dikkat ceker (profesyonel)
        fs = int(FONT_SIZE * 1.15) if g["start"] < 2.5 else FONT_SIZE
        # Sabit kutu + yazi kutunun icinde tam ortalanir -> ust/alt bol bosluk, hicbir harf kesilmez
        ortak = dict(font=font_path, text=g["text"], font_size=fs, method="caption",
                     size=(kutu_g, kutu_y), text_align="center",
                     horizontal_align="center", vertical_align="center")

        # Golge (derinlik + okunurluk)
        golge = (TextClip(color="black", **ortak)
                 .with_start(g["start"]).with_duration(sure)
                 .with_position((x0 + 5, y0 + 5)).with_opacity(0.45))
        # Ana sari yazi + kalin siyah kenarlik
        ana = (TextClip(color=TEXT_COLOR, stroke_color=STROKE_COLOR, stroke_width=STROKE_WIDTH, **ortak)
               .with_start(g["start"]).with_duration(sure)
               .with_position((x0, y0)))

        klipler.append(golge)
        klipler.append(ana)
    return klipler


def _marka_klipleri(dur, font_path):
    """Kose logosu (kalici) + animasyonlu ABONE OL cagrisi (orta + son) -> abone tesviki."""
    from moviepy import ImageClip, TextClip, vfx
    klipler = []
    if not os.path.exists(LOGO_PATH):
        return klipler
    try:
        # 1) KOSE LOGOSU (sol ust, kucuk, hafif saydam, TUM video boyunca)
        kb = int(W * 0.13)
        klipler.append(ImageClip(LOGO_PATH).resized((kb, kb))
                       .with_duration(dur).with_position((36, 40)).with_opacity(0.82))

        # 2) ABONE OL CAGRISI (logo + yazi, fade in/out animasyonlu; altyazilarin USTUNDE, ust ucte)
        lb = int(W * 0.20)
        yaz_y = int(H * 0.30) + lb - 6
        def cta(basla, sure=3.2):
            lg = (ImageClip(LOGO_PATH).resized((lb, lb))
                  .with_start(basla).with_duration(sure)
                  .with_position(("center", int(H * 0.30)))
                  .with_effects([vfx.CrossFadeIn(0.4), vfx.CrossFadeOut(0.4)]))
            yz = (TextClip(font=font_path, text=ABONE_YAZI, font_size=78, color="yellow",
                           stroke_color="black", stroke_width=7, method="caption",
                           size=(int(W * 0.8), 130), horizontal_align="center", vertical_align="center")
                  .with_start(basla).with_duration(sure)
                  .with_position(("center", yaz_y))
                  .with_effects([vfx.CrossFadeIn(0.4), vfx.CrossFadeOut(0.4)]))
            return [lg, yz]
        klipler += cta(dur * 0.45)                 # ortada bir kez
        if dur > 9:
            klipler += cta(max(dur - 4.2, dur * 0.6))   # sona dogru bir kez daha
    except Exception as e:
        print("  (marka/abone klibi atlandi:", e, ")")
    return klipler


def video_olustur(words, medya, out_path):
    from moviepy import AudioFileClip, CompositeVideoClip

    # Font kontrolu (gomulu Anton yoksa -> Windows -> Linux/bulut fontlarina gec)
    font_path = FONT_PATH
    if not os.path.exists(font_path):
        for alt in [
            r"C:\Windows\Fonts\impact.ttf", r"C:\Windows\Fonts\ariblk.ttf",
            r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]:
            if os.path.exists(alt):
                font_path = alt
                break

    audio = AudioFileClip(AUDIO_FILE)
    dur = audio.duration

    bg = _arka_plan_montaj(medya, dur)
    altyazilar = _altyazi_klipleri(words, font_path)
    marka = _marka_klipleri(dur, font_path)        # kose logosu + abone cagrisi

    final = CompositeVideoClip([bg, *altyazilar, *marka], size=(W, H))
    final = final.with_audio(audio).with_duration(dur)

    final.write_videofile(
        out_path, fps=30, codec="libx264", audio_codec="aac",
        threads=4, preset="medium",   # ilerleme % cubugu terminalde gorunsun diye logger acik
    )

    audio.close()
    bg.close()
    final.close()


# =========================================================
#  6) YouTube Data API v3 ile yukle (Private)
# =========================================================
def youtube_yukle(dosya, baslik, aciklama, etiket_listesi):
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": baslik[:100],
            "description": aciklama,
            "tags": etiket_listesi,
            "categoryId": CATEGORY_ID,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {"privacyStatus": PRIVACY, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(dosya, chunksize=-1, resumable=True, mimetype="video/mp4")
    istek = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print("  YouTube'a yukleniyor...")
    resp = None
    while resp is None:
        status, resp = istek.next_chunk()
        if status:
            print(f"    Yukleniyor: %{int(status.progress() * 100)}")
    print("  Yuklendi! Video ID:", resp["id"])
    print("  Link:", "https://youtu.be/" + resp["id"])


# =========================================================
#  7) ANA AKIS
# =========================================================
def main():
    # 1) Metinler + gorsel kelimeleri
    if MANUAL_MODE:
        script     = senaryo_metni
        baslik     = video_basligi
        aciklama   = video_aciklamasi
        etiket_lst = etiketler
        sorgular   = gorsel_sorgulari
        print("MANUEL MOD: yapistirilan senaryo kullaniliyor.")
    else:
        print("[1/5] Gemini ile konu + senaryo + gorsel kelimeleri uretiliyor...")
        data       = gemini_uret()
        script     = data["script"]
        baslik     = data["title"]
        aciklama   = data["description"]
        etiket_lst = data.get("tags", [])
        sorgular   = data.get("visual_queries", []) or etiket_lst
        print("      Konu   :", data.get("topic"))
        print("      Baslik :", baslik)
        print("      Gorsel kelimeleri:", ", ".join(sorgular))

    # 2) Seslendirme + kelime zamanlamasi
    print("[2/5] Seslendiriliyor (edge-tts)...")
    words = asyncio.run(seslendir_ve_zamanla(script, VOICE, AUDIO_FILE))
    print(f"      {len(words)} kelime seslendirildi -> {AUDIO_FILE}")
    if not words:
        raise RuntimeError("edge-tts kelime zamanlamasi dondurmedi. Senaryo bos olabilir.")

    # 3) KONUYA GORE otomatik arka plan indir
    print("[3/5] Konuya uygun arka plan medyasi indiriliyor (Pixabay/Pexels/Openverse)...")
    medya = arka_plan_indir(sorgular)

    # 4) Video + altyazi
    print("[4/5] Video kurgulaniyor (MoviePy)... (biraz surebilir)")
    video_olustur(words, medya, OUTPUT_FILE)
    print("      Video hazir ->", OUTPUT_FILE)

    # 5) YouTube
    if UPLOAD_TO_YOUTUBE:
        print("[5/5] YouTube yukleme...")
        youtube_yukle(OUTPUT_FILE, baslik, aciklama, etiket_lst)
    else:
        print("[5/5] YouTube yukleme KAPALI (UPLOAD_TO_YOUTUBE = False).")

    print("\nBITTI - tamamlandi.")


if __name__ == "__main__":
    import sys
    import traceback
    try:
        main()
    except Exception as e:
        print("\nHATA:", type(e).__name__, "-", e)
        traceback.print_exc()
        sys.exit(1)   # bu kosu basarisiz gorunur; sonraki zamanlanmis calisma normal calisir
