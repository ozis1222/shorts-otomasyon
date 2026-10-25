# -*- coding: utf-8 -*-
"""
============================================================
   YOUTUBE SHORTS OTOMASYONU  (Tam Otomatik, Yuksek Kalite)
============================================================
Hicbir ucretli/uyelikli servis KULLANILMAZ.

Akis (her calistirmada sirayla, elle hicbir sey yapmadan):
  0) KENDINI GELISTIRME -> kendi kanalinin EN COK IZLENEN videolarini ve
                           nisteki VIRAL Shorts basliklarini inceler
  1) Gemini              -> konu + senaryo + baslik + aciklama + etiket
                            + thumbnail yazisi + gorsel arama kelimeleri
                            (GECMISTEKI HICBIR KONUYU TEKRAR ETMEZ - kod garanti eder)
  2) edge-tts            -> senaryoyu Ingilizce dogal sesle okur -> ses.mp3
  3) Pixabay/Pexels/AI   -> KONUYA GORE otomatik arka plan medyasi indirir
                            (SADECE 1080x1920'yi bozmayan yuksek cozunurluk kabul edilir)
  4) Remotion (varsayilan) -> AI ile cizilen sahnelerden ANIMASYONLU 1080x1920 video:
                            kamera hareketleri, parallax, sis/toz/isik efektleri, gecisler,
                            karaoke altyazi, "CASE FILE" karti, ses efektleri + ambient
     MoviePy (yedek)       -> Remotion calismazsa eski stok-klip montaji (hat asla kirilmaz)
  5) PIL                 -> otomatik tiklanma odakli THUMBNAIL uretir
  6) YouTube Data API v3 -> videoyu yukler + thumbnail'i basar

Calistirmak icin:  python shorts_otomasyon.py
Hem yerel Windows'ta hem GitHub Actions (bulut/Linux) uzerinde calisir.

ANAHTARLAR ORTAM DEGISKENINDEN (secret) OKUNUR - koda ASLA yazma.
"""

import os
import re
import sys
import json
import math
import random
import asyncio
import datetime
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
#  1) AYARLAR
# =========================================================

# --- Gemini (UCRETSIZ: https://aistudio.google.com/apikey ) ---
#  GUVENLIK: anahtar KODA YAZILMAZ. GitHub -> Settings -> Secrets -> GEMINI_API_KEY
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL   = os.environ.get("GEMINI_MODEL") or "gemini-flash-latest"

# --- Kanalin konusu (Gemini buradan konu + gorsel kelimelerini uretir, hep INGILIZCE) ---
NICHE = ("real unsolved mysteries, unexplained events, mysterious disappearances, "
         "strange historical cases, cold cases and eerie unexplained phenomena")
# Viral arastirma icin YouTube'da aranacak kelimeler (kendi nisin)
VIRAL_SORGULARI = ["unsolved mystery shorts", "unexplained disappearance shorts",
                   "creepy true mystery shorts", "cold case shorts"]

# --- Arka plan gorselleri icin ANAHTARLAR (hepsi ucretsiz, secret'tan okunur) ---
#  * Pixabay: https://pixabay.com/api/docs/
#  * Pexels : https://www.pexels.com/api/   <-- DIKEY 4K klip icin COK ONEMLI, mutlaka ekle
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "").strip()
PEXELS_API_KEY  = os.environ.get("PEXELS_API_KEY", "").strip()

# --- Seslendirme (Ingilizce dogal erkek sesi) ---
VOICE     = os.environ.get("VOICE") or "en-US-ChristopherNeural"  # derin/otoriter anlatici
TTS_RATE  = "+6%"     # hafif hizli -> daha enerjik, retention'a olumlu
TTS_PITCH = "-3Hz"    # bir tik daha derin -> daha otoriter/sinematik

# --- Altyazi ayarlari ---
FONT_PATH       = os.path.join(BASE_DIR, "fonts", "Anton-Regular.ttf")
WORDS_PER_CHUNK = 3
FONT_SIZE       = 115
TEXT_COLOR      = "yellow"
STROKE_COLOR    = "black"
STROKE_WIDTH    = 8
SUBTITLE_Y      = 0.72

# --- Video boyutu (Shorts = dikey) ---
W, H = 1080, 1920

# --- KALITE AYARLARI (bulanik/480p gorunumun ilaci) ---
FPS               = 30
VIDEO_BITRATE     = os.environ.get("VIDEO_BITRATE") or "16000k"  # 1080x1920 icin comert
AUDIO_BITRATE     = "192k"
# 'medium': acik bitrate zaten yuksek oldugu icin 'slow'a gore gozle gorulur kalite farki
# yok, ama 2 cekirdekli Actions makinesinde kodlama suresini yariya indiriyor.
X264_PRESET       = os.environ.get("X264_PRESET") or "medium"

# --- FAZ 2: SINEMATIK RENDER KATMANI (FFmpeg son-islem pasi) ---
# Render bitince ham videoya tek bir FFmpeg pasi uygulanir: soguk belgesel gradesi +
# film grain (temporal = hafif dogal flicker) + vignette, ve anlatim altina lavfi ile
# SENTEZLENEN (asset gerektirmeyen) derin ambient ugultu. Pas coker ozel bir durumda
# ham video oldugu gibi kullanilir -> hat asla kirilmaz.
SINEMATIK      = os.environ.get("SINEMATIK", "1") != "0"     # grade + grain + vignette
SINEMATIK_GRAIN = int(os.environ.get("SINEMATIK_GRAIN") or 7)  # 0-20; film grain siddeti
AMBIENT_SES    = os.environ.get("AMBIENT_SES", "1") != "0"   # derin ugultu ses yatagi
AMBIENT_VOL    = os.environ.get("AMBIENT_VOL") or "0.16"     # anlatimin cok altinda kalsin
VHS_MOD        = os.environ.get("VHS", "0") == "1"           # opsiyonel: arsiv/CCTV analog doku
# Bir kaynak, 1080x1920'yi doldurmak icin en fazla bu kadar BUYUTULEBILIR.
# 1.0 = hic buyutme yok (birebir/kucultme). 1.25 = en fazla %25 buyutme.
MAX_BUYUTME       = 1.25    # 1. tercih: gercek klip, kristal net
MAX_BUYUTME_ZAYIF = 1.90    # son care klipler icin gevsek esik
HEDEF_SAHNE_SN    = 3.6     # ekranda ayni goruntu en fazla bu kadar kalsin (pattern interrupt)
MAX_SAHNE         = 18      # toplam kesme sayisi ust siniri (render suresi kontrol altinda kalsin)

# --- Ken Burns (foto/AI gorseli "klip gibi" hareket ettiren sinematik zoom+kaydirma) ---
KEN_BURNS_ZOOM = 0.20   # sahne sonunda %20 zoom
KEN_BURNS_PAN  = 46     # piksel cinsinden kaydirma

# --- RENDER MOTORU ---
#  'remotion' (varsayilan): AI illustrasyonlarindan animasyon tarzi video (remotion/ klasoru)
#  'moviepy'              : eski stok-klip montaji. Remotion hata verirse otomatik buna dusulur.
RENDER_MOTORU = (os.environ.get("RENDER_MOTORU") or "remotion").strip().lower()
REMOTION_DIR  = os.path.join(BASE_DIR, "remotion")
REMOTION_RUN  = os.path.join(REMOTION_DIR, "public", "run")   # her kosuda yeniden doldurulur
# Animasyon stili: 'stickman' (varsayilan, kodla cizilen konusan cop adam) | 'illustrasyon' (AI cizimleri)
RENDER_STIL   = (os.environ.get("RENDER_STIL") or "stickman").strip().lower()
# Cloudflare Workers AI (ucretsiz FLUX): iki secret da varsa sahneler hikayeye ozel cizilir
CF_HESAP = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
CF_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
# FLUX.2 Klein 4B: dikey boyut destekler (multipart, genislik/yukseklik 256-1920). 864x1536 = tam 9:16,
# 6 karo ~ 160 neuron -> gunluk ucretsiz kotayla ~60 gorsel. Hata olursa FLUX.1 schnell (kare) yedek.
CF_MODEL = os.environ.get("CF_GORSEL_MODEL") or "@cf/black-forest-labs/flux-2-klein-4b"
CF_YEDEK_MODEL = "@cf/black-forest-labs/flux-1-schnell"
ANIM_MIN_GORSEL = 4      # bundan az AI gorseli cikarsa stok medyaya (klip/foto) gecilir
ANIM_ISTEK_ARASI_SN = 6  # Pollinations hiz siniri: basarili kareler arasinda kisa bekleme
ANIM_GORSEL_BUTCE_SN = 14 * 60   # tum karelere ayrilan en uzun sure (60 dk is limiti icin)

# --- AI gorsel (Pollinations, ucretsiz) ---
AI_BOYUTLARI = [(1440, 2560), (1080, 1920)]   # once yuksek coz., olmazsa normal

# --- Otomatik indirilen medyalarin gecici klasoru ---
MEDYA_KLASORU = os.path.join(BASE_DIR, "medya_gecici")
YEDEK_VIDEO_KLASORU = os.path.join(BASE_DIR, "arka_plan_videolar")

# --- MANUEL MOD (True yaparsan Gemini kullanmaz, asagidakileri kullanir) ---
MANUAL_MODE      = os.environ.get("MANUAL_MODE", "0") == "1"
senaryo_metni    = """Buraya kendi senaryonu yapistirabilirsin (yalnizca MANUAL_MODE = True ise kullanilir)."""
video_basligi    = "My Video Title #Shorts"
video_aciklamasi = "My description here. #Shorts"
etiketler        = ["shorts", "facts"]
thumbnail_yazisi = "NEVER FOUND"
gorsel_sorgulari = ["dark foggy forest night", "abandoned building at night", "old mysterious documents",
                    "snowy mountains blizzard", "empty dark road at night", "misty graveyard night"]

# --- YouTube ---
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")
TOKEN_FILE         = os.path.join(BASE_DIR, "token.json")
CATEGORY_ID        = "27"       # 27=Education, 24=Entertainment, 22=People & Blogs
PRIVACY            = os.environ.get("PRIVACY") or "public"
UPLOAD_TO_YOUTUBE  = os.environ.get("UPLOAD_TO_YOUTUBE", "1") != "0"

YT_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",     # video yukleme
    "https://www.googleapis.com/auth/youtube.readonly",   # kendi istatistiklerini okuma (ogrenme)
    "https://www.googleapis.com/auth/yt-analytics.readonly",  # haftalik analiz (kanal_analiz.py)
]

# --- Marka / Abone ol ---
LOGO_PATH  = os.path.join(BASE_DIR, "assets", "logo.png")
ABONE_YAZI = "SUBSCRIBE"
SONRAKI_YAZI = "WATCH NEXT"     # izleyiciyi diger videolara yonlendiren kapanis CTA'si

# --- Cikti dosyalari ---
AUDIO_FILE       = os.path.join(BASE_DIR, "ses.mp3")
OUTPUT_FILE      = os.path.join(BASE_DIR, "shorts_hazir.mp4")
THUMB_FILE       = os.path.join(BASE_DIR, "thumbnail.jpg")

# --- Kalici hafiza dosyalari (GitHub Actions bunlari repoya geri commit eder) ---
GECMIS_FILE      = os.path.join(BASE_DIR, "gecmis.json")              # uretilen tum konular
PERFORMANS_FILE  = os.path.join(BASE_DIR, "performans.json")          # kendi videolarinin izlenmesi
VIRAL_FILE       = os.path.join(BASE_DIR, "viral_ornekler.json")      # nisteki viral basliklar
KULLANILAN_GORSEL_FILE = os.path.join(BASE_DIR, "kullanilan_gorseller.txt")
ESKI_KONU_FILE   = os.path.join(BASE_DIR, "kullanilan_konular.txt")   # eski surumden gecis icin

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")


# =========================================================
#  2) KALICI HAFIZA + TEKRAR ENGELLEME
#     "Ayni hikaye ASLA olmasin" garantisi burada kuruluyor.
# =========================================================

# YAYGIN kelimeler: iki konuda ortak cikmalari "ayni hikaye" anlamina GELMEZ.
# (Buradaki amac, 'expedition' ortak diye gecerli bir konuyu yanlislikla reddetmemek;
#  buna karsilik 'dyatlov', 'roanoke', 'celeste' gibi OZEL ISIMLER tekrari yakalamak.)
_YAYGIN = set("""
mystery mysteries mysterious unsolved unexplained strange eerie creepy chilling case cases cold true
real story stories incident incidents event events disappearance disappearances vanished vanishing
vanish missing lost gone death deaths died killed murder murders found never that this what who why
how happened history historical ancient night dark secret secrets famous shocking bizarre haunted
ghost ghosts shorts short video youtube people person unknown
the and for with from into over under security cameras cctv footage anomaly anomalies tape tapes
recording recordings recorder voicemail phone signal message radio route road highway street house
room midnight clock vault woods forest creek river lake mountain island village town hospital hotel
school office station railyard tunnel basement attic window mirror photo photograph caught captured
running shows showed inside outside
about above after again ahead alive alone along another answer answers appear appeared around arrive
artifact artifacts asleep attack autumn awake based beach became become before began behind being
believe below beneath beside between beyond black blood board boat bodies body bones border bottom
bridge bright broken brother build building buried burned cabin called camera camp canyon captain
carried castle cause caused cave center century chain chamber chance change chapel chief child
children church city claim claims clear cliff close cloud coast collapse color common complete
computer contact continue could country couple court cover crash crew cross crowd daughter dead
decade decades deep depth desert detail details device discover discovered disappear distance doctor
document documents door doubt dozen drift drive during earth edge empty engine enter entire escape
evening every evidence exist existed expedition expeditions explain explained explore extreme family
father feet field fifty final find fire first fishing flight floor force forest forever four friend
front frozen further giant girl glass government grave great green ground group guard half hand
harbor hidden high hill house human hundred hunter image inside island journey jungle keep killer
king know lake land large last late later leave left legend letter letters level light like line
little live local lock long look machine made major make many mark mass master member members
message metal meter middle might mile miles military mind mine minute modern moment money month moon
morning mother mount mountain mountains move much museum must name national native nature near need
news next nine north note nothing notice number ocean officer official often only open order other
outside over pain part pass past path perfect perhaps photo photos picture piece pilot place plane
plant point police port power present press prison probably problem project proof public question
questions quiet radio rain reach read ready reason record records region remain remains report
rescue research rest result return reveal revealed river road rock roman room rope route ruin ruins
rule safe sail sailor same sand save scene school science scientist scientists search second section
seem sent series service seven several shadow ship ships shore should show side sight sign signal
silence since single sink sister site size sleep small snow soldier soldiers solve some soon sound
source south space speak special spot stand star start state station stay step still stone stop
storm stream street strike structure study submarine such sudden summer support surface survive
survived system table take taken team tell temple term test thing think third thousand three through
time today together told tomb took total tower town trace track trail train travel tree trip truck
turn twenty under until upon valley value vessel village visit voice wall want watch water wave week
well went west when where which while white whole whose wide wild wind window winter within without
witness witnesses woman women wood word work world would wreck wreckage write wrong year years young
anomaly anomalies apparition cryptid phenomenon phenomena paranormal supernatural unidentified
encounter encounters sighting sightings abduction conspiracy theory theories investigation
investigator detective forensic autopsy coroner verdict testimony survivor victim victims suspect
murderer trace trapped rumor rumors legend legends folklore urban creature creatures monster
million billion trillion defies defied terrifying creepiest eeriest impossible disturbing
forgotten legally banned locked walked wearing sacrificed destroyed burning burned erase erased
tried kept stopped overnight alive rained raining object objects condition conditions scientific
american european african asian australian english british scottish irish french german spanish
italian greek japanese chinese brazilian mexican egyptian indian eastern western northern southern
""".split())

# NOT: 'arctic', 'pacific', 'siberia' gibi YER adlari bilerek jenerik SAYILMADI.
# Olculdu: yer adlarini jenerik yapinca yanlis alarm sifirlaniyor ama kanaldaki
# "Arktik hayalet kasaba" tekrari (3 video) yakalanamaz hale geliyordu.
# Tercih: tekrari kacirmaktansa ara sira gecerli bir konuyu reddetmek daha iyi -
# reddin bedeli tek bir yeniden uretim denemesi, kacirmanin bedeli tekrar video.

# Vaka kimligi tasiyan kelimeler BILEREK _YAYGIN'a alinmadi. Ornegin bu kanalda
# 'masks' (Kursun Maskeler), 'lighthouse' (Flannan Isles), 'artifact', 'hammer',
# 'blobs' (Oakville) tam da tekrar eden vakalari isaret ediyor; jenerik sayilsalardi
# ayni hikayenin dorduncu kez cikmasini engelleyemezdik.


def _kelime_kumesi(metin):
    """Karsilastirma icin metni anlamli kelime kumesine cevirir."""
    return {w for w in re.findall(r"[a-z0-9]{3,}", (metin or "").lower()) if w not in _YAYGIN}


def _ozel_isimler(metin):
    """
    Konudaki AYIRT EDICI kelimeler: yaygin sozlukte olmayan, 5+ harfli kelimeler.
    Pratikte bunlar vaka adlaridir -> 'dyatlov', 'roanoke', 'celeste', 'tunguska', 'voynich'.
    Iki konuda ayni ayirt edici kelime varsa AYNI HIKAYEDIR.
    """
    return {w for w in re.findall(r"[a-z]{5,}", (metin or "").lower()) if w not in _YAYGIN}


def _jaccard(a, b):
    A, B = _kelime_kumesi(a), _kelime_kumesi(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def _normalize(s):
    """Birebir-ayni karsilastirmasi icin metni sadelestirir: hashtag'leri at, kucuk
    harfe indir, harf/rakam disindaki her seyi bosluga cevir.
    Boylece 'Same Title #Shorts' ile 'same title!' AYNI kabul edilir."""
    s = re.sub(r"#\w+", " ", (s or "").lower())
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def gecmisi_oku():
    """gecmis.json -> [{topic,title,hook,tarih,video_id}, ...]"""
    kayitlar = []
    if os.path.exists(GECMIS_FILE):
        try:
            with open(GECMIS_FILE, "r", encoding="utf-8") as f:
                veri = json.load(f)
            kayitlar = veri.get("videolar", []) if isinstance(veri, dict) else list(veri)
        except Exception as e:
            print("  (gecmis.json okunamadi, bos kabul edildi:", e, ")")
    # Eski surumden gecis: kullanilan_konular.txt varsa onu da hafizaya kat
    if os.path.exists(ESKI_KONU_FILE):
        try:
            with open(ESKI_KONU_FILE, "r", encoding="utf-8") as f:
                for satir in f:
                    satir = satir.strip()
                    if satir and not any(k.get("topic") == satir for k in kayitlar):
                        kayitlar.append({"topic": satir, "title": "", "hook": "", "tarih": ""})
        except OSError:
            pass
    return kayitlar


def gecmisi_kanaldan_tohumla(performans):
    """
    Kanalda ZATEN YAYINLANMIS videolarin basliklarini hafizaya ekler.
    Boylece otomasyon, gecmis.json'dan onceki donemde yuklenmis bir hikayeyi
    de asla tekrar anlatmaz. (Sadece eksik olanlari ekler, tekrar yazmaz.)
    """
    if not performans or not performans.get("tum_basliklar"):
        return 0
    kayitlar = gecmisi_oku()
    varolan = {(k.get("title") or "").strip().lower() for k in kayitlar}
    varolan |= {(k.get("topic") or "").strip().lower() for k in kayitlar}
    eklenen = 0
    for b in performans["tum_basliklar"]:
        temiz = re.sub(r"#\w+", "", b or "").strip()
        if not temiz or temiz.lower() in varolan:
            continue
        kayitlar.append({"topic": temiz, "title": b, "hook": "",
                         "tarih": "", "video_id": "", "kaynak": "kanal"})
        varolan.add(temiz.lower())
        eklenen += 1
    if eklenen:
        try:
            with open(GECMIS_FILE, "w", encoding="utf-8") as f:
                json.dump({"guncelleme": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                           "videolar": kayitlar}, f, ensure_ascii=False, indent=1)
            print(f"      Kanaldaki {eklenen} yayinlanmis video hafizaya eklendi (tekrar edilmeyecek)")
        except OSError as e:
            print("  (gecmis.json yazilamadi:", e, ")")
    return eklenen


def gecmise_ekle(kayit):
    kayitlar = gecmisi_oku()
    kayitlar.append(kayit)
    try:
        with open(GECMIS_FILE, "w", encoding="utf-8") as f:
            json.dump({"guncelleme": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       "videolar": kayitlar}, f, ensure_ascii=False, indent=1)
    except OSError as e:
        print("  (gecmis.json yazilamadi:", e, ")")


def tekrar_mi(konu, baslik, hook, gecmis, kati=True, aciklama=""):
    """
    Uretilen fikir gecmistekilerden biriyle AYNI/COK BENZER mi?
    Tekrar ise sebebi yazan bir metin, degilse None doner.

    HER ZAMAN uygulanan (vazgecilmez, kati/gevsek fark etmez) kurallar:
      * Ayni AYIRT EDICI kelime (vaka adi) iki konuda da geciyorsa -> AYNI HIKAYE.
      * BASLIK gecmisteki bir baslikla birebir (normalize edilmis) ayni ya da
        cok benzer -> tekrar. Ayni baslik ASLA iki kez cikmaz.
      * ACIKLAMA gecmistekiyle birebir ayni ya da cok benzer -> tekrar. Ayni
        aciklama ASLA iki kez cikmaz.
    kati=True iken konu/hook icin ek (daha siki) benzerlik esikleri de uygulanir.
    kati=False son denemelerde kullanilir: yukaridaki 'asla' kurallari yine
    uygulanir, sadece yakin-tema konu esigi biraz gevser ki uretim kilitlenmesin.
    """
    yeni_isim = _ozel_isimler(konu) | _ozel_isimler(baslik)
    yeni_baslik_n = _normalize(baslik)
    yeni_aciklama_n = _normalize(aciklama)
    for k in gecmis:
        eski_konu = k.get("topic", "") or ""
        eski_baslik = k.get("title", "") or ""
        eski_aciklama = k.get("description", "") or ""
        eski_isim = _ozel_isimler(eski_konu) | _ozel_isimler(eski_baslik)

        cakisan = yeni_isim & eski_isim
        if cakisan:
            hedef = eski_konu or eski_baslik
            return f"'{hedef}' ile ayni vaka adi geciyor: {', '.join(sorted(cakisan))}"

        # BASLIK -> her iki modda da ASLA tekrar etmesin
        if eski_baslik and yeni_baslik_n:
            if yeni_baslik_n == _normalize(eski_baslik):
                return f"'{eski_baslik}' ile birebir ayni baslik"
            if _jaccard(baslik, eski_baslik) >= (0.55 if kati else 0.65):
                return f"'{eski_baslik}' basligiyla cok benzer"

        # ACIKLAMA -> her iki modda da ASLA tekrar etmesin
        if eski_aciklama and yeni_aciklama_n:
            if yeni_aciklama_n == _normalize(eski_aciklama):
                return f"'{eski_konu or eski_baslik}' ile birebir ayni aciklama"
            if _jaccard(aciklama, eski_aciklama) >= (0.60 if kati else 0.70):
                return f"'{eski_konu or eski_baslik}' aciklamasiyla cok benzer"

        if kati:
            if _jaccard(konu, eski_konu) >= 0.40:
                return f"'{eski_konu}' konusuyla cok benzer"
            if k.get("hook") and hook and _jaccard(hook, k["hook"]) >= 0.55:
                return f"'{k['hook']}' hook'uyla cok benzer"
        else:
            if _jaccard(konu, eski_konu) >= 0.60:
                return f"'{eski_konu}' konusuyla neredeyse ayni"
    return None


# --- HOOK KALITE KONTROLU (ilk 2 saniye = videonun kaderi) ---
_YASAK_HOOK_BAS = (
    "imagine", "today", "welcome", "in this video", "have you ever", "did you know",
    "let me tell", "picture this", "this is the story", "hey ", "what if i told",
    "here's", "here is", "so ", "well ", "okay", "alright", "once upon",
)


def _ilk_cumle(metin):
    m = re.split(r"(?<=[.!?])\s+", (metin or "").strip())
    return m[0].strip() if m else ""


def hook_sorunu(script):
    """Hook zayifsa sebebini doner, saglamsa None.
    Ilk cumle videonun kaderidir. Reddedilir: cok uzun/kisa, klise kalip, SORU ile
    acilis, ya da TARIH (yil/ay) ile acilis. Hedef: dogrudan CELISKI ile baslamak."""
    hook = _ilk_cumle(script)
    if not hook:
        return "senaryo bos"
    kelime = len(hook.split())
    if kelime > 15:
        return f"hook cok uzun ({kelime} kelime, en fazla 15 olmali)"
    if kelime < 4:
        return f"hook cok kisa ({kelime} kelime)"
    dusuk = hook.lower()
    for y in _YASAK_HOOK_BAS:
        if dusuk.startswith(y):
            return f"hook yasak kalipla basliyor: '{y.strip()}'"
    # SORU ile acilis yasak: izleyiciyi durduran sey cevap degil, celiskidir
    if hook.rstrip().endswith("?"):
        return "hook soru ile aciliyor (celiski ile acilmali)"
    # TARIH ile acilis yasak: 'In 1972,' / 'On March 3,' / '1972 ...'
    if re.match(r"^(in|on|by|during|back in)\s+(the\s+)?(17|18|19|20)\d\d\b", dusuk):
        return "hook tarihle (yil) aciliyor"
    if re.match(r"^(in|on)\s+(january|february|march|april|may|june|july|august|"
                r"september|october|november|december)\b", dusuk):
        return "hook tarihle (ay) aciliyor"
    if re.match(r"^(17|18|19|20)\d\d\b", dusuk):
        return "hook yil ile aciliyor"
    return None


# --- ASIRI KULLANILAN KELIME / KLISE YASAGI ---
# Kanal 'hep ayni video' gibi gorunmesin diye: olayi ETIKETLEME, olayin kendisini anlat.
# Asagidaki kelime/kaliplar SCRIPT ve BASLIKTA yasak; gecerse fikir yeniden uretilir.
YASAK_KELIMELER = [
    "vanished", "vanish", "vanishes", "vanishing",
    "disappeared", "disappear", "disappears", "disappearance", "disappearances",
    "unsolved", "missing",
    "lost forever", "gone without a trace", "without a trace",
    "nobody knows", "no one knows", "the mystery remains", "remains a mystery",
    "to this day", "never found", "never seen again", "never to be seen",
]


def _yasak_kelime_var(*metinler):
    """Metinlerde asiri kullanilan klise kelime/kalip varsa ilkini, yoksa None doner.
    Tek kelimeler kelime-siniriyla, bosluklu kaliplar dogrudan aranir."""
    bir = " ".join((m or "") for m in metinler).lower()
    for k in YASAK_KELIMELER:
        if " " in k:
            if k in bir:
                return k
        elif re.search(r"\b" + re.escape(k) + r"\b", bir):
            return k
    return None


# --- KONU TURU ROTASYONU: art arda ayni tur gelmesin (10'da bir tekrar bile azalir) ---
KONU_TURLERI = [
    "true crime", "maritime", "aviation", "old documents", "strange object",
    "history", "radio signal", "last phone recording", "cctv footage",
    "unexplained photo", "lab finding", "archaeology", "cold case file",
    "strange experiment", "cold war file", "impossible event",
]
_KONU_TUR_ENUM = " | ".join(KONU_TURLERI)

# --- ICERIK AILELERI (ilk 30 gunluk strateji: uc yakin alan, rastgele konu karisimi yok) ---
#  gercek_vaka   : belgelenmis gizemli kaybolma vakalari (kaynak dogrulanir, gercek olarak sunulur)
#  hayatta_kalma : "sen olsan ne yapardin" gerilim/hayatta kalma senaryolari (KURGU, etiketlenir)
#  ozgun_korku   : ozgun, sinematik korku-gizem kisa hikayeleri (KURGU, etiketlenir)
# Dagilim veri/icerik_dagilimi.json'dan okunur; haftalik analiz (kanal_analiz.py) bunu performansa
# gore gunceller. Dosya yoksa esit dagilim.
AILELER = ("gercek_vaka", "hayatta_kalma", "ozgun_korku")
DAGILIM_FILE = os.path.join(BASE_DIR, "veri", "icerik_dagilimi.json")
KURGU_NOTU = "This is a fictional story, created for entertainment. Any resemblance to real events is coincidental."


def aile_dagilimi():
    varsayilan = {a: round(1 / len(AILELER), 3) for a in AILELER}
    try:
        with open(DAGILIM_FILE, encoding="utf-8") as f:
            d = json.load(f).get("agirliklar", {})
        d = {a: float(d.get(a, 0)) for a in AILELER}
        toplam = sum(d.values())
        return {a: v / toplam for a, v in d.items()} if toplam > 0 else varsayilan
    except Exception:
        return varsayilan


def aile_sec(gecmis):
    """Agirliga gore aile secer; ayni aile ust uste 3. kez secilmez (cesitlilik)."""
    zorunlu = os.environ.get("ICERIK_AILESI", "").strip()
    if zorunlu in AILELER:
        return zorunlu
    son = [k.get("aile") for k in gecmis[-2:]]
    adaylar = dict(aile_dagilimi())
    if len(son) == 2 and son[0] == son[1] and son[0] in adaylar and len(adaylar) > 1:
        adaylar.pop(son[0])
    secim = random.choices(list(adaylar), weights=list(adaylar.values()))[0]
    return secim


# Genis viral tema havuzu: her video bir DUNYA alir; son kullanilanlar tekrar secilmez.
# Amac: hep "issiz kulube + yasli adam + tuhaf nesne" cikmasin; herkesin aninda anladigi,
# gundelik ya da buyuleyici ortamlarda gecen, paylasilmaya uygun hikayeler.
TEMALAR = {
    "gercek_vaka": [
        "a passenger plane or its crew", "a ship, ghost ship or lost submarine", "a mountain or polar expedition",
        "a missing hiker in a national park", "an internet mystery or strange video posted online",
        "a person who vanished from a hotel, elevator or locked room", "a deep-sea or ocean discovery",
        "a space mission or astronaut incident", "a lighthouse, island or remote outpost", "a strange broadcast or radio signal",
        "an ancient artifact or archaeological site", "a child who vanished in plain sight", "a famous heist or vanished treasure",
        "a desert, highway or road-trip disappearance", "a military or Cold War incident", "a small town where something unexplained happened",
    ],
    "hayatta_kalma": [
        "trapped in a stuck elevator in a skyscraper at night", "lost scuba diving inside an underwater cave",
        "the last passenger on a night subway train that will not stop", "stranded on a frozen lake as the ice cracks",
        "locked inside a supermarket after closing", "alone on a sinking cruise ship", "a broken-down car on a desert highway",
        "a solo night shift in an empty hospital ward", "lost in a corn maze at night", "a capsized kayak far from shore",
        "a ski lift stopped mid-air in a blizzard", "an astronaut drifting after a spacewalk tether snaps",
        "a flooded basement during a storm", "a wrong turn into an abandoned theme park", "a submarine tour that loses power",
        "a phone at 1 percent battery in an unfamiliar city", "a mountain gondola stuck over a canyon", "a wildfire closing every road out",
    ],
    "ozgun_korku": [
        "a smart home assistant that starts giving orders", "a livestream where the chat sees something the streamer cannot",
        "a babysitting job with one strange house rule", "a hotel room that is not on the floor plan", "a night shift at a gas station",
        "a ride-share driver with the wrong destination", "a video call where the other person freezes but keeps talking",
        "an apartment where the neighbor knocks back", "a delivery app order nobody placed", "a school after hours",
        "a dashcam recording that shows a different road", "an abandoned shopping mall at night", "a voicemail from your own number",
        "a cruise ship cabin with a hidden door", "a subway station that is not on the map", "a security guard watching cameras",
        "a dating app match who knows too much", "a family photo with one extra person", "a submarine sonar contact that copies the crew",
        "an online game with a player who should not exist", "a camping trip where the tent is unzipped from outside",
    ],
}


def tema_sec(gecmis, aile, son_n=8):
    """Aileye gore tema secer; son son_n videoda kullanilan temalar disarida kalir."""
    havuz = list(TEMALAR.get(aile) or [])
    son = {k.get("tema") for k in gecmis[-son_n:] if k.get("tema")}
    adaylar = [t for t in havuz if t not in son] or havuz
    return random.choice(adaylar) if adaylar else ""


def _son_mekanlar(gecmis, n=12):
    """Son videolarin konu basliklari (mekan/premis tekrarini onlemek icin prompt'a verilir)."""
    return [k.get("topic") for k in gecmis[-n:] if k.get("topic")]


def _son_farkli_turler(gecmis, n):
    """gecmisteki SON n FARKLI konu turunu (kucuk harf, en yeniden eskiye) dondurur."""
    tur = []
    for k in reversed(gecmis):
        t = (k.get("topic_type") or "").strip().lower()
        if t and t not in tur:
            tur.append(t)
        if len(tur) >= n:
            break
    return tur


# =========================================================
#  3) KENDINI GELISTIRME KATMANI
#     a) Kendi kanalinin en cok izlenen videolari
#     b) Nisteki viral Shorts basliklari
#     Ikisi de Gemini'ye SADECE VERI olarak verilir (talimat olarak degil).
# =========================================================

_YT_SERVIS = None
_YT_READONLY = False


def youtube_servisi():
    """Tek bir yetkilendirilmis YouTube servisi uretir (yukleme + okuma icin ortak)."""
    global _YT_SERVIS, _YT_READONLY
    if _YT_SERVIS is not None:
        return _YT_SERVIS

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(TOKEN_FILE):
        # Scope'lari DOSYADAN oku -> eski (sadece upload yetkili) token'lar da calismaya devam eder
        creds = Credentials.from_authorized_user_file(TOKEN_FILE)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            from google_auth_oauthlib.flow import InstalledAppFlow
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise RuntimeError("client_secret.json yok - YouTube yetkilendirmesi yapilamiyor.")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, YT_SCOPES)
            creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    verilen = set(creds.scopes or [])
    _YT_READONLY = any(("youtube.readonly" in s) or ("youtube.force-ssl" in s) or s.endswith("/youtube")
                       for s in verilen)
    _YT_SERVIS = build("youtube", "v3", credentials=creds, cache_discovery=False)
    return _YT_SERVIS


def _temiz_baslik(s, limit=110):
    """Disaridan gelen metni (YouTube basliklari) zararsiz DUZ VERI haline getirir."""
    s = re.sub(r"[\r\n\t]+", " ", str(s or ""))
    s = re.sub(r"[{}\[\]<>`]", "", s)          # prompt'u bozacak/talimat gibi duracak isaretleri at
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s[:limit]


# Viral aramada nise UYMAYAN icerik (canli testte cizgi film / K-pop / dizi klipleri
# 'unsolved mystery' kelimesini tasidigi icin ilk siralara giriyordu)
_VIRAL_YASAK = (
    "cartoon", "anime", "kpop", "k-pop", "doraemon", "tmkoc", "drama", "episode", "gameplay",
    "minecraft", "roblox", "gta", "fortnite", "prank", "movie clip", "trailer", "song", "lyrics",
    "reaction", "tiktok compilation", "asmr", "quiz", "riddle", "can you solve", "puzzle",
)
# Nis kelimesi hic gecmiyorsa baslik bize uygun degildir
_VIRAL_GEREKLI = ("mystery", "mysteries", "unsolved", "unexplained", "disappear", "vanish",
                  "missing", "cold case", "creepy", "eerie", "haunt", "strange")


def _viral_uygun_mu(baslik):
    """Viral ornek gercekten bu nise mi ait? Degilse prompt'a hic girmemeli."""
    if not baslik:
        return False
    d = baslik.lower()
    if any(y in d for y in _VIRAL_YASAK):
        return False
    if not any(g in d for g in _VIRAL_GEREKLI):
        return False
    # Ingilizce disi basliklar (Hintce/Endonezce/Korece vb.) stil referansi olarak ise yaramaz
    harf = [c for c in baslik if c.isalpha()]
    if not harf:
        return False
    ascii_oran = sum(1 for c in harf if ord(c) < 128) / len(harf)
    return ascii_oran >= 0.9


def kanal_performansi():
    """
    Kendi kanalindaki videolari izlenmeye gore siralar.
    Donen: {"en_iyi": [...], "en_kotu": [...], "ortalama": n}
    Yetki yoksa veya hata olursa -> None (akis asla durmaz).
    """
    onbellek = {}
    if os.path.exists(PERFORMANS_FILE):
        try:
            with open(PERFORMANS_FILE, "r", encoding="utf-8") as f:
                onbellek = json.load(f)
        except Exception:
            onbellek = {}
    try:
        yt = youtube_servisi()
        if not _YT_READONLY:
            print("      (token'da 'youtube.readonly' yetkisi yok -> kendi istatistiklerin okunamiyor.")
            print("       Cozum: yenile_token.py calistirip TOKEN_JSON secret'ini guncelle.)")
            return onbellek.get("ozet")

        kanal = yt.channels().list(part="contentDetails,statistics", mine=True).execute()
        ogeler = kanal.get("items", [])
        if not ogeler:
            return onbellek.get("ozet")
        yuklemeler = ogeler[0]["contentDetails"]["relatedPlaylists"]["uploads"]

        video_idler, sayfa = [], None
        while len(video_idler) < 100:
            r = yt.playlistItems().list(part="contentDetails", playlistId=yuklemeler,
                                        maxResults=50, pageToken=sayfa).execute()
            video_idler += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
            sayfa = r.get("nextPageToken")
            if not sayfa:
                break

        veriler = []
        for i in range(0, len(video_idler), 50):
            r = yt.videos().list(part="snippet,statistics", id=",".join(video_idler[i:i + 50])).execute()
            for v in r.get("items", []):
                st = v.get("statistics", {})
                veriler.append({
                    "baslik": _temiz_baslik(v["snippet"]["title"]),
                    "izlenme": int(st.get("viewCount", 0) or 0),
                    "begeni": int(st.get("likeCount", 0) or 0),
                    "yorum": int(st.get("commentCount", 0) or 0),
                })

        if not veriler:
            return onbellek.get("ozet")

        veriler.sort(key=lambda x: x["izlenme"], reverse=True)
        ortalama = sum(v["izlenme"] for v in veriler) / len(veriler)
        ozet = {
            "en_iyi": veriler[:6],
            "en_kotu": veriler[-4:] if len(veriler) > 8 else [],
            "ortalama": round(ortalama, 1),
            "video_sayisi": len(veriler),
            # Zaten YAYINLANMIS her baslik -> tekrar engelinin tohumu
            "tum_basliklar": [v["baslik"] for v in veriler],
        }
        try:
            with open(PERFORMANS_FILE, "w", encoding="utf-8") as f:
                json.dump({"guncelleme": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                           "ozet": ozet}, f, ensure_ascii=False, indent=1)
        except OSError:
            pass
        print(f"      Kendi kanalin: {len(veriler)} video, ortalama {ortalama:,.0f} izlenme")
        return ozet
    except Exception as e:
        print("      (kanal performansi okunamadi, atlaniyor:", str(e)[:120], ")")
        return onbellek.get("ozet")


def viral_ornekleri_getir(saat_gecerlilik=20):
    """
    Nisteki EN COK IZLENEN Shorts basliklarini toplar (sadece STIL referansi olarak kullanilir).
    Kotayi bosa harcamamak icin sonucu onbellege alir.
    """
    simdi = datetime.datetime.now(datetime.timezone.utc)
    if os.path.exists(VIRAL_FILE):
        try:
            with open(VIRAL_FILE, "r", encoding="utf-8") as f:
                onb = json.load(f)
            t = datetime.datetime.fromisoformat(onb.get("guncelleme"))
            if (simdi - t).total_seconds() < saat_gecerlilik * 3600 and onb.get("basliklar"):
                print(f"      Viral ornekler onbellekten ({len(onb['basliklar'])} baslik)")
                return onb["basliklar"]
        except Exception:
            pass
    try:
        yt = youtube_servisi()
        if not _YT_READONLY:
            return []
        sonra = (simdi - datetime.timedelta(days=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
        bulunan = {}
        # 3 sorgu: filtreleme sonrasi elde yeterli ornek kalsin (sonuc 20 saat onbellekleniyor,
        # yani gunde bir kez ~300 kota birimi - yukleme basina 1600'un yaninda onemsiz)
        for q in VIRAL_SORGULARI[:3]:
            r = yt.search().list(part="snippet", q=q, type="video", videoDuration="short",
                                 order="viewCount", publishedAfter=sonra, maxResults=25,
                                 relevanceLanguage="en", regionCode="US").execute()
            idler = [i["id"]["videoId"] for i in r.get("items", []) if i.get("id", {}).get("videoId")]
            if not idler:
                continue
            d = yt.videos().list(part="snippet,statistics", id=",".join(idler)).execute()
            for v in d.get("items", []):
                iz = int(v.get("statistics", {}).get("viewCount", 0) or 0)
                baslik = _temiz_baslik(v["snippet"]["title"])
                # Alakasiz viral icerigi prompt'a SOKMA: kotu ornek, kotu yon verir
                if iz >= 300000 and _viral_uygun_mu(baslik):
                    bulunan[v["id"]] = {"baslik": baslik, "izlenme": iz}
        basliklar = sorted(bulunan.values(), key=lambda x: x["izlenme"], reverse=True)[:14]
        if basliklar:
            try:
                with open(VIRAL_FILE, "w", encoding="utf-8") as f:
                    json.dump({"guncelleme": simdi.isoformat(), "basliklar": basliklar},
                              f, ensure_ascii=False, indent=1)
            except OSError:
                pass
            print(f"      Nisteki viral ornekler: {len(basliklar)} baslik incelendi")
        return basliklar
    except Exception as e:
        print("      (viral arastirma atlandi:", str(e)[:120], ")")
        return []


# =========================================================
#  4) SEO KATMANI (baslik/aciklama/etiket) - koda GARANTI edildi
# =========================================================
SEO_SABIT_ETIKET = ['unsolved mysteries', 'true mystery', 'disappearance', 'cold case', 'unexplained', 'mystery']
SEO_HASHTAG      = ['#unsolvedmystery', '#mystery', '#unexplained', '#truestory']
# Kurgu hikayeler gercek olay gibi etiketlenmez ("true mystery", "cold case", "#truestory" yok)
SEO_KURGU_ETIKET = ['horror story', 'scary story', 'creepy story', 'fictional story', 'mystery']
SEO_KURGU_HASHTAG = ['#horrorstory', '#scarystory', '#creepy', '#mystery']
_GERCEK_GIBI = ("true mystery", "true story", "truestory", "cold case", "true crime", "real story",
                "unsolved mysteries", "disappearance")
# Izleyiciyi DIGER videolara yonlendiren sabit satir (oturum suresi = kanal buyumesi)
IZLEME_CAGRISI = ("If this one got you, the next one is even stranger - "
                  "watch more on the channel and subscribe so you never miss one.")


def _seo_duzenle(baslik, aciklama, etiketler, konu="", aile="gercek_vaka"):
    """Hashtag'i GARANTI eder, etiketleri uzun-kuyruk + kanal sabitleriyle genisletir."""
    kurgu = aile in ("hayatta_kalma", "ozgun_korku")
    ek = []
    k = (konu or "").strip().lower()
    if k and len(k) <= 40:
        ek += [k, k + " story"] if kurgu else [k, k + " explained", k + " mystery"]
    birlesik, gorulen = [], set()
    for t in list(etiketler or []) + ek + (SEO_KURGU_ETIKET if kurgu else SEO_SABIT_ETIKET):
        t = str(t).strip().lstrip("#")
        if kurgu and any(g in t.lower() for g in _GERCEK_GIBI):
            continue
        if t and t.lower() not in gorulen and 2 < len(t) <= 40:
            gorulen.add(t.lower())
            birlesik.append(t)
    birlesik = birlesik[:15]

    ac = (aciklama or "").strip()
    if IZLEME_CAGRISI not in ac:
        ac = ac + "\n\n" + IZLEME_CAGRISI
    if "#" not in ac:
        konu_hash = ["#" + t.replace(" ", "").replace("-", "") for t in birlesik[:3]]
        hepsi = list(dict.fromkeys(konu_hash + (SEO_KURGU_HASHTAG if kurgu else SEO_HASHTAG) + ["#shorts"]))
        ac = ac + "\n\n" + " ".join(hepsi[:8])
    elif "#shorts" not in ac.lower():
        ac = ac + " #shorts"
    return baslik, ac, birlesik


# =========================================================
#  5) GEMINI ile konu + senaryo + gorsel kelimeleri uret
# =========================================================
_AILE_BLOK = {
    "gercek_vaka": """--- THIS VIDEO'S CONTENT FAMILY: REAL DISAPPEARANCE CASE ---
A real, documented disappearance: a person, a group, a ship, a plane or an expedition that was really lost.
Keep it eerie and suspenseful but factual. Present unproven theories AS theories, never as fact.
It must have an English Wikipedia article: put its EXACT article title in "wikipedia_title" (it is verified
automatically; a wrong title means the idea is rejected).
""",
    "hayatta_kalma": """--- THIS VIDEO'S CONTENT FAMILY: SURVIVAL / "WHAT WOULD YOU DO" SCENARIO (FICTION) ---
An ORIGINAL fictional survival thriller told in second person or about one named fictional character:
trapped, stranded, hunted or facing an impossible choice (a sealed bunker, a stalled elevator in a blackout,
a night shift at a remote station, a broken-down car on an empty road...). Escalating danger, a hard decision,
a twist ending. Use invented first names only - NEVER real people, real crimes or real victims, and never
claim it really happened. Set "wikipedia_title" to "".
""",
    "ozgun_korku": """--- THIS VIDEO'S CONTENT FAMILY: ORIGINAL CINEMATIC HORROR-MYSTERY STORY (FICTION) ---
An ORIGINAL short horror/mystery story with ONE eerie premise, a slow-building wrongness and a chilling
final reveal (think: a perfect "two-sentence horror" stretched into a cinematic short). Invented characters
and places only - NEVER real people or real tragedies, and never present it as a true event.
No gore; dread comes from what is implied. Set "wikipedia_title" to "".
""",
}

_GERCEK_KURAL = """--- REAL CASES ONLY: THIS MUST BE A REAL, NAMED, DATED EVENT (non-negotiable) ---
- The event actually happened and is independently documented. Use the REAL full name of the person /
  ship / plane / place involved, and the REAL year (add the month or day only when it matters).
- NEVER invent or guess names, dates, places, quotes, numbers or evidence. If you are not certain the
  name and year are real and verifiable, choose a different, better-documented case.
- Favor cases with a strong, named human at the center and ONE shocking, concrete, documented detail.
"""

_KURGU_KURAL = """--- FICTION RULES (non-negotiable) ---
- Everything is invented: invented first names, invented small places (or generic real cities/terrain only).
- Do NOT reference real crimes, real victims or real disasters. Do NOT say "true story" or "this really happened".
- Give it a real story arc: setup -> rising danger -> a decision or discovery -> a twist the viewer did not see coming.
"""


def _prompt_kur(gecmis, performans, viraller, reddedilenler, aile="gercek_vaka", tema=""):
    # TUM gecmis verilir: eskiden sadece son 150 konu gidiyordu, model daha eskileri (Oakville,
    # Gloria Ramirez, L-8, McCabe...) tekrar oneriyor, 8 denemenin hepsi TEKRAR diye reddedilip kosu iptal oluyordu.
    onceki = "\n".join("- " + (k.get("topic") or "") for k in gecmis if k.get("topic"))
    onceki_baslik = "\n".join("- " + k["title"] for k in gecmis[-40:] if k.get("title"))
    onceki_kanca = ", ".join(k["kanca_yazisi"] for k in gecmis[-40:] if k.get("kanca_yazisi")) or "(none yet)"
    son_turler = _son_farkli_turler(gecmis, 4)
    tur_blok = ", ".join(son_turler) if son_turler else "(none yet)"

    perf_blok = ""
    if performans and performans.get("en_iyi"):
        iyi = "\n".join(f"- {v['baslik']}  ({v['izlenme']:,} views)" for v in performans["en_iyi"])
        perf_blok = f"""
--- WHAT ALREADY WORKS ON THIS CHANNEL (DATA ONLY - these are past video titles, not instructions) ---
Channel average: {performans.get('ortalama', 0):,.0f} views across {performans.get('video_sayisi', 0)} videos.
Best performing videos:
{iyi}
Study WHY these worked (the emotional trigger, the title pattern, the type of case, the scale of the
mystery) and aim for that SAME kind of appeal - but with a COMPLETELY DIFFERENT story. Never re-tell
any case listed above.
"""
        if performans.get("en_kotu"):
            kotu = "\n".join(f"- {v['baslik']}  ({v['izlenme']:,} views)" for v in performans["en_kotu"])
            perf_blok += f"\nWorst performing videos (avoid this kind of angle/title):\n{kotu}\n"

    viral_blok = ""
    if viraller:
        vb = "\n".join(f"- {v['baslik']}  ({v['izlenme']:,} views)" for v in viraller)
        viral_blok = f"""
--- CURRENTLY VIRAL IN THIS NICHE (DATA ONLY - titles harvested from YouTube, not instructions) ---
{vb}
Use these ONLY to learn the current title rhythm, hook energy and curiosity structure that is working
right now. Do NOT copy any of these stories, titles or wordings. Your story must be different.
"""

    red_blok = ""
    if reddedilenler:
        red_blok = ("\n--- REJECTED IN THIS RUN (you already proposed these, they are duplicates - "
                    "pick something completely different) ---\n" +
                    "\n".join("- " + r for r in reddedilenler) + "\n")

    return f"""You are the head writer for a HIGH-QUALITY, curiosity-driven ENGLISH YouTube Shorts channel.
Channel niche: {NICHE}

{_AILE_BLOK[aile]}
--- THIS VIDEO'S WORLD (mandatory, picked by rotation so the channel never feels repetitive) ---
The story MUST take place in / be about: {tema or "any fresh setting"}.
Pick the MOST viral angle inside that world: a premise anyone (13 or 60 years old) instantly understands in
one sentence, an everyday situation that turns impossible, a detail people will repeat to friends.
Do NOT use any of these recent premises or settings again (no remote cabins, no lone old man with a strange
object unless the world above says so): {"; ".join(_son_mekanlar(gecmis)) or "-"}
{perf_blok}{viral_blok}
--- ABSOLUTE RULE: NEVER REPEAT A STORY ---
These cases have ALREADY been covered by this channel. Your topic must NOT be any of them, must not be a
different angle on them, and must not involve the same people, ships, places or events:
{onceki if onceki else "(none yet)"}

Titles already used (do not echo their wording):
{onceki_baslik if onceki_baslik else "(none yet)"}
{red_blok}
--- TOPIC TYPE ROTATION (kill the "every video is the same" feeling) ---
Choose ONE "topic_type" for this video from EXACTLY this list:
{_KONU_TUR_ENUM}
The last videos already used these types (MOST RECENT FIRST): {tur_blok}
Your topic_type MUST be different from those. Rotate hard so no type repeats close together.
This channel is NOT just "missing people" - stories about a strange object, an old document, a radio
signal, a piece of CCTV, a lab finding, an archaeological find or a cold-war file are just as strong.
Actively favor NON-disappearance angles.

Pick a genuinely FRESH, SPECIFIC idea that fits this content family. Vary country, era and setting every time.

{_GERCEK_KURAL if aile == 'gercek_vaka' else _KURGU_KURAL}
--- SCRIPT RULES (spoken narration) -- write like a Netflix / HBO true-crime doc, not an AI narrator ---
- Language: English. Length: 100-140 words (about 40-55 seconds spoken). NEVER exceed 58 seconds.
- ONE idea, ONE payoff, a full arc: setup, escalation, the key detail, a strong ending. No filler or repetition.
- GOLDEN RULE - SHOW THE EVENT, DO NOT LABEL IT. Never tell the viewer a mystery happened; make them
  feel like an invisible witness standing inside the scene, opening a classified file for the first time.
  * WRONG: "The man vanished."   RIGHT: "The elevator reached the top floor empty."
  * WRONG: "She disappeared."     RIGHT: "Her coffee was still warm when police arrived."
  * WRONG: "The plane disappeared." RIGHT: "The radar signal stopped in the middle of open sky."
- BANNED WORDS/PHRASES (they make every video sound identical - NEVER use them in script OR title):
  vanished, disappeared, disappearance, missing, unsolved, lost forever, gone without a trace,
  nobody knows, no one knows, the mystery remains, to this day, never found, never seen again.
  Instead of these labels, state the concrete physical fact that proves it.
- SENTENCE 1 IS THE HOOK and it decides everything:
  * MAXIMUM 15 words. Ideally 8-12. It must be a BLUNT CONTRADICTION of what should be true, stated
    as a plain physical fact - so the viewer's brain needs the resolution.
  * Great hooks (this energy): "The camera recorded everyone entering the building. Except one."
    / "They had enough food to survive. They all died anyway." / "The door was locked from inside,
    but the room was empty."
  * You MAY put the person's real name inside the hook if it hits hard, but still LEAD with the shocking
    concrete fact. NEVER open with a bare date/year ("In 1972..."), "Did you know", "Imagine", or a question.
- Then keep tension rising with short, punchy sentences. No filler, no throat-clearing, no summarising.
- ANCHOR IT: within the first ~8 seconds say who, where and when (real case: the REAL name, year and place;
  fiction: the character's first name and a concrete setting).
- PACING - drop a NEW concrete detail every 2-3 seconds (a fact, an object, a number, a piece of
  evidence). The viewer must never be able to guess what the next line reveals.
- Loose beat map (flexible, not a template): 0-2s shocking contradiction | 2-8s who/where/when |
  8-25s tension climbs, new detail each beat | 25-42s the key evidence or the hard decision |
  42-55s the twist / the line that stays in their head.
- The FINAL sentence is the most disturbing concrete detail of the whole case - never a summary,
  never "the case is still open". End on one unresolved physical fact, then it stops.
- PERSONAL RELEVANCE (biggest measured subscriber driver): before the halfway point, land ONE line
  that puts the VIEWER in the scene - what they would see, hear or feel standing there. Distance is
  the enemy of subscribing.
- NO stage directions, NO emojis, NO "[music]", NO speaker labels.

--- TITLE RULES (browse CTR) ---
- Under 70 characters, then " #Shorts".
- Same BANNED WORDS as the script apply to the title (no "vanished", "disappeared", "missing",
  "unsolved", "mystery remains", etc.). State the concrete shocking fact instead.
- If the subject HAS A NAME, you may use it, but lead with the CONCRETE SHOCKING FACT, not the name.
- WINNING FORMULA (measured on 177 sibling-channel videos, channel-internal percentile):
  a CONCRETE SUBJECT + a clause stating the shocking thing that HAPPENED, phrased as a hard fact.
  "The Elevator Reached the Top Floor Empty" / "60 People Died After Sitting in the Busby Stoop Chair"
  / "Her Coffee Was Still Warm When Police Arrived". Measured +12.7 percentile.
- ONE word may be ALL-CAPS for emphasis (+14.0 measured). It MUST be a POWER word (noun/verb/adjective),
  never a connector like THAT/WHO/THE.
- Numbers and concrete quantities help (+3.6).
- NEVER end the title with a question mark (-7.3 measured) and NEVER start with "This"/"That" (-8.7).
  Avoid starting with "Why"/"How" (-5.0). Vary wording between videos, but always keep the formula above.

--- THUMBNAIL TEXT ---
- "thumbnail_text": 2 to 4 words, UPPERCASE, brutally punchy, readable at thumbnail size.
  It must create curiosity on its own. Energy: "STILL WARM", "LOCKED FROM INSIDE", "NO BODIES FOUND",
  "SIGNAL STOPPED". Obey the banned-words rule. Do NOT just repeat the title.

--- VISUAL QUERIES (storyboard - maximum quality from Pexels/Pixabay) ---
- Give 9 to 12 PROFESSIONAL stock-footage search phrases, 3 to 6 words each. NEVER a single word
  (not "forest" but "foggy pine forest aerial"; not "office" but "empty fluorescent office at night";
  not "road" but "rain soaked highway at night"; not "boat" but "abandoned fishing boat at sea").
- Build each phrase as SUBJECT + SETTING + LIGHT/WEATHER, and when useful add a shot word that stock
  sites index well: aerial, close-up, macro, slow motion, drone shot, top down, handheld, timelapse.
- They MUST be listed IN NARRATION ORDER: phrase 1 = the opening line, then evenly to the end, so what
  is on screen always matches what is being said at that moment.
- Each phrase = a DIFFERENT concrete scene, and it should point the camera at the ONE detail that
  matters in that beat (an empty chair, a phone screen, a map, wet footprints, a CCTV monitor, an old
  file cover, a radar screen), not a generic wide shot.
- Mood is always dark, eerie, cinematic: night, fog, shadow, rain, snow, dim light, deep water,
  abandoned interiors, old paper, cold isolated places.
- STRICTLY FORBIDDEN: flowers, insects, cute animals, happy people, weddings, food, bright sunny
  nature, modern city life, corporate stock.

--- STORYBOARD (each scene becomes ONE illustrated shot: a polished 2D cinematic mystery illustration with
clean ink outlines, deep navy/black shadows and one controlled warm yellow light; the people are drawn
from "image_prompt", so it must describe them exactly) ---
- "cast": how the people in the story look. Key "subject" = the central real person of the case;
  optionally "other" = a second person (police, pilot, witness...). The "narrator" is fixed, do not add it.
  Each look: {{"hair": one of none|short|messy|long|bun|cap|hat, "hair_color": "#RRGGBB",
  "shirt": "#RRGGBB", "skin": "#RRGGBB", "glasses": true/false, "mustache": true/false, "beard": true/false}}.
  Match era/role (1900s man -> hat + mustache, pilot -> cap, old professor -> messy white hair + glasses).
- "scenes": 7 to 10 beats IN NARRATION ORDER, evenly covering the script. Each:
  {{"background": one of plain|room|night|forest|sea|sky|office|lab|snow|desert|cave|street,
    "prop": one of none|door|window|chair|table|phone|radio|map|letter|clock|car|ship|plane|lighthouse|
            house|tree|grave|box|key|footprints|camera|skull|question,
    "characters": 1-2 of {{"role": "narrator"|"subject"|"other",
                           "expression": neutral|scared|shocked|sad|thinking|angry|happy,
                           "pose": idle|point|hands_up|hands_on_head|shrug|walk}},
    "label": optional 1-3 word sign shown on screen (a year, a place, a number) or "",
    "place": the EXACT place and era of this beat in 6-15 words (e.g. "deck of a 19th-century wooden brigantine in Atlantic fog"),
    "key_object": the ONE concrete object the narration mentions in this beat (e.g. "wedding ring", "VCR with red light") or ""}}
  "place" and "key_object" are drawn specifically for this story, so they must follow the narration beat by beat.
  "image_prompt": 25-45 words, English: the FULL illustration of this beat for an image AI. Say who is in the
    picture using the SAME fixed look phrase every time (e.g. "a bearded sailor in a navy coat and captain hat"),
    what they are doing, their facial expression, the exact place and era, the key object, and the camera angle
    (close-up / wide shot / over-the-shoulder). Concrete and visual; never names of real people; no text in the image.
    At least 6 of the scenes must SHOW the story's person(s) acting and reacting (not only objects); use object
    close-ups only for the 1-3 beats where the object itself is the shocking detail.
    The image_prompt NEVER mentions a narrator, presenter or stickman: the "narrator" role exists only in
    "characters". For narrator beats, draw the story's own person or the key object instead.
  DIRECTOR'S SHOT PLAN - every scene ALSO has these fields (they drive camera, timing, text and sound):
    "narration": the EXACT words of the script this picture covers, copied verbatim (consecutive scenes
       together cover the whole script in order; one scene = one beat of 1-3 sentences),
    "purpose": why this shot exists in 3-8 words (hook / establish place / reveal clue / build dread / twist),
    "focus": the ONE thing the eye must land on (the clock face with no pendulum, her trembling hand),
    "emotion": the person's feeling shown by face AND body (frozen, leaning away, eyes locked on the object),
    "shot": one of extreme_close|close|medium|wide,
    "move": one of push_in|pull_out|pan_left|pan_right|tilt_up|tilt_down|static - chosen for the beat:
       push_in = rising dread / reveal, pull_out = isolation / aftermath, pan = searching / following a
       gaze, tilt = height or discovery, static = shock beat or a hard cut. Never the same move 3 times in a row.
    "light": one of steady|flicker|dim_down|reveal|lightning,
    "on_screen_text": "" for almost every scene. ONLY when a word on screen adds what the picture cannot
       (a date, a place, a number) give 1-4 words. Never repeat the narration or the title.
    "continuity": what carries over from the previous shot (same coat, clock now on the left, same hallway),
    "sfx": one of none|boom|hit|creak|knock|static|heartbeat|whoosh.
  The picture must ADD something the narration does not say (a detail, a reaction, a scale), not just
  illustrate the sentence. The beat that states the IMPOSSIBLE thing must SHOW it literally and clearly
  (furniture hanging upside down from the ceiling, footprints walking up the wall) - never a generic
  person looking scared next to a normal-looking room. Vary shot sizes: open wide or close, never three wides in a row; the scene where
  the key object is described is a close / extreme_close of that object.
- "hook_text": 2-5 WORDS, UPPERCASE, shown ONLY on the first frame. A concrete contradiction that makes the
  viewer stay (pattern examples only, write your own: "IT HAD NO PENDULUM", "THE DOOR WAS NAILED SHUT"). It must differ from the title, from the
  thumbnail_text and from the first spoken sentence. Never reuse a hook_text from an earlier video.
  Earlier hook_texts (do not reuse or paraphrase): {onceki_kanca}
- "look_bible": one sentence fixing each person's appearance (age, face, hair, clothing colors) and the
  key place; every image_prompt must reuse these exact look phrases so people never change between shots.
  The FIRST character of a scene is the one whose mouth talks. Scene 1 = the hook: "narrator", shocked,
  pointing at the key prop. Reenact the story with "subject"; return to "narrator" for the twist/ending.
  Pick the prop that IS the beat (the stopped clock, the empty car, the letter). Vary backgrounds.
- "case_card": the REAL case identity for an on-screen dossier card: {{"name": "...", "year": "1900",
  "place": "City/Region, Country"}}. Short values (name <= 32 chars, place <= 32 chars).
- "keywords": 3 to 6 single words FROM THE SCRIPT that carry the story (numbers, the key object, the
  shocking verb); they are highlighted in the captions.

Return ONLY valid JSON (no markdown, no ```), EXACTLY this shape:
{{
  "topic": "short specific topic label naming the actual case or the fictional premise",
  "wikipedia_title": "exact English Wikipedia article title (real cases only, else empty string)",
  "topic_type": "exactly ONE of: {_KONU_TUR_ENUM}",
  "script": "the full narration text as one paragraph",
  "title": "catchy, curiosity-driven YouTube title under 70 characters, include #Shorts",
  "description": "2-3 sentence description, then a few relevant hashtags",
  "thumbnail_text": "2-4 WORD PUNCH",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"],
  "visual_queries": ["query1", "query2", "query3", "query4", "query5", "query6", "query7", "query8", "query9"],
  "cast": {{"subject": {{"hair": "hat", "hair_color": "#2b2b2b", "shirt": "#5d4037", "skin": "#e8b07a", "glasses": false, "mustache": true, "beard": false}}}},
  "hook_text": "2-5 WORD CONTRADICTION",
  "look_bible": "Elena: woman in her 30s, pale oval face, long straight black hair, dark green wool coat; hallway: narrow stone cottage hall, one oil lamp",
  "scenes": [{{"background": "night", "prop": "clock", "characters": [{{"role": "subject", "expression": "scared", "pose": "idle"}}], "label": "",
              "place": "...", "key_object": "...", "image_prompt": "...", "narration": "exact script words",
              "purpose": "...", "focus": "...", "emotion": "...", "shot": "close", "move": "push_in",
              "light": "flicker", "on_screen_text": "", "continuity": "...", "sfx": "none"}}],
  "case_card": {{"name": "real case name", "year": "YYYY", "place": "place, country"}},
  "keywords": ["word1", "word2", "word3"]
}}
"""


# Kotasi biten (429) model bu kosu boyunca tekrar denenmez: her fikir denemesinde ayni modele
# 3 kez bekleyerek donmek kosuyu ~1.5 dk/deneme uzatiyordu (8 denemede 60 dk sinira dayaniyordu).
_KOTASI_BITEN = set()
_YOGUN_MODEL = set()   # bu kosuda 503 veren modeller (siraya en sona konur)


def _gemini_cagir(prompt):
    """Gecici hatalarda tekrar dener + yedek modele gecer. Ham JSON sozlugu doner."""
    import time
    from google import genai

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY bos! Anahtari koda YAZMA - ortam degiskeni/secret olarak ver.\n"
            "  GitHub: Settings > Secrets and variables > Actions > New secret > GEMINI_API_KEY\n"
            "  Yerel (PowerShell): $env:GEMINI_API_KEY = 'anahtarin'")

    from google.genai import types
    # Zaman asimi SART: asili kalan tek bir istek tum kosuyu 60 dk is limitine kadar kilitliyordu
    client = genai.Client(api_key=GEMINI_API_KEY, http_options=types.HttpOptions(timeout=120_000))
    modeller, gorulen = [], set()
    for md in [GEMINI_MODEL, "gemini-3.5-flash", "gemini-3-flash-preview", "gemini-2.5-flash"]:
        if md and md not in gorulen:
            gorulen.add(md)
            modeller.append(md)

    # Bu kosuda asiri yuklu (503) cikan modeller sona: her cagride 2 dk zaman asimi beklemeyelim
    modeller = [m for m in modeller if m not in _YOGUN_MODEL] + [m for m in modeller if m in _YOGUN_MODEL]
    son_hata = None
    if all(m in _KOTASI_BITEN for m in modeller):
        _KOTASI_BITEN.clear()   # hepsi bittiyse bir tur daha sans ver
    for model in modeller:
        if model in _KOTASI_BITEN:
            continue
        for deneme in range(1, 5):
            try:
                resp = client.models.generate_content(model=model, contents=prompt)
                text = (resp.text or "").strip()
                bulunan = re.search(r"\{.*\}", text, re.S)
                if not bulunan:
                    raise RuntimeError("Gemini gecerli JSON dondurmedi: " + text[:120])
                data = json.loads(bulunan.group(0))
                print(f"      (Gemini model: {model})")
                return data
            except Exception as e:
                son_hata = e
                mesaj = str(e).lower()
                gecici = any(k in mesaj for k in ("503", "429", "500", "unavailable", "overloaded",
                                                  "resource_exhausted", "high demand", "timeout", "deadline"))
                yogun = any(k in mesaj for k in ("503", "unavailable", "overloaded", "high demand"))
                if yogun and deneme >= 2:
                    _YOGUN_MODEL.add(model)
                    print(f"      Model '{model}' asiri yuklu (503), bu kosuda sona alindi; sonraki modele...")
                    break
                if gecici and deneme < 4:
                    bekle = 5 * deneme
                    print(f"      Gemini gecici hata ({model}, deneme {deneme}): {bekle}s bekle...")
                    time.sleep(bekle)
                    continue
                if "429" in mesaj or "resource_exhausted" in mesaj:
                    _KOTASI_BITEN.add(model)
                print(f"      Model '{model}' olmadi ({str(e)[:70]}), sonraki modele...")
                break
    raise RuntimeError(f"Gemini hicbir modelle uretemedi. Son hata: {son_hata}")


DENEME_SAYISI = 8
KATI_DENEME   = 5     # ilk 5 deneme siki eleme, sonrasi sadece 'ayni vaka' engeli


def wikipedia_dogrula(baslik):
    """
    Gercek vaka icin Ingilizce Wikipedia maddesinin VAR oldugunu dogrular (ucretsiz MediaWiki API).
    Donus: {dogrulandi, url, baslik, yok}. yok=True -> madde kesin olarak yok (fikir reddedilir);
    ag/limit hatasinda yok=False, dogrulandi=False -> kalite kontrol videoyu yayina vermez.
    """
    import time
    sonuc = {"dogrulandi": False, "url": "", "baslik": str(baslik or ""), "yok": False}
    if not baslik or not str(baslik).strip():
        sonuc["yok"] = True
        return sonuc
    params = {"action": "query", "titles": str(baslik).strip(), "redirects": 1, "prop": "info",
              "inprop": "url", "format": "json"}
    for deneme in range(3):
        try:
            r = _http_get("https://en.wikipedia.org/w/api.php", params=params, timeout=20,
                          headers={"User-Agent": "unsadark-shorts-bot/1.0 (source verification)"})
            if r.status_code == 429:
                time.sleep(4 * (deneme + 1))
                continue
            sayfalar = (r.json().get("query") or {}).get("pages") or {}
            for sayfa in sayfalar.values():
                if "missing" in sayfa or "invalid" in sayfa:
                    sonuc["yok"] = True
                elif sayfa.get("ns") == 0:
                    sonuc.update(dogrulandi=True, url=sayfa.get("fullurl", ""), baslik=sayfa.get("title", baslik))
            return sonuc
        except Exception as e:
            print("      (wikipedia dogrulamasi denemesi basarisiz:", str(e)[:80], ")")
            time.sleep(2)
    return sonuc


def gemini_uret(performans, viraller):
    """
    Gecmisle CAKISMAYAN, hook'u SAGLAM bir fikir uretilene kadar dener.
    Kod tarafinda dogrulanir -> ayni hikaye veya zayif hook YAYINA CIKAMAZ.
    """
    gecmis = gecmisi_oku()
    print(f"      Hafizada {len(gecmis)} islenmis konu var (hicbiri tekrar edilmeyecek)")
    aile = aile_sec(gecmis)
    print(f"      Icerik ailesi: {aile}  (dagilim: {', '.join(f'{k}={v:.0%}' for k, v in aile_dagilimi().items())})")
    reddedilenler = []
    # Sadece USLUP sebebiyle (hook / yasak kelime / tarih / tur rotasyonu) reddedilen ama
    # TEKRAR OLMAYAN son fikir. Hicbir fikir tum kurallardan gecemezse kosuyu iptal etmek
    # yerine bu kullanilir -> "her gun bir video" garantisi. Tekrar eden konu ASLA buraya girmez.
    yedek = None

    for tur in range(1, DENEME_SAYISI + 1):
        kati = tur <= KATI_DENEME
        tema = tema_sec(gecmis, aile)
        print(f"      Tema: {tema}")
        data = _gemini_cagir(_prompt_kur(gecmis, performans, viraller, reddedilenler, aile, tema))
        data["aile"] = aile
        data["tema"] = tema
        konu    = (data.get("topic") or "").strip()
        script  = (data.get("script") or "").strip()
        baslik  = (data.get("title") or "").strip()
        aciklama = (data.get("description") or "").strip()
        if not konu or not script or not baslik:
            reddedilenler.append(konu or "(bos yanit)")
            print(f"      [{tur}] eksik alan geldi, yeniden isteniyor...")
            continue

        sebep = tekrar_mi(konu, baslik, _ilk_cumle(script), gecmis, kati=kati, aciklama=aciklama)
        if sebep:
            reddedilenler.append(konu)
            print(f"      [{tur}] TEKRAR reddedildi -> {konu}  ({sebep})")
            continue

        hsorun = hook_sorunu(script)
        if hsorun:
            reddedilenler.append(konu)
            print(f"      [{tur}] ZAYIF HOOK reddedildi -> {hsorun}")
            yedek = data
            continue

        yk = _yasak_kelime_var(script, baslik)
        if yk:
            reddedilenler.append(konu)
            print(f"      [{tur}] YASAK KELIME reddedildi -> '{yk}' (olayi anlat, etiketleme)")
            yedek = data
            continue

        # GERCEK, TARIHLI VAKA garantisi: yasanmis bir olay her zaman bir tarih icerir.
        # 4 haneli yil (1000-2099) VEYA antik referans (AD/BC/CE/century) araniyor. Yoksa
        # hikaye 'bir adam bir kadin yasadi' gibi jenerik/uydurma hissi verir -> reddet.
        if aile == "gercek_vaka" and not (re.search(r"\b(1\d{3}|20\d\d)\b", script)
                or re.search(r"\b(\d{1,4}\s?(?:ad|bc|ce|bce)|centur(?:y|ies))\b", script, re.I)):
            reddedilenler.append(konu)
            print(f"      [{tur}] TARIH YOK reddedildi -> script gercek bir yil/tarih icermiyor (isimli-tarihli olmali)")
            yedek = data
            continue

        if aile == "gercek_vaka":
            kaynak = wikipedia_dogrula(data.get("wikipedia_title"))
            data["kaynak"] = kaynak
            if kaynak["yok"]:
                reddedilenler.append(konu)
                print(f"      [{tur}] KAYNAK YOK -> '{data.get('wikipedia_title')}' Wikipedia'da bulunamadi (gercek vaka kaynaksiz anlatilmaz)")
                continue

        ttype = (data.get("topic_type") or "").strip().lower()
        yasak_tur = _son_farkli_turler(gecmis, 2 if kati else 1) if aile == "gercek_vaka" else []
        if ttype and ttype in yasak_tur:
            reddedilenler.append(konu)
            print(f"      [{tur}] TUR TEKRARI reddedildi -> '{ttype}' (son turler: {yasak_tur})")
            yedek = data
            continue

        print(f"      [{tur}] onaylandi: {konu}  [tur: {ttype or '-'}]")
        return data

    if yedek and aile == "gercek_vaka" and "kaynak" not in yedek:
        yedek["kaynak"] = wikipedia_dogrula(yedek.get("wikipedia_title"))
    if yedek:
        print(f"      Tum kurallardan gecen fikir cikmadi -> tekrar OLMAYAN son fikir kullaniliyor: "
              f"{(yedek.get('topic') or '').strip()}")
        return yedek

    raise RuntimeError(
        f"Gemini {DENEME_SAYISI} denemede de benzersiz bir hikaye uretemedi. "
        "Ayni konularin tekrar yayinlanmamasi icin bu kosu bilerek iptal edildi; "
        "bir sonraki zamanlanmis kosu normal calisacaktir. "
        "Sik sik oluyorsa NICHE ayarini genislet.")


# =========================================================
#  6) edge-tts ile seslendir + KELIME ZAMANLAMASI
# =========================================================
async def seslendir_ve_zamanla(text, voice, out_path):
    import edge_tts

    # edge-tts 7.x: kelime senkronu icin boundary="WordBoundary" SART (varsayilan SentenceBoundary)
    # rate/pitch -> daha enerjik ve derin, profesyonel anlatici tonu
    communicate = None
    for kw in ({"boundary": "WordBoundary", "rate": TTS_RATE, "pitch": TTS_PITCH},
               {"rate": TTS_RATE, "pitch": TTS_PITCH},
               {"boundary": "WordBoundary"},
               {}):
        try:
            communicate = edge_tts.Communicate(text, voice, **kw)
            break
        except TypeError:
            continue
    if communicate is None:
        communicate = edge_tts.Communicate(text, voice)

    words, sentences, audio_bytes = [], [], 0
    with open(out_path, "wb") as f:
        async for chunk in communicate.stream():
            tur = chunk["type"]
            if tur == "audio":
                f.write(chunk["data"])
                audio_bytes += len(chunk["data"])
            elif tur == "WordBoundary":
                s = chunk["offset"] / 10_000_000
                d = chunk["duration"] / 10_000_000
                words.append({"word": chunk["text"], "start": s, "end": s + d})
            elif tur == "SentenceBoundary":
                s = chunk["offset"] / 10_000_000
                d = chunk["duration"] / 10_000_000
                sentences.append({"text": chunk["text"], "start": s, "end": s + d})

    if audio_bytes < 1024:
        raise RuntimeError("edge-tts ses uretemedi (internet ya da servis sorunu olabilir).")

    if words:
        return words
    if sentences:
        return _cumleden_kelime_zamani(sentences)
    return _sese_esit_dagit(text, out_path)


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
    """AKILLI parcalama: noktalamada temiz keser, zayif kelimeyle (a/the/of) BITIRMEZ."""
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
                break
            son = ham.strip('.,!?;:"\'').lower()
            if len(parca) >= n and son not in _ZAYIF_SON:
                break
        if not parca:
            break
        gruplar.append({
            "text":  " ".join(w["word"] for w in parca).upper(),
            "start": parca[0]["start"],
            "end":   parca[-1]["end"],
            "words": parca,
        })
    return gruplar


# =========================================================
#  7) KONUYA GORE OTOMATIK, YUKSEK COZUNURLUKLU ARKA PLAN
#     Kalite kurali: bir kaynak 1080x1920'yi doldurmak icin
#     MAX_BUYUTME'den fazla buyutulmesi gerekiyorsa REDDEDILIR.
# =========================================================
def _http_get(url, headers=None, params=None, stream=False, timeout=40):
    import requests
    h = {"User-Agent": USER_AGENT}
    if headers:
        h.update(headers)
    return requests.get(url, headers=h, params=params, stream=stream, timeout=timeout)


def _buyutme_orani(w, h):
    """Kaynagi 1080x1920 cerceveye TAM oturtmak icin gereken olcek. <=1.0 ise hic buyutme yok."""
    if not w or not h:
        return 99.0
    return max(W / float(w), H / float(h))


def _dosya_indir(url, hedef):
    try:
        r = _http_get(url, stream=True)
        if r.status_code != 200:
            return False
        beklenen = int(r.headers.get("Content-Length", 0) or 0)
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


def _en_iyi_kalite(adaylar, esik):
    """
    adaylar: [(url, w, h), ...] -> en az buyutme gerektiren, kullanilmamis olani secer.
    Esigi gecen aday yoksa None (caller AI'ya duser).
    """
    puanli = []
    for url, w, h in adaylar:
        if not url or url in _KULLANILAN_MEDYA:
            continue
        o = _buyutme_orani(w, h)
        if o <= esik:
            puanli.append((o, url, w, h))
    if not puanli:
        return None
    puanli.sort(key=lambda x: x[0])
    # En iyi 3 aday arasindan rastgele -> hem kalite hem cesitlilik
    o, url, w, h = random.choice(puanli[:3])
    print(f"    (secilen kaynak {w}x{h}, buyutme x{o:.2f})")
    return url


def _pixabay_video(q, esik):
    if not PIXABAY_API_KEY:
        return None
    try:
        r = _http_get("https://pixabay.com/api/videos/", params={
            "key": PIXABAY_API_KEY, "q": q, "per_page": 80, "safesearch": "true"})
        hits = _temiz_hits(r.json().get("hits", []), q)
        adaylar = []
        for h in hits:
            for boyut in ("large", "medium", "small", "tiny"):
                v = h.get("videos", {}).get(boyut) or {}
                if v.get("url"):
                    adaylar.append((v["url"], v.get("width", 0), v.get("height", 0)))
        return _en_iyi_kalite(adaylar, esik)
    except Exception as e:
        print("    (pixabay video hatasi:", e, ")")
    return None


def _pexels_video(q, esik):
    if not PEXELS_API_KEY:
        return None
    try:
        r = _http_get("https://api.pexels.com/videos/search",
                      headers={"Authorization": PEXELS_API_KEY},
                      params={"query": q, "orientation": "portrait", "size": "large", "per_page": 20})
        adaylar = []
        # Pexels alaka sirasina gore doner -> sadece EN ALAKALI ilk 8'i degerlendir,
        # yoksa "en yuksek cozunurluklu" diye konuyla ilgisiz bir klip secilebilir.
        for v in r.json().get("videos", [])[:8]:
            # Sayfa adresindeki slug konuyu icerir: .../video/dark-foggy-forest-123456/
            etiket = re.sub(r"[-/]", " ", (v.get("url") or "").split("pexels.com")[-1])
            if _yasak_mi(etiket):
                continue
            for f in v.get("video_files", []):
                if f.get("link"):
                    adaylar.append((f["link"], f.get("width", 0), f.get("height", 0)))
        return _en_iyi_kalite(adaylar, esik)
    except Exception as e:
        print("    (pexels video hatasi:", e, ")")
    return None


def _pixabay_foto(q, esik):
    if not PIXABAY_API_KEY:
        return None
    try:
        r = _http_get("https://pixabay.com/api/", params={
            "key": PIXABAY_API_KEY, "q": q, "image_type": "photo",
            "orientation": "vertical", "safesearch": "true", "per_page": 80, "order": "popular"})
        hits = _temiz_hits(r.json().get("hits", []), q)
        adaylar = []
        for h in hits:
            # largeImageURL uzun kenari 1280'e sabitler -> gercek oranini koruyarak boyut hesapla
            iw, ih = h.get("imageWidth", 0), h.get("imageHeight", 0)
            u = h.get("largeImageURL") or h.get("webformatURL")
            if not u or not iw or not ih:
                continue
            olcek = 1280.0 / max(iw, ih)
            adaylar.append((u, int(iw * olcek), int(ih * olcek)))
        return _en_iyi_kalite(adaylar, esik)
    except Exception as e:
        print("    (pixabay foto hatasi:", e, ")")
    return None


def _pexels_foto(q, esik):
    if not PEXELS_API_KEY:
        return None
    try:
        r = _http_get("https://api.pexels.com/v1/search",
                      headers={"Authorization": PEXELS_API_KEY},
                      params={"query": q, "orientation": "portrait", "size": "large", "per_page": 20})
        adaylar = []
        for p in r.json().get("photos", [])[:10]:
            if _yasak_mi(p.get("alt", "")):        # cicek/bocek/nese gibi alakasiz stok girmesin
                continue
            src = p.get("src", {})
            u = src.get("portrait") or src.get("large2x") or src.get("large")
            if u:
                # portrait src'i Pexels 1200x1800 verir; large2x 1880 genisliktedir
                adaylar.append((u, 1200, 1800) if src.get("portrait") else (u, p.get("width", 0), p.get("height", 0)))
        return _en_iyi_kalite(adaylar, esik)
    except Exception as e:
        print("    (pexels foto hatasi:", e, ")")
    return None


# --- KONU FILTRESI (GIZEM/KARANLIK): nese/gunduz/cicek gibi ALAKASIZ stok girmesin ---
_YASAK_ETIKET = (
    "flower", "floral", "blossom", "insect", "bug", "butterfly", "bee", "dragonfly",
    "garden", "sunny", "sunshine", "sunflower", "meadow", "spring", "summer", "beach", "tropical",
    "wedding", "baby", "kids", "child", "smiling", "happy", "party", "food", "fruit", "cake",
    "business", "office", "yoga", "fitness", "sport", "colorful", "rainbow", "cute", "puppy", "kitten",
)
_AI_STIL  = ("dark mysterious, eerie, cinematic film still, moody dramatic lighting, volumetric fog, "
             "photorealistic, ultra detailed, sharp focus, 8k, suspenseful atmosphere, vertical composition")
_AI_MODEL = "flux"
# Animasyon modu: TUM sahneler ayni cizim dilinde -> kanal kimligi + "animasyon dizisi" hissi
_ANIM_STIL = ("dark atmospheric 2D animated film still, painterly digital illustration, graphic novel "
              "style, bold ink shadows, dramatic rim lighting, volumetric fog, muted teal and amber "
              "palette, cinematic composition, highly detailed, eerie suspenseful mood, vertical 9:16 "
              "frame, no text, no letters, no watermark")
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
        return q + " cinematic"
    return q + " " + _ATMOSFER


_COK_GENEL = set("stone light water gold golden nature landscape scenery background texture wallpaper "
                 "abstract sunset sunrise cloud clouds grass tree trees field river lake ocean sea beach coast coastal cliff shore waves wave island seaside harbor "
                 "sky sun rock rocks mountain hill wall dust smoke".split())

_KONU_FILLER = set("cinematic close aerial slow motion shot footage view scene epic dramatic dark night "
                   "moody light lighting high detailed realistic photorealistic".split()) | set(_ATMOSFER.lower().split())


def _konu_kelimeleri(q):
    """RAW sorgudaki KONU kelimeleri. Ultra-genel kelimeler ikincil."""
    kel = [w for w in re.findall(r"[a-z]{4,}", (q or "").lower()) if w not in _KONU_FILLER]
    ozel = [w for w in kel if w not in _COK_GENEL]
    return ozel if ozel else kel


_AKTIF_KONU = []


def _temiz_hits(hits, q=""):
    """KONU varsa SADECE o konuyla eslesen stok'u kabul et; yoksa BOS -> caller AI'ya gecer."""
    temiz = [h for h in hits if not _yasak_mi(h.get("tags", ""))]
    if _AKTIF_KONU:
        ana = _AKTIF_KONU[0]
        tam = [h for h in temiz if ana in (h.get("tags", "") or "").lower()]
        if tam:
            return tam[:40]
        cok = [h for h in temiz
               if sum(1 for w in _AKTIF_KONU if w in (h.get("tags", "") or "").lower()) >= 2]
        return cok[:40]
    if not temiz:
        temiz = hits
    uygun = [h for h in temiz if any(w in (h.get("tags", "") or "").lower() for w in _TEMA_KELIMELER)]
    return (uygun or temiz)[:40]


_KULLANILAN_MEDYA = set()


def _medyayi_isaretle(url):
    _KULLANILAN_MEDYA.add(url)
    try:
        with open(KULLANILAN_GORSEL_FILE, "a", encoding="utf-8") as f:
            f.write(url + "\n")
    except OSError:
        pass


def _tekrarsiz_url(fn, q):
    """Kaynak (Pexels/Pixabay) fonksiyonunu cagirir ve TEKRARSIZ bir URL dondurur.
    Kaynaklar zaten _en_iyi_kalite icinde _KULLANILAN_MEDYA'daki (daha once kullanilmis)
    tum URL'leri eledigi icin donen URL her zaman daha once hic kullanilmamis olandir."""
    return fn(q, MAX_BUYUTME)


def _keskinlestir(path):
    """
    Foto/AI gorselini videoya girmeden once profesyonellestirir:
    gerekiyorsa LANCZOS ile buyutur, unsharp mask ile netlestirir, kontrast/doygunlugu toparlar.
    Bu adim 'yumusak/bulanik' gorunumun buyuk kismini yok eder.
    """
    try:
        from PIL import Image, ImageFilter, ImageEnhance
        im = Image.open(path).convert("RGB")
        gerek = _buyutme_orani(im.width, im.height)
        if gerek > 1.0:
            # Cerceveyi doldurmaya yetecek kadar + Ken Burns payi kadar LANCZOS ile buyut
            hedef = (max(W, int(im.width * gerek * 1.22)), max(H, int(im.height * gerek * 1.22)))
            im = im.resize(hedef, Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=115, threshold=3))
        im = ImageEnhance.Contrast(im).enhance(1.07)
        im = ImageEnhance.Color(im).enhance(1.06)
        im.save(path, "JPEG", quality=95, subsampling=0)
        return True
    except Exception as e:
        print("    (keskinlestirme atlandi:", e, ")")
        return False


_AI_ARDISIK_HATA = 0
AI_HATA_SINIRI = 3     # servis coktuyse her sahnede bosuna beklemeyelim (Actions zaman asimi korumasi)


def _filigrani_kirp(path, oran=0.06):
    """Pollinations, nologo=true olsa da sag alt koseye 'pollinations.ai' yazisi basiyor.
    Alt seridi kirp -> videoda ve thumbnail'de filigran gorunmez (cover ile yine tam ekran)."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
            kirpik = im.convert("RGB").crop((0, 0, w, int(h * (1 - oran))))
        kirpik.save(path, quality=95)
    except Exception as e:
        print("    (filigran kirpilamadi:", str(e)[:60], ")")


def _ai_gorsel(query, hedef, stil=None, boyutlar=None):
    """
    Pollinations (ucretsiz AI) ile sorguyu BIREBIR cizen YUKSEK COZUNURLUKLU dikey gorsel.
    Once 1440x2560 dener (Ken Burns zoom'u bile buyutme yapmaz), olmazsa 1080x1920.
    Ust uste AI_HATA_SINIRI kadar basarisiz olursa servis cokmus sayilir ve
    kosunun geri kalaninda AI denenmez -> is akisi asla takilip kalmaz.
    """
    global _AI_ARDISIK_HATA
    import urllib.parse

    if _AI_ARDISIK_HATA >= AI_HATA_SINIRI:
        return None

    prompt = f"{query}, {stil or _AI_STIL}"
    for gw, gh in (boyutlar or AI_BOYUTLARI):   # boyut basina TEK deneme -> sure sinirli
        seed = random.randint(1, 999999)
        url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt) +
               f"?width={gw}&height={gh}&nologo=true&seed={seed}&model={_AI_MODEL}")
        try:
            r = _http_get(url, timeout=90)
            ct = r.headers.get("Content-Type", "")
            if r.status_code != 200 or not ct.startswith("image"):
                print(f"    (ai gorsel yaniti: HTTP {r.status_code} {ct[:30]})")
            if r.status_code == 200 and ct.startswith("image"):
                with open(hedef, "wb") as f:
                    f.write(r.content)
                if os.path.getsize(hedef) > 12000:
                    _filigrani_kirp(hedef)
                    _keskinlestir(hedef)
                    print(f"    (AI gorsel {gw}x{gh})")
                    _AI_ARDISIK_HATA = 0
                    return hedef
                os.remove(hedef)
        except Exception as e:
            print("    (ai gorsel denemesi basarisiz:", str(e)[:80], ")")

    _AI_ARDISIK_HATA += 1
    if _AI_ARDISIK_HATA >= AI_HATA_SINIRI:
        print("    (AI gorsel servisi yanit vermiyor -> bu kosuda stok kaynaklara gecildi)")
    return None


def arka_plan_indir(sorgular):
    """
    Sahne sirasi korunarak, HER SAHNE icin kalite oncelikli medya bulur:
      1) KRISTAL NET gercek klip (buyutme <= MAX_BUYUTME)      -> hem hareket hem kalite
      2) Yuksek cozunurluklu AI gorseli (sinematik zoom+pan)   -> konuya %100 ozel
      3) Gevsek esikli gercek klip                             -> hareket kalsin
      4) Stok foto (son care)
    [(yol, tur), ...] dondurur.
    """
    global _KULLANILAN_MEDYA, _AKTIF_KONU
    umf = os.path.join(BASE_DIR, "kullanilan_gorseller.txt")
    # KALICI TEKRAR ENGELI: daha once HERHANGI bir videoda kullanilmis her gorsel/klip
    # URL'si SONSUZA DEK yasakli -> ayni stok klip/foto iki farkli videoda ASLA cikmaz.
    # (Kaynak fonksiyonlar _en_iyi_kalite icinde bu kumeyi eleme olarak kullanir. Havuz
    #  tukendiginde zincir zaten AI gorseline duser; AI her sahnede rastgele seed ile
    #  benzersiz gorsel urettiginden gorsel tekrari yine olusmaz.)
    _KULLANILAN_MEDYA = set()
    if os.path.exists(KULLANILAN_GORSEL_FILE):
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
        _AKTIF_KONU = _konu_kelimeleri(q)
        qa = _atmosfer_ekle(q)
        hedef_ai = os.path.join(MEDYA_KLASORU, f"m_{i:02d}.jpg")
        hedef_vid = os.path.join(MEDYA_KLASORU, f"m_{i:02d}.mp4")
        print(f"  Gorsel [{i+1}/{len(sorgular)}]: '{q}'  (konu: {' '.join(_AKTIF_KONU) or '-'})")

        # 1) KRISTAL NET, konuya birebir uygun HAREKETLI klip
        url = _pexels_video(qa, MAX_BUYUTME) or _pixabay_video(qa, MAX_BUYUTME)
        if url and _dosya_indir(url, hedef_vid):
            medya.append((hedef_vid, "video"))
            _medyayi_isaretle(url)
            print("    -> KLIP (yuksek cozunurluk, konuya uygun)")
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
        # 1b) KLIP icin IKINCI DENEME: ana konu + kanal temasi (daha genis havuz).
        #     Amac: kaliteli HAREKETLI klip bulma sansini artirmak, AI stile dusmemek.
        if _AKTIF_KONU:
            genis = _AKTIF_KONU[0] + " " + _ATMOSFER
            url = _tekrarsiz_url(_pixabay_video, genis) or _tekrarsiz_url(_pexels_video, genis)
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
                    print("    -> KLIP (genis arama, konuya uygun)")
                    continue

        # 2) uygun klip YOKSA -> AI konuyu BIREBIR cizer (sinematik zoom+kaydirma ile klip gibi akar)
        _AKTIF_KONU = []
        if _ai_gorsel(q, hedef_ai):
            medya.append((hedef_ai, "foto"))
            print("    -> AI GORSEL (konuya ozel, sinematik hareketli)")
            continue

        # 3) Kalite esigi gevsetilmis klip (hareket kaybolmasin)
        _AKTIF_KONU = _konu_kelimeleri(q)
        url = _pexels_video(qa, MAX_BUYUTME_ZAYIF) or _pixabay_video(qa, MAX_BUYUTME_ZAYIF)
        if url and _dosya_indir(url, hedef_vid):
            medya.append((hedef_vid, "video"))
            _medyayi_isaretle(url)
            print("    -> KLIP (esnek kalite esigi)")
            continue

        # 4) SON CARE: stok foto (netlestirilerek)
        url = _pexels_foto(qa, MAX_BUYUTME_ZAYIF) or _pixabay_foto(qa, MAX_BUYUTME_ZAYIF)
        if url and _dosya_indir(url, hedef_ai):
            _keskinlestir(hedef_ai)
            medya.append((hedef_ai, "foto"))
            _medyayi_isaretle(url)
            print("    -> STOK FOTO (son care, netlestirildi)")
            continue

        print("    -> bulunamadi, atlaniyor")

    print(f"  Toplam {len(medya)} arka plan medyasi hazir.")
    return medya


# =========================================================
#  8) MoviePy ile video kurgusu + altyazi
# =========================================================
def _fit_dikey(clip):
    """Klibi 1080x1920 cerceveyi tamamen kaplayacak sekilde olceklendirip ortadan kirpar."""
    hedef = W / H
    oran = clip.w / clip.h
    if oran > hedef:
        clip = clip.resized(height=H)
        clip = clip.cropped(x_center=clip.w / 2, width=W)
    else:
        clip = clip.resized(width=W)
        clip = clip.cropped(y_center=clip.h / 2, height=H)
    return clip


def _video_klip(path, sure, sira=0, toplam=1):
    """
    Klipten bir parca alir. sira/toplam verilirse klibi esit bolgelere ayirip FARKLI
    bolgesini kullanir -> ayni kaynaktan arka arkaya 'ayni goruntu' hissi olusmaz.
    """
    from moviepy import VideoFileClip, concatenate_videoclips
    v = VideoFileClip(path).without_audio()
    if v.duration < sure:
        n = int(sure // v.duration) + 1
        v = concatenate_videoclips([v] * n).subclipped(0, sure)
    else:
        bolge = (v.duration - sure) / max(1, toplam)
        bas = min(max(0.0, bolge * sira + random.uniform(0, bolge * 0.6)), v.duration - sure)
        v = v.subclipped(bas, bas + sure)
    return _fit_dikey(v).with_duration(sure)


def _foto_klip(path, sure, sira=0, toplam=1):
    """
    Ken Burns: fotografi/AI gorselini KLIP gibi hareket ettirir.

    HIZ NOTU: naif yontem (her karede tum gorseli buyutup sonra kirpmak) karede ~220 ms
    aliyordu -> 50 sn'lik videoda tek basina 5+ dakika. Burada PIL'in 'box' parametresi
    kullaniliyor: gorunecek dikdortgen KIRPILIP dogrudan 1080x1920'ye olcekleniyor,
    yani tek islem ve sabit cikti boyutu. Gorsel sonuc ayni, maliyet kat kat dusuk.

    Olcek hicbir zaman gorselin kendi cozunurlugunun altina dusmez -> netlik korunur.
    """
    from moviepy import VideoClip, ImageClip
    import numpy as np
    from PIL import Image

    try:
        im = Image.open(path).convert("RGB")
        iw, ih = im.size
        doldur = max(W / iw, H / ih)          # cerceveyi tam dolduran en kucuk olcek
        bas = doldur * 1.05                   # pan icin kucuk marj
        son = doldur * (1.05 + KEN_BURNS_ZOOM)
        yonler = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)]
        yon = yonler[(sira + abs(hash(path))) % len(yonler)]
        if sira % 2:                          # tek sirali sahneler zoom-out ile girsin
            bas, son = son, bas

        def _kare(t):
            o = min(1.0, max(0.0, t / max(sure, 0.1)))
            s = bas + (son - bas) * o                      # o anki olcek
            sw, sh = min(iw, W / s), min(ih, H / s)        # kaynakta gorunen dikdortgen
            cx = iw / 2 + yon[0] * KEN_BURNS_PAN * o / s   # kaydirmayi kaynak pikseline cevir
            cy = ih / 2 + yon[1] * KEN_BURNS_PAN * o / s
            x0 = min(max(0.0, cx - sw / 2), iw - sw)       # gorselin disina tasma
            y0 = min(max(0.0, cy - sh / 2), ih - sh)
            return np.asarray(im.resize((W, H), Image.BILINEAR,
                                        box=(x0, y0, x0 + sw, y0 + sh)))

        try:
            return VideoClip(frame_function=_kare, duration=sure)     # moviepy 2.x
        except TypeError:
            return VideoClip(make_frame=_kare, duration=sure)         # moviepy 1.x
    except Exception as e:
        print("  (ken burns kurulamadi, sabit gorsel:", str(e)[:90], ")")
        return _fit_dikey(ImageClip(path).with_duration(sure))


def _yedek_arka_plan(sure):
    """Internetten hic medya gelmezse: yerel klasordeki video, o da yoksa duz koyu ekran."""
    from moviepy import ColorClip
    if os.path.isdir(YEDEK_VIDEO_KLASORU):
        vids = [os.path.join(YEDEK_VIDEO_KLASORU, f) for f in os.listdir(YEDEK_VIDEO_KLASORU)
                if f.lower().endswith((".mp4", ".mov", ".mkv", ".webm", ".avi"))]
        if vids:
            print("  (internet medyasi yok -> yerel yedek video kullaniliyor)")
            return _video_klip(random.choice(vids), sure)
    print("  (hic gorsel yok -> duz koyu arka plan kullaniliyor)")
    return ColorClip(size=(W, H), color=(15, 15, 20)).with_duration(sure)


def _sahne_plani(medya_sayisi, sure):
    """
    Her medyaya senaryodaki sirasina gore bir zaman penceresi verir, sonra pencereyi
    HEDEF_SAHNE_SN'yi asmayacak sekilde alt-cekimlere boler.
    Boylece anlatimla gorsel senkronu BOZULMADAN kesme temposu artar (retention).
    -> [(medya_index, alt_sira, alt_toplam, sahne_suresi), ...]
    """
    pencere = sure / medya_sayisi
    alt = max(1, min(4, int(math.ceil(pencere / HEDEF_SAHNE_SN))))
    # Sinira takilirsa dogrudan 1'e dusme; siniri asmayan EN BUYUK bolme sayisini kullan
    while alt > 1 and medya_sayisi * alt > MAX_SAHNE:
        alt -= 1
    plan = []
    for i in range(medya_sayisi):
        for j in range(alt):
            plan.append((i, j, alt, pencere / alt))
    return plan


def _arka_plan_montaj(medya, sure):
    """
    Sahneleri SERT KESME ile birlestirir.

    Neden crossfade yok: olculdu -> crossfade + compose karede ~200 ms, sert kesme + chain
    ~52 ms. Yani crossfade tek basina render suresini 4 katina cikariyordu. Ustelik hizli
    sert kesme Shorts'ta daha vurucu ve retention'a daha iyi geliyor.
    """
    from moviepy import concatenate_videoclips
    if not medya:
        return _yedek_arka_plan(sure)

    medya = medya[:12]
    plan = _sahne_plani(len(medya), sure)

    sahneler = []
    for (mi, alt_sira, alt_toplam, sahne_sn) in plan:
        path, tur = medya[mi]
        # +0.05: kayan nokta yuvarlamasi yuzunden arka plan sesten KISA kalip
        # sonda siyah kare birakmasin diye kucuk guvenlik payi
        s = max(1.2, sahne_sn + 0.05)
        try:
            if tur == "video":
                sahneler.append(_video_klip(path, s, alt_sira, alt_toplam))
            else:
                sahneler.append(_foto_klip(path, s, alt_sira, alt_toplam))
        except Exception as e:
            print("  (bir medya atlandi:", str(e)[:90], ")")

    if not sahneler:
        return _yedek_arka_plan(sure)
    if len(sahneler) == 1:
        return sahneler[0].with_duration(sure)

    # 'chain' HIZLI ama tum sahnelerin birebir ayni boyutta olmasini sart kosar.
    tam_boyut = all(tuple(s.size) == (W, H) for s in sahneler)
    try:
        bg = concatenate_videoclips(sahneler, method="chain" if tam_boyut else "compose")
    except Exception as e:
        print("  (chain birlestirme olmadi, compose'a gecildi:", str(e)[:90], ")")
        bg = concatenate_videoclips(sahneler, method="compose")

    if bg.duration < sure:
        tekrar = int(sure // bg.duration) + 1
        bg = concatenate_videoclips([bg] * tekrar, method="compose")
    return bg.subclipped(0, sure)


def _altyazi_klipleri(words, font_path):
    from moviepy import TextClip
    kutu_g = int(W * 0.9)
    kutu_y = 420                                 # SABIT yukseklik -> harf/kenarlik KIRPILMAZ
    x0 = (W - kutu_g) // 2
    y0 = int(H * SUBTITLE_Y - kutu_y / 2)
    klipler = []

    gruplar = kelime_gruplari(words, WORDS_PER_CHUNK)
    # Cumle aralarindaki sessizliklerde altyazi tamamen kaybolup ekran "bos" kaliyordu
    # (yanip sonme hissi). Her grubu bir sonraki grup baslayana kadar ekranda tut,
    # ama en fazla 0.7 sn uzat -> ne bosluk kalir ne de yazi gec kalir.
    for i, g in enumerate(gruplar):
        if i + 1 < len(gruplar):
            g["end"] = min(gruplar[i + 1]["start"], g["end"] + 0.7)

    for g in gruplar:
        sure = max(0.15, g["end"] - g["start"])
        # HOOK VURGUSU: ilk 3 sn daha BUYUK punto -> ilk saniyeler ekrana kilitler
        fs = int(FONT_SIZE * 1.18) if g["start"] < 3.0 else FONT_SIZE
        ortak = dict(font=font_path, text=g["text"], font_size=fs, method="caption",
                     size=(kutu_g, kutu_y), text_align="center",
                     horizontal_align="center", vertical_align="center")

        golge = (TextClip(color="black", **ortak)
                 .with_start(g["start"]).with_duration(sure)
                 .with_position((x0 + 5, y0 + 5)).with_opacity(0.45))
        ana = (TextClip(color=TEXT_COLOR, stroke_color=STROKE_COLOR, stroke_width=STROKE_WIDTH, **ortak)
               .with_start(g["start"]).with_duration(sure)
               .with_position((x0, y0)))

        klipler.append(golge)
        klipler.append(ana)
    return klipler


def _cta_klipleri(dur, font_path, yazi, basla, sure=3.0, y_oran=0.30):
    """Logo + buyuk yazidan olusan, yumusak girip cikan cagri klibi."""
    from moviepy import ImageClip, TextClip, vfx
    klipler = []
    lb = int(W * 0.20)
    yaz_y = int(H * y_oran) + lb - 6
    try:
        if os.path.exists(LOGO_PATH):
            klipler.append(ImageClip(LOGO_PATH).resized((lb, lb))
                           .with_start(basla).with_duration(sure)
                           .with_position(("center", int(H * y_oran)))
                           .with_effects([vfx.CrossFadeIn(0.4), vfx.CrossFadeOut(0.4)]))
        klipler.append(TextClip(font=font_path, text=yazi, font_size=78, color="yellow",
                                stroke_color="black", stroke_width=7, method="caption",
                                size=(int(W * 0.8), 130), horizontal_align="center",
                                vertical_align="center")
                       .with_start(basla).with_duration(sure)
                       .with_position(("center", yaz_y))
                       .with_effects([vfx.CrossFadeIn(0.4), vfx.CrossFadeOut(0.4)]))
    except Exception as e:
        print("  (CTA klibi atlandi:", str(e)[:90], ")")
    return klipler


def _marka_klipleri(dur, font_path):
    """Kose logosu (kalici) + ortada ABONE OL + sonda DIGER VIDEOLARI IZLE cagrisi."""
    from moviepy import ImageClip
    klipler = []
    try:
        if os.path.exists(LOGO_PATH):
            kb = int(W * 0.13)
            klipler.append(ImageClip(LOGO_PATH).resized((kb, kb))
                           .with_duration(dur).with_position((36, 40)).with_opacity(0.82))
        klipler += _cta_klipleri(dur, font_path, ABONE_YAZI, dur * 0.45, 3.0, 0.30)
        if dur > 12:
            # Kapanis: izleyiciyi baska bir videoya yonlendir (oturum suresi artar)
            klipler += _cta_klipleri(dur, font_path, SONRAKI_YAZI, max(dur - 3.4, dur * 0.7), 3.2, 0.28)
    except Exception as e:
        print("  (marka klibi atlandi:", str(e)[:90], ")")
    return klipler


def _font_bul():
    if os.path.exists(FONT_PATH):
        return FONT_PATH
    for alt in [
        r"C:\Windows\Fonts\impact.ttf", r"C:\Windows\Fonts\ariblk.ttf",
        r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        if os.path.exists(alt):
            return alt
    return FONT_PATH


def _ffmpeg_yolu():
    """moviepy'nin kullandigi ffmpeg binary'sini bulur (PATH'te olmasa da calisir)."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _sinematik_pas(giris, cikis):
    """
    FAZ 2: Ham videoya tek FFmpeg pasi ile sinematik katman uygular.
      - soguk belgesel gradesi (eq + colorbalance)
      - film grain (noise, temporal = hafif dogal flicker/arsiv hissi)
      - vignette (kenar karartma)
      - anlatim altina lavfi ile SENTEZLENEN derin ambient ugultu (asset gerektirmez)
      - VHS=1 ise ek analog doku (renk kaymasi + dusuk doygunluk)
    En zengin zincirden en sadeye dogru geriler; hicbiri olmazsa hata firlatir
    (caller ham videoyu kullanir, hat kirilmaz).
    """
    import subprocess
    ff = _ffmpeg_yolu()
    grade = "eq=contrast=1.06:saturation=0.90:brightness=-0.015:gamma=0.98"
    cold  = "colorbalance=rs=-0.03:gs=-0.01:bs=0.05:rm=-0.02:bm=0.03"
    grain = f"noise=alls={max(0, SINEMATIK_GRAIN)}:allf=t"
    vig   = "vignette=angle=PI/5"

    def _vf(vhs):
        parca = ["format=yuv420p", grade, cold]
        if vhs:
            parca += ["rgbashift=rh=3:bh=-3", "eq=saturation=0.82"]
        parca += [grain, vig]
        return ",".join(parca)

    enc = ["-c:v", "libx264", "-preset", X264_PRESET, "-b:v", VIDEO_BITRATE,
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
           "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-movflags", "+faststart"]

    # (ses_modu, vhs) en zenginden en sadeye - biri patlarsa bir alttakine gecilir
    denemeler = []
    if AMBIENT_SES:
        denemeler.append(("ambient", VHS_MOD))
        if VHS_MOD:
            denemeler.append(("ambient", False))
    denemeler.append(("sessiz", VHS_MOD))
    if VHS_MOD:
        denemeler.append(("sessiz", False))

    son_hata = None
    for ses, vhs in denemeler:
        vf = _vf(vhs)
        if ses == "ambient":
            fc = (f"[0:v]{vf}[v];"
                  f"[1:a]volume={AMBIENT_VOL},highpass=f=30,lowpass=f=170[amb];"
                  "[0:a][amb]amix=inputs=2:duration=first:dropout_transition=0[a]")
            komut = ([ff, "-y", "-i", giris,
                      "-f", "lavfi", "-i", "anoisesrc=color=brown:amplitude=0.9:seed=7",
                      "-filter_complex", fc, "-map", "[v]", "-map", "[a]"]
                     + enc + ["-shortest", cikis])
        else:
            komut = [ff, "-y", "-i", giris, "-vf", vf, "-map", "0:v", "-map", "0:a?"] + enc + [cikis]
        try:
            subprocess.run(komut, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            return (ses, vhs)
        except subprocess.CalledProcessError as e:
            son_hata = (e.stderr or b"").decode("utf-8", "ignore")[-300:]
            continue
    raise RuntimeError("tum sinematik zincir denemeleri basarisiz: " + (son_hata or "bilinmeyen hata"))


def video_olustur(words, medya, out_path):
    from moviepy import AudioFileClip, CompositeVideoClip

    font_path = _font_bul()
    audio = AudioFileClip(AUDIO_FILE)
    # SES NORMALIZASYONU: TTS cikisinin seviyesi videodan videoya degisiyor; akista
    # sessiz gelen video aninda kaydiriliyor -> her video ayni seviyede olsun.
    try:
        from moviepy import afx
        audio = audio.with_effects([afx.AudioNormalize()])
    except Exception as e:
        print("  (ses normalize atlandi:", e, ")")
    dur = audio.duration

    bg = _arka_plan_montaj(medya, dur)
    altyazilar = _altyazi_klipleri(words, font_path)
    marka = _marka_klipleri(dur, font_path)

    # use_bgclip=True: arka plan zaten tam ekran ve opak oldugu icin MoviePy'nin
    # her kare icin bos siyah tuval olusturmasi gereksiz. Olculdu: 184 -> 102 ms/kare.
    # Guvenlik: arka plan tam boyutta degilse varsayilan davranisa don.
    bg_tam = tuple(bg.size) == (W, H)
    try:
        final = CompositeVideoClip([bg, *altyazilar, *marka], size=(W, H), use_bgclip=bg_tam)
    except TypeError:      # cok eski moviepy: use_bgclip parametresi yok
        final = CompositeVideoClip([bg, *altyazilar, *marka], size=(W, H))
    final = final.with_audio(audio).with_duration(dur)

    # SINEMATIK acikken once HAM dosyaya yaz, sonra FFmpeg sinematik pasi out_path'e yazsin.
    ham = (out_path + ".raw.mp4") if SINEMATIK else out_path
    final.write_videofile(
        ham,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate=VIDEO_BITRATE,
        audio_bitrate=AUDIO_BITRATE,
        preset=X264_PRESET,
        threads=os.cpu_count() or 4,
        pixel_format="yuv420p",                       # her cihazda/YouTube'da dogru renk
        ffmpeg_params=["-profile:v", "high", "-level", "4.2", "-movflags", "+faststart"],
    )

    audio.close()
    bg.close()
    final.close()

    # --- FAZ 2: sinematik son-islem pasi (grade + grain + vignette + ambient) ---
    if SINEMATIK:
        try:
            ses, vhs = _sinematik_pas(ham, out_path)
            try:
                os.remove(ham)
            except OSError:
                pass
            print(f"  Sinematik pas uygulandi: grade + grain + vignette"
                  f"{' + VHS' if vhs else ''}{' + ambient ugultu' if ses == 'ambient' else ''}.")
        except Exception as e:
            print("  (sinematik pas atlandi, ham video kullaniliyor:", str(e)[:200], ")")
            os.replace(ham, out_path)


# =========================================================
#  8b) REMOTION ANIMASYON MOTORU
#      Python: senaryo + ses + kelime zamani + AI cizimleri hazirlar, props.json yazar.
#      Remotion (remotion/ klasoru): kamera hareketi, parallax, sis/toz/isik, gecisler,
#      karaoke altyazi, CASE FILE karti, CTA'lar, ses efektleri -> 1080x1920 mp4.
# =========================================================
_KAMERALAR = ["pushIn", "panLeft", "tiltUp", "pullOut", "dutch", "panRight", "pushIn", "tiltDown"]
_GECISLER  = ["zoom", "glitch", "zoom", "flash", "iris", "glitch"]


def animasyon_gorselleri(art_prompts, yedek_sorgular):
    """
    Her storyboard karesi icin ayni cizim stilinde AI illustrasyonu uretir.
    Yeterince gorsel cikmazsa (servis cokuk vb.) eski stok medya zincirine duser.
    [(yol, tur), ...] dondurur (thumbnail_olustur ile ayni format).
    """
    os.makedirs(MEDYA_KLASORU, exist_ok=True)
    for eski in os.listdir(MEDYA_KLASORU):
        try:
            os.remove(os.path.join(MEDYA_KLASORU, eski))
        except OSError:
            pass

    import time
    global _AI_ARDISIK_HATA
    # Pollinations ayni IP'den arka arkaya gelen istekleri kisitliyor (Actions'ta ilk kareden
    # sonra hepsi reddedildi). Animasyonda her kare onemli: istekler arasi bekle, basarisizsa
    # artan beklemeyle tekrar dene. Toplam sure butcesi Actions zaman asimini korur.
    bitis = time.time() + ANIM_GORSEL_BUTCE_SN
    medya = []
    for i, prompt in enumerate(art_prompts):
        hedef = os.path.join(MEDYA_KLASORU, f"anim_{i:02d}.jpg")
        print(f"  Sahne [{i+1}/{len(art_prompts)}]: {prompt[:90]}")
        cizildi = False
        for deneme, bekle in enumerate((0, 12, 25, 45)):
            if time.time() + bekle > bitis:
                break
            if bekle:
                print(f"    (bekleniyor {bekle} sn, deneme {deneme + 1})")
                time.sleep(bekle)
            _AI_ARDISIK_HATA = 0      # kosu geneli devre kesici animasyon karelerini durdurmasin
            # 1440x2560 artik ucretli (HTTP 402); 1080x1920 ucretsiz ve Remotion icin yeterli
            if _ai_gorsel(prompt, hedef, stil=_ANIM_STIL, boyutlar=[(1080, 1920)]):
                cizildi = True
                break
        if cizildi:
            medya.append((hedef, "foto"))
            time.sleep(ANIM_ISTEK_ARASI_SN)
        else:
            print("    -> cizilemedi")
        if time.time() > bitis:
            print("    (gorsel sure butcesi doldu)")
            break

    if len(medya) >= min(ANIM_MIN_GORSEL, len(art_prompts)):
        print(f"  Toplam {len(medya)} animasyon karesi hazir.")
        return medya

    print(f"  Sadece {len(medya)} AI karesi cikti -> stok medya zincirine geciliyor.")
    return arka_plan_indir(yedek_sorgular)


def _sahne_zamanlari(n, dur, gruplar):
    """
    n sahneyi sureye yayar; her kesmeyi en yakin ALTYAZI GRUBU baslangicina oturtur
    (kesme bir kelimenin ortasinda degil, yeni cumle parcasinda olur). Ilk kesme erken
    (~1.8 sn) -> kancadan hemen sonra goruntu degisir (pattern interrupt).
    """
    if n <= 1:
        return [(0.0, dur)]
    hedefler = [1.8] + [1.8 + (dur - 1.8) * k / (n - 1) for k in range(1, n - 1)]
    baslar = [g["start"] for g in gruplar] or [dur * k / n for k in range(n)]
    kesmeler, son = [], 0.0
    for h in hedefler:
        aday = min(baslar, key=lambda b: abs(b - h))
        if aday - son < 1.2 or aday > dur - 1.0:      # cok kisa sahne olmasin
            aday = h
        kesmeler.append(max(son + 1.0, aday))
        son = kesmeler[-1]
    zamanlar, bas = [], 0.0
    for k in kesmeler:
        zamanlar.append((bas, k))
        bas = k
    zamanlar.append((bas, dur))
    return zamanlar


def _ffmpeg_ses(ff, args, cikis):
    import subprocess
    subprocess.run([ff, "-y", *args, cikis], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return cikis


def _ses_efektleri_uret(ff, dur, ambient=True):
    """Harici asset gerektirmeden FFmpeg ile sentezlenen ses tasarimi."""
    sfx = {"boom": None, "whoosh": None, "hit": None, "pop": None}
    amb = None
    try:   # derin ambient drone: brown noise + 55 Hz ugultu, yavas nabiz
        amb = _ffmpeg_ses(ff, [
            "-f", "lavfi", "-i", f"anoisesrc=color=brown:amplitude=0.7:duration={dur + 2:.2f}:seed=7",
            "-f", "lavfi", "-i", f"sine=frequency=55:duration={dur + 2:.2f}",
            "-filter_complex",
            f"[0]lowpass=f=170,highpass=f=30,volume={AMBIENT_VOL}[n];[1]volume=0.05,tremolo=f=0.25:d=0.6[d];"
            "[n][d]amix=inputs=2:normalize=0", "-ar", "44100", "-ac", "2"],
            os.path.join(REMOTION_RUN, "ambient.wav")) if ambient else None
    except Exception as e:
        print("  (ambient uretilemedi:", str(e)[:80], ")")
    try:   # kanca "boom"u: alcak sinus dususu + gurultu, yavas sonumlenme
        sfx["boom"] = _ffmpeg_ses(ff, [
            "-f", "lavfi", "-i", "sine=frequency=46:duration=2.2",
            "-f", "lavfi", "-i", "anoisesrc=color=brown:amplitude=0.8:duration=2.2",
            "-filter_complex", "[0][1]amix=inputs=2:normalize=0,lowpass=f=200,afade=t=out:st=0.08:d=2.1,volume=2.4",
            "-ar", "44100", "-ac", "2"], os.path.join(REMOTION_RUN, "boom.wav"))
        sfx["whoosh"] = _ffmpeg_ses(ff, [
            "-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=0.9:duration=0.7",
            "-af", "highpass=f=300,lowpass=f=4000,afade=t=in:d=0.35,afade=t=out:st=0.35:d=0.35,volume=1.4",
            "-ar", "44100", "-ac", "2"], os.path.join(REMOTION_RUN, "whoosh.wav"))
        sfx["hit"] = _ffmpeg_ses(ff, [
            "-f", "lavfi", "-i", "sine=frequency=90:duration=0.6",
            "-f", "lavfi", "-i", "anoisesrc=color=white:amplitude=0.6:duration=0.6",
            "-filter_complex", "[0][1]amix=inputs=2:normalize=0,lowpass=f=1200,afade=t=out:st=0.02:d=0.55,volume=2",
            "-ar", "44100", "-ac", "2"], os.path.join(REMOTION_RUN, "hit.wav"))
        # cizgi film "pop"u: karakter/sahne girisinde kisa, yukari kayan ton
        sfx["pop"] = _ffmpeg_ses(ff, [
            "-f", "lavfi", "-i", "sine=frequency=520:duration=0.12",
            "-af", "vibrato=f=18:d=0.4,afade=t=out:st=0.02:d=0.1,volume=0.9",
            "-ar", "44100", "-ac", "2"], os.path.join(REMOTION_RUN, "pop.wav"))
    except Exception as e:
        print("  (ses efekti uretilemedi:", str(e)[:80], ")")
    try:   # sahne planindaki ozel efektler (yonetmen plani 'sfx' alani)
        sfx["creak"] = _ffmpeg_ses(ff, [
            "-f", "lavfi", "-i", "sine=frequency=140:duration=1.1",
            "-af", "vibrato=f=7:d=0.9,lowpass=f=900,afade=t=in:d=0.2,afade=t=out:st=0.6:d=0.5,volume=0.9",
            "-ar", "44100", "-ac", "2"], os.path.join(REMOTION_RUN, "creak.wav"))
        sfx["knock"] = _ffmpeg_ses(ff, [
            "-f", "lavfi", "-i", "anoisesrc=color=brown:amplitude=0.9:duration=1.2",
            "-af", "lowpass=f=260,volume='if(lt(mod(t,0.38),0.07),2.6,0)':eval=frame,afade=t=out:st=1.0:d=0.2",
            "-ar", "44100", "-ac", "2"], os.path.join(REMOTION_RUN, "knock.wav"))
        sfx["static"] = _ffmpeg_ses(ff, [
            "-f", "lavfi", "-i", "anoisesrc=color=white:amplitude=0.5:duration=0.9",
            "-af", "highpass=f=1200,lowpass=f=6000,tremolo=f=23:d=0.7,afade=t=out:st=0.6:d=0.3,volume=0.7",
            "-ar", "44100", "-ac", "2"], os.path.join(REMOTION_RUN, "static.wav"))
        sfx["heartbeat"] = _ffmpeg_ses(ff, [
            "-f", "lavfi", "-i", "sine=frequency=52:duration=1.6",
            "-af", "volume='if(lt(mod(t,0.8),0.09)+between(mod(t,0.8),0.2,0.27),2.8,0)':eval=frame,lowpass=f=150",
            "-ar", "44100", "-ac", "2"], os.path.join(REMOTION_RUN, "heartbeat.wav"))
    except Exception as e:
        print("  (sahne efekti uretilemedi:", str(e)[:80], ")")
    rel = lambda yol: ("run/" + os.path.basename(yol)) if yol else None
    return rel(amb), {k: rel(v) for k, v in sfx.items()}


def _dosya_karti(data, words):
    kart = data.get("case_card") if isinstance(data, dict) else None
    if not isinstance(kart, dict):
        return None
    ad = str(kart.get("name") or "").strip()[:34]
    yil = str(kart.get("year") or "").strip()[:12]
    yer = str(kart.get("place") or "").strip()[:34]
    if not (ad or yil):
        return None
    # Kart, anlaticinin yili soyledigi anda gelsin (yoksa kancadan hemen sonra)
    bas = 2.4
    for w in words:
        if yil and yil[:4] in w["word"]:
            bas = w["start"] - 0.3
            break
    return {"name": ad, "year": yil, "place": yer, "start": round(max(1.6, bas), 2)}


def _bulanik_kopya(yol):
    """Parallax arka katmani icin kucuk + bulanik + koyu kopya (Remotion'da canli blur pahali)."""
    bg = os.path.splitext(yol)[0] + "_bg.jpg"
    if os.path.exists(bg):
        return "run/" + os.path.basename(bg)
    try:
        from PIL import Image, ImageFilter, ImageEnhance
        with Image.open(yol) as im:
            k = im.convert("RGB").resize((360, 640))
        k = ImageEnhance.Brightness(k.filter(ImageFilter.GaussianBlur(5))).enhance(0.7)
        k.save(bg, quality=85)
        return "run/" + os.path.basename(bg)
    except Exception:
        return None


from derinlik import katmanlara_ayir, ortam_efektleri  # noqa: E402

PARALAKS = os.environ.get("PARALAKS", "1") != "0"
_PLAN_KAMERA = {"push_in": "pushIn", "pull_out": "pullOut", "pan_left": "panLeft", "pan_right": "panRight",
                "tilt_up": "tiltUp", "tilt_down": "tiltDown", "static": "static"}
_PLAN_ISIK = {"steady", "flicker", "dim_down", "reveal", "lightning"}
_ZAMAN_ATLAMA = re.compile(r"\b(later|next (?:day|night|morning)|years?|weeks?|months?|that night|morning|hours? later)\b", re.I)
_MIN_SAHNE_SN = 1.4


def _jeton(w):
    return re.sub(r"[^a-z0-9']", "", str(w).lower())


def anlatim_baslangiclari(planlar, words):
    """Her sahnenin 'narration' parcasinin seslendirmede BASLADIGI kelime indeksini bulur.
    Once beklenen konum (onceki parcalarin kelime sayisi) civarinda ilk 3 kelimeyi arar; bulamazsa
    beklenen konumu kullanir. Donus: artan indeks listesi (ilk sahne her zaman 0)."""
    jetonlar = [_jeton(w["word"]) for w in words]
    n = len(jetonlar)
    sonuc, beklenen, son = [], 0, -1
    for k, plan in enumerate(planlar):
        parca = [_jeton(t) for t in str((plan or {}).get("narration") or "").split()]
        parca = [t for t in parca if t]
        if k == 0:
            idx = 0
        else:
            idx = None
            bas3 = parca[:3]
            if bas3:
                for d in range(0, 14):
                    for aday in (beklenen + d, beklenen - d):
                        if son < aday < n - 1 and jetonlar[aday:aday + len(bas3)] == bas3:
                            idx = aday
                            break
                    if idx is not None:
                        break
            if idx is None:
                idx = min(max(son + 1, beklenen), n - 1) if parca else None
        if idx is None:   # anlatim parcasi verilmemis: esit paylastir
            idx = min(n - 1, max(son + 1, round(n * k / max(1, len(planlar)))))
        sonuc.append(idx)
        son = idx
        beklenen = idx + max(1, len(parca))
    return sonuc


def planli_sahneler(eslesme, words, dur, sfx_dosyalari=None):
    """Yonetmen planindan Remotion sahneleri: her gorsel BIR kez, kendi anlatim parcasinin
    basladigi kelimede acilir; kamera/isik/gecis/yazi/ses plandan gelir."""
    sfx_dosyalari = sfx_dosyalari or {}
    planlar = [p for _, p in eslesme]
    baslar = anlatim_baslangiclari(planlar, words)
    zamanlar = [0.0] + [max(0.0, words[i]["start"] - 0.08) for i in baslar[1:]]
    # cok kisa kalan sahneyi bir oncekiyle birlestir (gorsel kaybolmasin diye yerini sonrakine verir)
    secilen = []
    for k, t in enumerate(zamanlar):
        if secilen and t - secilen[-1][1] < _MIN_SAHNE_SN:
            continue
        if t > dur - 1.0 and k > 0:
            continue
        secilen.append((k, t))
    sahneler, onceki_kamera = [], []
    for j, (k, t) in enumerate(secilen):
        yol, plan = eslesme[k]
        bitis = secilen[j + 1][1] if j + 1 < len(secilen) else dur
        kamera = _PLAN_KAMERA.get(str(plan.get("move") or "").lower())
        if not kamera:
            kamera = "pushIn" if j == 0 else ("static" if str(plan.get("shot")) == "extreme_close" else
                                               ["pushIn", "panLeft", "pullOut", "panRight", "tiltUp"][j % 5])
        if onceki_kamera[-2:] == [kamera, kamera]:   # ayni hareket ust uste 3 kez olmasin
            kamera = "static" if kamera != "static" else "pushIn"
        onceki_kamera.append(kamera)
        isik = str(plan.get("light") or "steady").lower()
        devam = " ".join(str(plan.get(a) or "") for a in ("continuity", "narration"))
        gecis = "fade" if j > 0 and _ZAMAN_ATLAMA.search(devam) else "cut"
        yazi = re.sub(r"\s+", " ", str(plan.get("on_screen_text") or "")).strip().upper()
        sahneler.append({
            "src": yol, "kind": "image", "start": round(t, 3), "end": round(bitis, 3),
            "camera": kamera, "transition": gecis,
            "light": isik if isik in _PLAN_ISIK else "steady",
            "text": yazi if 0 < len(yazi.split()) <= 4 else "",
            "sfx": sfx_dosyalari.get(str(plan.get("sfx") or "").lower()),
            # efekt yalnizca GORSELDE gorunenden secilir (anlatimdaki "storm" bodruma yagmur yagdirmasin)
            "efekt": ortam_efektleri(" ".join(str(plan.get(a) or "") for a in ("image_prompt", "place"))),
        })
    return sahneler


def ekran_yazilari_cakisma(baslik, kanca, sahne_yazilari, script):
    """Baslik, kanca, sahne yazilari ve anlatim ayni cumleyi tekrar ediyor mu? Sorun listesi doner."""
    norm = lambda m: " ".join(_jeton(t) for t in str(m or "").split() if _jeton(t) and _jeton(t) != "shorts")
    sorunlar = []
    k = norm(kanca)
    if k:
        if k == norm(baslik) or (len(k) > 8 and k in norm(baslik)):
            sorunlar.append("kanca yazisi basligi tekrar ediyor")
        if len(k.split()) >= 3 and k in norm(_ilk_cumle(script)):
            sorunlar.append("kanca yazisi ilk anlatim cumlesini tekrar ediyor")
        if len(k.split()) > 6:
            sorunlar.append("kanca yazisi 6 kelimeden uzun")
    gorulen = set()
    for y in sahne_yazilari:
        n = norm(y)
        if not n:
            continue
        if n in gorulen or n == k:
            sorunlar.append(f"ekran yazisi tekrar ediyor: {y}")
        gorulen.add(n)
    return sorunlar


def remotion_olustur(words, medya, data, thumb_yazi, out_path, cizgi=False):
    import shutil
    import subprocess

    ff = _ffmpeg_yolu()
    if os.path.isdir(REMOTION_RUN):
        shutil.rmtree(REMOTION_RUN, ignore_errors=True)
    os.makedirs(REMOTION_RUN, exist_ok=True)

    # Anlatim: yayin seviyesine normalize (-14 LUFS, Shorts standardi)
    ses = os.path.join(REMOTION_RUN, "ses.wav")
    try:
        _ffmpeg_ses(ff, ["-i", AUDIO_FILE, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100", "-ac", "2"], ses)
    except Exception:
        _ffmpeg_ses(ff, ["-i", AUDIO_FILE, "-ar", "44100", "-ac", "2"], ses)
    dur = max(w["end"] for w in words) + 0.35

    gruplar = kelime_gruplari(words, WORDS_PER_CHUNK)
    captions = [{"start": round(g["start"], 3), "end": round(g["end"], 3),
                 "words": [{"word": w["word"], "start": round(w["start"], 3), "end": round(w["end"], 3)}
                           for w in g["words"]]} for g in gruplar]

    # Sahneler: medya sayisi az ise HEDEF_SAHNE_SN'yi korumak icin gorseller farkli kamera ile tekrar
    n = max(len(medya), min(MAX_SAHNE, math.ceil(dur / HEDEF_SAHNE_SN)))
    sahneler = []
    for i, (bas, son) in enumerate(_sahne_zamanlari(n, dur, gruplar)):
        src, tur, bg = None, "foto", None
        if medya:
            yol, tur = medya[i % len(medya)]
            ad = f"sahne_{i % len(medya):02d}" + os.path.splitext(yol)[1].lower()
            hedef = os.path.join(REMOTION_RUN, ad)
            if not os.path.exists(hedef):
                shutil.copyfile(yol, hedef)
            src = "run/" + ad
            bg = _bulanik_kopya(hedef) if tur != "video" else None
        sahneler.append({"src": src, "bg": bg,
                         "kind": "video" if tur == "video" else "image",
                         "start": round(bas, 3), "end": round(son, 3),
                         "camera": _KAMERALAR[i % len(_KAMERALAR)],
                         "transition": _GECISLER[i % len(_GECISLER)]})

    logo = None
    if os.path.exists(LOGO_PATH) and not cizgi:   # planli modda logo yok: alt sag kose YouTube dugmelerinin altinda kaliyordu
        shutil.copyfile(LOGO_PATH, os.path.join(REMOTION_RUN, "logo.png"))
        logo = "run/logo.png"

    ambient, sfx = _ses_efektleri_uret(ff, dur) if AMBIENT_SES else (None, {"boom": None, "whoosh": None, "hit": None})
    anahtar = [str(k) for k in (data.get("keywords") or [])][:6] if isinstance(data, dict) else []

    # Yonetmen plani: her gorsel kendi anlatim parcasinda, BIR kez (dongu ile tekrar yok)
    eslesme = (data.get("_sahne_medya") or []) if isinstance(data, dict) and cizgi else []
    planli = len(eslesme) >= ANIM_MIN_GORSEL
    if planli:
        kopya = []
        for i, (yol, plan) in enumerate(eslesme):
            ad = f"plan_{i:02d}" + os.path.splitext(yol)[1].lower()
            shutil.copyfile(yol, os.path.join(REMOTION_RUN, ad))
            kopya.append(("run/" + ad, plan))
        sfx_plan = {k: v for k, v in sfx.items() if v and k in ("boom", "hit", "whoosh", "creak", "knock", "static", "heartbeat")}
        sahneler = planli_sahneler(kopya, words, dur, sfx_plan)
        katmanli = 0
        for sh in sahneler:
            tam = os.path.join(REMOTION_RUN, os.path.basename(sh["src"]))
            sh["bg"] = _bulanik_kopya(tam)
            # 2.5D paralaks: derinlik haritasiyla on/arka plan katmanlari (ucretsiz, CPU)
            if PARALAKS:
                try:
                    k = katmanlara_ayir(tam, REMOTION_RUN, os.path.splitext(os.path.basename(tam))[0])
                except Exception as e:
                    k = None
                    print("    (paralaks atlandi:", str(e)[:80], ")")
                if k:
                    sh["fg"] = "run/" + os.path.basename(k["fg"])
                    sh["bgp"] = "run/" + os.path.basename(k["bg"])
                    katmanli += 1
        print(f"  Paralaks: {katmanli}/{len(sahneler)} sahne katmanli | efektler: "
              + ", ".join("+".join(sh.get("efekt") or []) for sh in sahneler))
    kanca = re.sub(r"\s+", " ", str((data or {}).get("hook_text") or "")).strip().upper() if planli else ""
    if kanca and ekran_yazilari_cakisma((data or {}).get("title", ""), kanca, [], (data or {}).get("script", "")):
        kanca = ""        # baslik/anlatimi tekrar eden kanca gosterilmez
    gercek = isinstance(data, dict) and data.get("aile", "gercek_vaka") == "gercek_vaka"
    if isinstance(data, dict):
        data["_ekran_plani"] = {"planli": planli, "kanca": kanca, "sahneler": sahneler,
                                "altyazi_ust": 1150 if cizgi else None, "altyazi_boyut": 80 if cizgi else 118}

    props = {
        "duration": round(dur, 3),
        "audio": "run/ses.wav",
        "ambient": ambient,
        "sfx": sfx,
        "captions": captions,
        "scenes": sahneler,
        "caseCard": _dosya_karti(data, words) if (gercek or not planli) else None,
        "headline": (thumb_yazi or "")[:40],
        "keywords": anahtar,
        "logo": logo,
        # Ekran ortasindaki SUBSCRIBE / WATCH NEXT haplari planli modda yok (ana nesneyi kapatiyordu)
        "subscribeAt": 0 if planli else round(dur * 0.45, 2),
        "watchNextAt": 0 if planli else (round(max(dur - 2.6, dur * 0.75), 2) if dur > 12 else 0),
        "cizgi": bool(cizgi),
        "hook": kanca,
        "band": False if cizgi else True,
    }
    props_yol = os.path.join(REMOTION_RUN, "props.json")
    with open(props_yol, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False)

    print(f"  Remotion render: {len(sahneler)} sahne, {dur:.1f} sn ...")
    _remotion_render("MysteryShort", props_yol, out_path)


def _remotion_render(kompozisyon, props_yol, out_path):
    import subprocess
    ff = _ffmpeg_yolu()
    ham = out_path + ".remotion.mp4"
    npx = "npx.cmd" if os.name == "nt" else "npx"
    komut = [npx, "remotion", "render", "src/index.ts", kompozisyon, ham,
             f"--props={props_yol}", "--codec=h264", f"--video-bitrate={VIDEO_BITRATE.replace('000k', 'M')}",
             f"--audio-bitrate={AUDIO_BITRATE}", f"--x264-preset={X264_PRESET}",
             "--pixel-format=yuv420p", f"--concurrency={os.cpu_count() or 2}", "--log=error"]
    # Render ~2-6 dk surer; takilirsa yedek motora gecilsin diye ust sinir
    subprocess.run(komut, cwd=REMOTION_DIR, check=True, timeout=20 * 60)

    # YouTube'da aninda oynasin diye moov atomu basa (+faststart), yeniden kodlama yok
    try:
        subprocess.run([ff, "-y", "-i", ham, "-c", "copy", "-movflags", "+faststart", out_path],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        os.remove(ham)
    except Exception:
        os.replace(ham, out_path)


# =========================================================
#  8c) STICKMAN (konusan cop adam) ANIMASYONU - varsayilan stil
#      Karakterler/dekor Remotion'da SVG olarak cizilir (AI gorseli gerekmez):
#      her videoda birebir ayni cizim dili, anlatimla senkron konusan agiz.
# =========================================================
_IFADELER = {"neutral", "scared", "shocked", "sad", "thinking", "angry", "happy"}
_POZLAR = {"idle", "point", "hands_up", "hands_on_head", "shrug", "walk"}
_SACLAR = {"none", "short", "messy", "long", "bun", "cap", "hat"}
_ARKAPLANLAR = {"plain", "room", "night", "forest", "sea", "sky", "office", "lab", "snow", "desert", "cave", "street"}
_OBJELER = {"none", "door", "window", "chair", "table", "phone", "radio", "map", "letter", "clock", "car", "ship",
            "plane", "lighthouse", "house", "tree", "grave", "box", "key", "footprints", "camera", "skull", "question"}

# Kanalin sabit anlaticisi: referanstaki kel, yuvarlak kafali, beyaz tisortlu karakter
_ANLATICI = {"skin": "#e8b07a", "shirt": "#f4f4f4", "hair": "none", "hairColor": "#2b2b2b",
             "glasses": False, "mustache": False, "beard": False}
_YEDEK_KADRO = [
    {"skin": "#f0a874", "shirt": "#4a4a4a", "hair": "messy", "hairColor": "#f2f2f2", "glasses": True, "mustache": True, "beard": False},
    {"skin": "#d99a6c", "shirt": "#3d5a80", "hair": "short", "hairColor": "#2b2b2b", "glasses": False, "mustache": False, "beard": False},
    {"skin": "#f2c29b", "shirt": "#b5523b", "hair": "long", "hairColor": "#6b3e26", "glasses": False, "mustache": False, "beard": False},
]


def _renk(deger, yedek):
    deger = str(deger or "").strip()
    return deger if re.fullmatch(r"#[0-9a-fA-F]{6}", deger) else yedek


def _gorunum(ham, yedek):
    ham = ham if isinstance(ham, dict) else {}
    sac = str(ham.get("hair") or "").lower()
    return {
        "skin": _renk(ham.get("skin"), yedek["skin"]),
        "shirt": _renk(ham.get("shirt"), yedek["shirt"]),
        "hair": sac if sac in _SACLAR else yedek["hair"],
        "hairColor": _renk(ham.get("hair_color") or ham.get("hairColor"), yedek["hairColor"]),
        "glasses": bool(ham.get("glasses", yedek["glasses"])),
        "mustache": bool(ham.get("mustache", yedek["mustache"])),
        "beard": bool(ham.get("beard", yedek["beard"])),
    }


def _stickman_sahneleri(data, dur, gruplar):
    """Gemini'nin storyboard'unu dogrular; eksik/bozuk alanlari guvenli varsayilanlarla doldurur."""
    ham = data.get("scenes") if isinstance(data, dict) else None
    ham = [s for s in (ham or []) if isinstance(s, dict)]
    if len(ham) < 4:   # storyboard yoksa: anlatici + konu kisisi donusumlu, cesitli dekor
        ham = [{"background": bg, "prop": pr, "characters": ch} for bg, pr, ch in [
            ("night", "question", [{"role": "narrator", "expression": "shocked", "pose": "point"}]),
            ("plain", "none", [{"role": "narrator", "expression": "neutral", "pose": "idle"},
                               {"role": "subject", "expression": "scared", "pose": "hands_on_head"}]),
            ("room", "clock", [{"role": "subject", "expression": "thinking", "pose": "shrug"}]),
            ("street", "none", [{"role": "subject", "expression": "scared", "pose": "walk"}]),
            ("office", "letter", [{"role": "narrator", "expression": "thinking", "pose": "point"}]),
            ("night", "footprints", [{"role": "subject", "expression": "sad", "pose": "idle"}]),
            ("plain", "skull", [{"role": "narrator", "expression": "shocked", "pose": "hands_up"}]),
        ]]
    ham = ham[:12]
    zamanlar = _sahne_zamanlari(len(ham), dur, gruplar)
    sahneler = []
    for (bas, son), s in zip(zamanlar, ham):
        bg = str(s.get("background") or "plain").lower()
        pr = str(s.get("prop") or "none").lower()
        karakterler = []
        for k in (s.get("characters") or [])[:2]:
            if not isinstance(k, dict):
                continue
            ifade = str(k.get("expression") or "neutral").lower()
            poz = str(k.get("pose") or "idle").lower()
            karakterler.append({"role": str(k.get("role") or "narrator").lower(),
                                "expression": ifade if ifade in _IFADELER else "neutral",
                                "pose": poz if poz in _POZLAR else "idle"})
        if not karakterler:
            karakterler = [{"role": "narrator", "expression": "neutral", "pose": "idle"}]
        etiket = str(s.get("label") or "").strip()[:20]
        sahneler.append({"start": round(bas, 3), "end": round(son, 3),
                         "background": bg if bg in _ARKAPLANLAR else "plain",
                         "prop": pr if pr in _OBJELER else "none",
                         "characters": karakterler, **({"label": etiket} if etiket else {})})
    return sahneler


# --- Hikayeye ozel sahne cizimi: Gemini her sahne icin SVG yazar (kalin kontur, duz renk) ---
_SVG_YASAK_ETIKET = {"script", "foreignobject", "image", "iframe", "object", "embed", "audio", "video", "style"}


def _svg_temizle(ham, genislik, yukseklik):
    """LLM'in yazdigi SVG'yi dogrular ve guvenli hale getirir. Gecersizse None."""
    import xml.etree.ElementTree as ET
    if not isinstance(ham, str) or "<svg" not in ham:
        return None
    ham = ham[ham.index("<svg"): ham.rindex("</svg>") + 6] if "</svg>" in ham else None
    if not ham or len(ham) > 120_000:
        return None
    try:
        kok = ET.fromstring(ham)
    except ET.ParseError:
        return None

    def ad(e):
        return e.tag.split("}")[-1].lower()

    if ad(kok) != "svg":
        return None
    sayac = 0
    for ebeveyn in list(kok.iter()):
        for cocuk in list(ebeveyn):
            if ad(cocuk) in _SVG_YASAK_ETIKET:
                ebeveyn.remove(cocuk)
    for e in kok.iter():
        sayac += 1
        for anahtar in list(e.attrib):
            kucuk = anahtar.split("}")[-1].lower()
            deger = e.attrib[anahtar]
            if kucuk.startswith("on") or (kucuk == "href" and not deger.startswith("#")) or "url(http" in deger:
                del e.attrib[anahtar]
    if sayac < 6:          # neredeyse bos cizim: kullanma
        return None
    kok.set("viewBox", kok.get("viewBox") or f"0 0 {genislik} {yukseklik}")
    kok.set("width", str(genislik))
    kok.set("height", str(yukseklik))
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    metin = ET.tostring(kok, encoding="unicode")
    if "xmlns=" not in metin[:200]:
        metin = metin.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    return metin


def sahne_cizimleri(data, sahneler, words, hedef_klasor):
    """
    Her sahne icin hikayeye OZEL arka plan + anahtar obje SVG'si ister (tek Gemini cagrisi).
    Basarili olanlar sahneye bgSvg/propSvg olarak eklenir; olmayanlar kodlu dekorla kalir.
    """
    # Varsayilan KAPALI: hikaye gorselleri artik Cloudflare FLUX ile ciziliyor (SVG_SAHNE=1 ile acilir)
    if MANUAL_MODE or not GEMINI_API_KEY or os.environ.get("SVG_SAHNE", "0") != "1":
        return 0
    ham_sahneler = data.get("scenes") if isinstance(data, dict) else None
    ham_sahneler = [s for s in (ham_sahneler or []) if isinstance(s, dict)]
    satirlar = []
    for i, s in enumerate(sahneler):
        anlatim = " ".join(w["word"] for w in words if s["start"] - 0.05 <= w["start"] < s["end"])
        h = ham_sahneler[i] if i < len(ham_sahneler) else {}
        satirlar.append(json.dumps({
            "i": i, "narration": anlatim,
            "place": str(h.get("place") or s["background"]),
            "key_object": str(h.get("key_object") or (s["prop"] if s["prop"] != "none" else "")),
        }, ensure_ascii=False))
    cizimler = {}
    # 4'erli gruplar: tek dev yanit kesilip gecersiz JSON olmasin
    for bas in range(0, len(satirlar), 4):
        grup = satirlar[bas:bas + 4]
        cevap = _sahne_cizim_iste(data, grup)
        for c in (cevap.get("scenes") or []) if isinstance(cevap, dict) else []:
            try:
                cizimler[int(c.get("i"))] = c
            except (TypeError, ValueError):
                continue
    adet = 0
    for i, s in enumerate(sahneler):
        c = cizimler.get(i) or {}
        bg = _svg_temizle(c.get("bg"), 1080, 1920)
        pr = _svg_temizle(c.get("prop"), 600, 600)
        if bg:
            with open(os.path.join(hedef_klasor, f"bg_{i:02d}.svg"), "w", encoding="utf-8") as f:
                f.write(bg)
            s["bgSvg"] = f"run/bg_{i:02d}.svg"
            adet += 1
        if pr:
            with open(os.path.join(hedef_klasor, f"obje_{i:02d}.svg"), "w", encoding="utf-8") as f:
                f.write(pr)
            s["propSvg"] = f"run/obje_{i:02d}.svg"
    print(f"      Hikayeye ozel cizim: {adet}/{len(sahneler)} sahne arka plani, "
          f"{sum(1 for s in sahneler if s.get('propSvg'))} anahtar obje")
    return adet


def _sahne_cizim_iste(data, satirlar):
    prompt = f"""You are the background artist of a 2D cartoon YouTube Shorts channel (talking stickman style).
Story: {data.get('topic', '')}

Draw each scene below as hand-written SVG code. STRICT STYLE (every scene must look like the same cartoon):
- Flat fill colors, slightly muted palette; simple geometric shapes; at most simple linearGradient for skies.
- Thick black outlines on every shape: stroke="#141414" stroke-width="8" (6 for small details), stroke-linejoin="round", stroke-linecap="round".
- NO people, NO characters, NO faces (the characters are added on top later). NO text or letters. NO <image>, <script>, <style>, <foreignObject>, external links.
- Keep each SVG compact (under 60 shapes).

For EACH scene return two SVGs:
1) "bg": the full environment, viewBox="0 0 1080 1920". The ground/floor line MUST be exactly at y=1560 (characters stand on it).
   Characters will stand between x=150 and x=930, from y=650 to y=1560: keep that zone simple (wall / sky / sea),
   put the story-specific details (furniture, ship parts, windows, buildings, trees, era details) at the edges, the top and on the floor.
   It must clearly show THIS scene's exact place and era from the narration (e.g. a 19th-century ship deck in fog, a 1990s airport parking lot at night).
2) "prop": the ONE key object of this beat that the narration talks about (e.g. a wedding ring, a VCR, a ship's logbook), viewBox="0 0 600 600",
   transparent background, the object fills ~80% of the box and sits on the bottom edge. If there is no clear object return "".

Scenes:
{chr(10).join(satirlar)}

Return ONLY JSON: {{"scenes": [{{"i": 0, "bg": "<svg ...>...</svg>", "prop": "<svg ...>...</svg>"}}]}}"""
    try:
        return _gemini_cagir(prompt)
    except Exception as e:
        print("      (sahne cizimi alinamadi, kodlu dekor kullanilacak:", str(e)[:120], ")")
        return {}


def stickman_olustur(words, data, thumb_yazi, out_path, thumb_path=None):
    """Konusan cop adam videosu uretir; thumb_path verilirse temiz bir kareyi PNG olarak da cizer."""
    import shutil
    import subprocess

    ff = _ffmpeg_yolu()
    if os.path.isdir(REMOTION_RUN):
        shutil.rmtree(REMOTION_RUN, ignore_errors=True)
    os.makedirs(REMOTION_RUN, exist_ok=True)

    ses = os.path.join(REMOTION_RUN, "ses.wav")
    try:
        _ffmpeg_ses(ff, ["-i", AUDIO_FILE, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100", "-ac", "2"], ses)
    except Exception:
        _ffmpeg_ses(ff, ["-i", AUDIO_FILE, "-ar", "44100", "-ac", "2"], ses)
    dur = max(w["end"] for w in words) + 0.35

    gruplar = kelime_gruplari(words, WORDS_PER_CHUNK)
    yuvarla = lambda w: {"word": w["word"], "start": round(w["start"], 3), "end": round(w["end"], 3)}
    captions = [{"start": round(g["start"], 3), "end": round(g["end"], 3),
                 "words": [yuvarla(w) for w in g["words"]]} for g in gruplar]

    kadro_ham = data.get("cast") if isinstance(data, dict) and isinstance(data.get("cast"), dict) else {}
    yedek = random.choice(_YEDEK_KADRO)
    cast = {"narrator": dict(_ANLATICI)}
    for rol, gor in kadro_ham.items():
        rol = str(rol).lower()
        if rol != "narrator":
            cast[rol] = _gorunum(gor, yedek)
    cast.setdefault("subject", dict(yedek))
    cast.setdefault("other", _gorunum({}, _YEDEK_KADRO[(_YEDEK_KADRO.index(yedek) + 1) % len(_YEDEK_KADRO)]))
    sahneler = _stickman_sahneleri(data, dur, gruplar)
    for s in sahneler:   # storyboard'da tanimsiz rol -> konu kisisi
        for k in s["characters"]:
            if k["role"] not in cast:
                k["role"] = "subject"
    sahne_cizimleri(data, sahneler, words, REMOTION_RUN)

    logo = None
    if os.path.exists(LOGO_PATH):
        shutil.copyfile(LOGO_PATH, os.path.join(REMOTION_RUN, "logo.png"))
        logo = "run/logo.png"
    _, sfx = _ses_efektleri_uret(ff, dur, ambient=False)
    anahtar = [str(k) for k in (data.get("keywords") or [])][:6] if isinstance(data, dict) else []

    kart = _dosya_karti(data, words)
    props = {
        "duration": round(dur, 3),
        "audio": "run/ses.wav",
        "sfx": sfx,
        "captions": captions,
        "words": [yuvarla(w) for w in words],
        "cast": cast,
        "scenes": sahneler,
        "caseCard": kart,
        "headline": (thumb_yazi or "")[:40],
        "keywords": anahtar,
        "logo": logo,
        # SUBSCRIBE dosya kartiyla ayni anda cikmasin
        "subscribeAt": round(max(dur * 0.45, (kart["start"] + 3.9) if kart else 0), 2),
        "watchNextAt": round(max(dur - 2.6, dur * 0.75), 2) if dur > 12 else 0,
    }
    props_yol = os.path.join(REMOTION_RUN, "props.json")
    with open(props_yol, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False)

    print(f"  Remotion render (stickman): {len(sahneler)} sahne, {dur:.1f} sn ...")
    _remotion_render("StickmanShort", props_yol, out_path)

    if thumb_path:
        # Thumbnail tabani: en carpici sahnenin (sok/korku) yazisiz temiz karesi
        sec = next((s for s in sahneler if any(k["expression"] in ("shocked", "scared") for k in s["characters"])),
                   sahneler[0])
        kare = int(((sec["start"] + sec["end"]) / 2) * FPS)
        temiz_yol = os.path.join(REMOTION_RUN, "props_temiz.json")
        with open(temiz_yol, "w", encoding="utf-8") as f:
            json.dump({**props, "temiz": True}, f, ensure_ascii=False)
        npx = "npx.cmd" if os.name == "nt" else "npx"
        try:
            subprocess.run([npx, "remotion", "still", "src/index.ts", "StickmanShort", thumb_path,
                            f"--props={temiz_yol}", f"--frame={kare}", "--log=error"], cwd=REMOTION_DIR, check=True,
                           timeout=5 * 60)
        except Exception as e:
            # Video hazir; thumbnail karesi olmasa da video atilmasin (thumbnail videodan kare alir)
            print("      (thumbnail karesi cizilemedi, videodan kare kullanilacak:", str(e)[:120], ")")
            return None
        return thumb_path
    return None


# =========================================================
#  8d) CLOUDFLARE WORKERS AI (FLUX) - hikayeye ozel cizgi film sahneleri
#      Ucretsiz: gunluk 10.000 neuron (~100+ dikey gorsel). Anahtar yoksa / hata verirse
#      stickman (kodla cizim) yedegine dusulur, video yine uretilir.
# =========================================================
# Gorsel yonetmenlik. A = mevcut cizgi dilinin iyilestirilmisi (varsayilan), B = daha sinematik isik,
# daha yakin ana nesne. Ikisi de: tek net odak, koyu lacivert/siyah golge + kontrollu sicak sari isik.
_CF_ORTAK = ("one clear focal subject, uncluttered composition with depth (foreground, subject, background), "
             "deep navy blue and black shadows, a single controlled warm yellow light source, "
             "consistent character design, natural hands with five fingers, objects never have faces, "
             "each person appears only once in the frame, no half-cut figures at the frame edges, "
             "faces in the middle of the frame, lower third kept simple and dark, "
             "vertical 9:16 composition, no text, no letters, no captions, no watermark, no logo")
_CF_STILLER = {
    "A": ("polished 2D cartoon illustration, clean bold black ink outlines, rich flat colors with soft cel shading, "
          "expressive faces and clear body language, cinematic mystery mood, " + _CF_ORTAK),
    "B": ("cinematic 2D illustrated film still, refined ink outlines, painterly low-key lighting with strong "
          "chiaroscuro, moody atmosphere with light haze, shallow depth of field, the key object large and close "
          "in frame, subtle film grain, " + _CF_ORTAK),
}
GORSEL_STIL = (os.environ.get("GORSEL_STIL") or "B").strip().upper()   # B: kullanici secimi (25.10.2026)
if GORSEL_STIL == "AB":
    # Deney modu (yalnizca kullanici onayiyla acilir): stiller gune gore donusumlu, her hikaye TEK stille
    # yayinlanir; ayni video iki kez yuklenmez. Olcum: kanal_analiz.py --haftalik "Gorsel stil A/B".
    GORSEL_STIL = "AB"[datetime.date.today().toordinal() % 2]
if GORSEL_STIL not in _CF_STILLER:
    GORSEL_STIL = "B"
_CF_STIL = _CF_STILLER[GORSEL_STIL]
_CF_PLAN = {"extreme_close": "extreme close-up shot", "close": "close-up shot",
            "medium": "medium shot", "wide": "wide establishing shot"}


def cf_hazir():
    return bool(CF_HESAP and CF_TOKEN)


def _dikey_kirp(path):
    """Gorseli ortadan 9:16 kirpar ve 1080x1920'ye getirir (FLUX kare cikti verebilir)."""
    from PIL import Image, ImageFilter
    with Image.open(path) as im:
        im = im.convert("RGB")
        w, h = im.size
        hedef = 9 / 16
        if w / h > hedef:
            yeni_w = int(h * hedef)
            x0 = (w - yeni_w) // 2
            im = im.crop((x0, 0, x0 + yeni_w, h))
        elif w / h < hedef:
            yeni_h = int(w / hedef)
            y0 = (h - yeni_h) // 2
            im = im.crop((0, y0, w, y0 + yeni_h))
        boyut = im.size
        im = im.resize((1080, 1920), Image.LANCZOS)
        if boyut[0] < 1000:   # buyutulduyse hafif netlestir
            im = im.filter(ImageFilter.UnsharpMask(radius=1.6, percent=70, threshold=2))
        im.save(path, quality=93)
    return boyut


def _cf_istek(model, metin, tohum):
    """Tek istek. Donus: (durum_kodu, base64_gorsel_veya_None, hata_metni)."""
    import requests
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_HESAP}/ai/run/{model}"
    bas = {"Authorization": f"Bearer {CF_TOKEN}"}
    if "flux-2" in model:   # multipart form alanlari; adim sayisi modelde sabit (4)
        alanlar = {"prompt": (None, metin), "width": (None, "864"), "height": (None, "1536"),
                   "seed": (None, str(tohum))}
        r = requests.post(url, headers=bas, files=alanlar, timeout=120)
    else:                   # flux-1-schnell yalnizca prompt + steps kabul eder (kare cikti)
        r = requests.post(url, headers=bas, json={"prompt": metin, "steps": 8}, timeout=120)
    if r.status_code != 200:
        return r.status_code, None, r.text[:200]
    sonuc = (r.json() or {}).get("result") or {}
    return 200, sonuc.get("image"), "" if sonuc.get("image") else str(sonuc)[:160]


def cf_gorsel(prompt, hedef, tohum, stil=None):
    """Tek gorsel uretir. Basariliysa True. Gecici hatada bekler; ana model olmazsa yedek modele gecer."""
    import base64
    import time
    metin = f"{prompt}, {_CF_STILLER.get(stil or GORSEL_STIL, _CF_STIL)}"[:2000]
    for model in dict.fromkeys([CF_MODEL, CF_YEDEK_MODEL]):
        for deneme in range(3):
            try:
                kod, b64, hata = _cf_istek(model, metin, tohum)
            except Exception as e:
                kod, b64, hata = 0, None, str(e)[:120]
            if b64:
                with open(hedef, "wb") as f:
                    f.write(base64.b64decode(b64))
                boyut = _dikey_kirp(hedef)
                print(f"    (FLUX {model.split('/')[-1]} {boyut[0]}x{boyut[1]} -> 1080x1920)")
                return True
            print(f"    (FLUX {model.split('/')[-1]} HTTP {kod}: {hata})")
            if kod in (401, 403):
                return False      # anahtar/izin sorunu: tekrar denemenin anlami yok
            if kod == 400:
                break             # parametre hatasi: bu modelde tekrar deneme, yedek modele gec
            time.sleep(8 * (deneme + 1) if kod == 429 else 3)
    return False


_ANLATICI_RE = re.compile(r"\b(?:an?|the)\s+(?:stick ?man\s+)?(?:narrator|presenter|stick ?man)\b", re.I)


_B_YAKINLAS = {"wide": "medium", "medium": "close", "close": "close", "extreme_close": "extreme_close"}


def b_plani(data):
    """Stil B'nin plan kurallari: ana nesne daha yakin (genis -> orta, orta -> yakin plan) ve
    sahne yazisi yok (ekranda yalnizca ilk karedeki kanca). data yerinde degisir ve geri doner."""
    for sh in (data or {}).get("scenes") or []:
        if isinstance(sh, dict):
            sh["shot"] = _B_YAKINLAS.get(str(sh.get("shot") or "").lower(), "close")
            sh["on_screen_text"] = ""
    return data


def sahne_promptu(sahne, look_bible="", ilk=False):
    """Sahne planindan FLUX metni: plan olcegi + sahne tarifi + sabit karakter/mekan tarifi.
    ilk=True: kanca yazisi ust bolgede durur -> ust ceyrek bos ve koyu kalsin, yuz ortada."""
    tarif = _ANLATICI_RE.sub("a frightened witness", str(sahne.get("image_prompt") or "").strip())
    if not tarif:
        return ""
    plan = _CF_PLAN.get(str(sahne.get("shot") or "").lower(), "")
    parca = [plan, tarif]
    if sahne.get("focus"):
        parca.append("focus on " + str(sahne["focus"])[:120])
    if look_bible:
        parca.append("consistent look: " + str(look_bible)[:300])
    if ilk:
        parca.append("the top quarter of the frame is empty dark background with no face or object in it")
    return ", ".join(p for p in parca if p)


def flux_sahneleri(data, sorgular, stil=None, klasor=None):
    """Gemini'nin sahne planindan gorselleri uretir -> [(yol, 'foto'), ...]
    Ayrica data['_sahne_medya'] = [(yol, sahne_plani), ...]: hangi gorselin hangi anlatim
    parcasina ait oldugu (kurgu bu eslemeyle yapilir, gorseller dongu ile tekrarlanmaz)."""
    klasor = klasor or MEDYA_KLASORU
    os.makedirs(klasor, exist_ok=True)
    for eski in os.listdir(klasor):
        try:
            os.remove(os.path.join(klasor, eski))
        except OSError:
            pass
    sahneler = [s for s in (data.get("scenes") or []) if isinstance(s, dict)] if isinstance(data, dict) else []
    look = str(data.get("look_bible") or "") if isinstance(data, dict) else ""
    planli = [(sahne_promptu(s, look, ilk=(i == 0)), s) for i, s in enumerate(sahneler)]
    planli = [(t, s) for t, s in planli if t]
    if not planli:   # eski yanit bicimi: yalnizca sorgu listesi
        planli = [(_ANLATICI_RE.sub("a frightened witness", str(q)), {})
                  for q in (data.get("art_prompts") or sorgular or [])]
    tohum = random.randint(1, 10_000_000)
    medya, eslesme = [], []
    for i, (tarif, sahne) in enumerate(planli[:10]):
        hedef = os.path.join(klasor, f"flux_{i:02d}.jpg")
        print(f"  Sahne [{i+1}/{min(len(planli), 10)}] {sahne.get('shot', '')}/{sahne.get('move', '')}: {tarif[:90]}")
        # ayni tohum ailesi: karakterlerin cizimi sahneler arasi daha tutarli kalir
        if cf_gorsel(tarif, hedef, tohum + i, stil):
            medya.append((hedef, "foto"))
            eslesme.append((hedef, sahne))
        else:
            print("    -> cizilemedi (bu anlatim parcasi komsu sahneye eklenir)")
    if isinstance(data, dict):
        data["_sahne_medya"] = eslesme
    print(f"  Toplam {len(medya)} FLUX sahnesi hazir.")
    return medya


# =========================================================
#  9) OTOMATIK THUMBNAIL (tiklanma orani icin)
# =========================================================
def _kare_puani(kare):
    """Bir karenin 'thumbnail olarak carpiciligi': detay yuksek + parlaklik dengeli."""
    g = kare.astype("float32").mean(axis=2)
    detay = g.std()
    ceza = 1.0 - min(1.0, abs(g.mean() - 110.0) / 120.0)   # ne cok karanlik ne patlamis
    return detay * (0.45 + 0.55 * ceza)


def _en_iyi_kare(medya, video_path=None):
    """
    Thumbnail icin en carpici kareyi ARKA PLAN MEDYALARINDAN secer.

    ONEMLI: kare bilerek son videodan DEGIL, kaynak medyadan alinir. Son videoda
    altyazilar goruntuye yanmis durumda; oradan alinan bir thumbnail'de altyazi ile
    thumbnail yazisi ust uste binip okunmaz bir kalabalik olusturuyordu.
    """
    import numpy as np
    from PIL import Image

    en_iyi, en_iyi_puan = None, -1.0
    for path, tur in (medya or []):
        kareler = []
        try:
            if tur == "video":
                from moviepy import VideoFileClip
                with VideoFileClip(path) as v:
                    for oran in (0.25, 0.5, 0.75):
                        kareler.append(np.asarray(v.get_frame(min(v.duration * oran,
                                                                  max(0.0, v.duration - 0.05)))))
            else:
                kareler.append(np.asarray(Image.open(path).convert("RGB")))
        except Exception:
            continue
        for kare in kareler:
            if kare is None or kare.ndim != 3:
                continue
            puan = _kare_puani(kare)
            if puan > en_iyi_puan:
                en_iyi_puan, en_iyi = puan, kare

    if en_iyi is not None:
        return en_iyi

    # Hic kaynak medya okunamadiysa son care: uretilen videodan bir kare
    if video_path and os.path.exists(video_path):
        from moviepy import VideoFileClip
        with VideoFileClip(video_path) as v:
            return np.asarray(v.get_frame(v.duration * 0.3))
    raise RuntimeError("thumbnail icin kare bulunamadi")


def _metni_sar(draw, metin, font, max_genislik):
    """Metni verilen genisliğe sigacak sekilde satirlara boler."""
    kelimeler = metin.split()
    satirlar, aktif = [], ""
    for k in kelimeler:
        deneme = (aktif + " " + k).strip()
        if draw.textlength(deneme, font=font) <= max_genislik or not aktif:
            aktif = deneme
        else:
            satirlar.append(aktif)
            aktif = k
    if aktif:
        satirlar.append(aktif)
    return satirlar


def thumbnail_olustur(medya, metin, out_path, video_path=None):
    """
    Arka plan medyalarinin en carpici karesinden 1080x1920 thumbnail uretir:
    kontrast/doygunluk artirimi + vinyet + alt/ust karartma + kalin sari baslik + logo.
    """
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

    kare = _en_iyi_kare(medya, video_path)
    im = Image.fromarray(kare).convert("RGB")
    if im.size != (W, H):
        oran = max(W / im.width, H / im.height)
        im = im.resize((int(im.width * oran), int(im.height * oran)), Image.LANCZOS)
        sol = (im.width - W) // 2
        ust = (im.height - H) // 2
        im = im.crop((sol, ust, sol + W, ust + H))

    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=130, threshold=3))
    im = ImageEnhance.Contrast(im).enhance(1.22)
    im = ImageEnhance.Color(im).enhance(1.15)
    im = ImageEnhance.Brightness(im).enhance(0.96)

    # Vinyet + alt karartma (yazinin okunurlugu ve sinematik his)
    katman = Image.new("L", (W, H), 0)
    kat_d = ImageDraw.Draw(katman)
    for i in range(H):
        if i < H * 0.22:
            a = int(150 * (1 - i / (H * 0.22)))
        elif i > H * 0.55:
            a = int(215 * ((i - H * 0.55) / (H * 0.45)))
        else:
            a = 0
        kat_d.line([(0, i), (W, i)], fill=a)
    im = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), im, katman)

    d = ImageDraw.Draw(im)
    yazi = (metin or "").strip().upper()[:44] or "UNSOLVED"
    font_yolu = _font_bul()

    # Yaziyi 2 satira sigacak en buyuk puntoyla yaz
    punto, satirlar, font = 190, [], None
    while punto >= 80:
        try:
            font = ImageFont.truetype(font_yolu, punto)
        except Exception:
            font = ImageFont.load_default()
            satirlar = [yazi]
            break
        satirlar = _metni_sar(d, yazi, font, int(W * 0.88))
        if len(satirlar) <= 3:
            break
        punto -= 12

    satir_y = int(punto * 1.12)
    toplam_y = satir_y * len(satirlar)
    y = int(H * 0.66) - toplam_y // 2
    for s in satirlar:
        g = d.textlength(s, font=font)
        d.text(((W - g) / 2, y), s, font=font, fill=(255, 214, 0),
               stroke_width=max(8, punto // 14), stroke_fill=(0, 0, 0))
        y += satir_y

    # Kose logosu
    try:
        if os.path.exists(LOGO_PATH):
            lg = Image.open(LOGO_PATH).convert("RGBA")
            kb = int(W * 0.16)
            lg = lg.resize((kb, kb), Image.LANCZOS)
            im.paste(lg, (40, 44), lg)
    except Exception as e:
        print("    (thumbnail logosu atlandi:", str(e)[:70], ")")

    im.save(out_path, "JPEG", quality=92, subsampling=0)
    kb = os.path.getsize(out_path) / 1024
    # YouTube siniri 2MB
    if kb > 1900:
        im.save(out_path, "JPEG", quality=82)
    print(f"      Thumbnail hazir -> {out_path} ({os.path.getsize(out_path)/1024:.0f} KB)")
    return out_path


# =========================================================
#  10) YouTube'a yukle (+ thumbnail bas)
# =========================================================
def youtube_yukle(dosya, baslik, aciklama, etiket_listesi, thumb_path=None):
    import time, ssl, socket
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    youtube = youtube_servisi()
    body = {
        "snippet": {
            "title": baslik[:100],
            "description": aciklama[:4900],
            "tags": etiket_listesi,
            "categoryId": CATEGORY_ID,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {"privacyStatus": PRIVACY, "selfDeclaredMadeForKids": False},
    }
    # Parcali (resumable) yukleme: tek bir SSL/ag kopmasi TUM yuklemeyi degil, yalnizca
    # o parcayi etkiler; alttaki dongu ayni yerden devam eder. chunksize=-1 (tek istek)
    # kullaniliyordu ve gecici bir SSLEOFError butun kosuyu cokertiyordu.
    media = MediaFileUpload(dosya, chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    istek = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print("  YouTube'a yukleniyor...")
    resp = None
    hata = 0
    MAX_HATA = 6
    while resp is None:
        try:
            status, resp = istek.next_chunk()
            if status:
                print(f"    Yukleniyor: %{int(status.progress() * 100)}")
        except HttpError as e:
            # Sadece gecici sunucu hatalarinda (5xx) tekrar dene; digerlerinde firlat
            if getattr(e, "resp", None) is not None and e.resp.status in (500, 502, 503, 504):
                hata += 1
                if hata > MAX_HATA:
                    raise
                bekle = min(60, 2 ** hata)
                print(f"    (YouTube {e.resp.status} -> {bekle}s sonra tekrar {hata}/{MAX_HATA})")
                time.sleep(bekle)
            else:
                raise
        except (ssl.SSLError, socket.timeout, ConnectionError, BrokenPipeError, TimeoutError, OSError) as e:
            # SSLEOFError dahil gecici ag kopmalari -> ayni yerden devam et
            hata += 1
            if hata > MAX_HATA:
                raise
            bekle = min(60, 2 ** hata)
            print(f"    (gecici ag hatasi: {type(e).__name__} -> {bekle}s sonra tekrar {hata}/{MAX_HATA})")
            time.sleep(bekle)
    video_id = resp["id"]
    print("  Yuklendi! Video ID:", video_id)
    print("  Link:", "https://youtu.be/" + video_id)

    # Thumbnail: kanal DOGRULANMAMISSA YouTube reddeder -> video yine de yayinda kalir
    if thumb_path and os.path.exists(thumb_path):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumb_path, mimetype="image/jpeg")).execute()
            print("  Thumbnail yuklendi.")
        except Exception as e:
            mesaj = str(e)
            if "403" in mesaj or "forbidden" in mesaj.lower():
                print("  (Thumbnail yuklenemedi: kanalin DOGRULANMIS olmasi gerekiyor.")
                print("   youtube.com/verify adresinden telefonla dogrula, sonra otomatik calisacak.)")
            else:
                print("  (Thumbnail yuklenemedi:", mesaj[:140], ")")
    return video_id


# =========================================================
#  10b) YAYIN PAKETI + VIDEO KAYITLARI
#       Uretim ile yayin ayridir: her kosu cikti/paket/ altina video + thumbnail + meta.json
#       yazar ve kalite kontrolunden gecirir. yayinla.py bu paketi (onay sonrasi) yukler.
# =========================================================
PAKET_KLASORU = os.path.join(BASE_DIR, "cikti", "paket")
VIDEOLAR_FILE = os.path.join(BASE_DIR, "veri", "videolar.json")


def _json_oku(yol, varsayilan):
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return varsayilan


def _json_yaz(yol, veri):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
    os.replace(gecici, yol)   # yarim yazilmis dosya kalmaz


def video_kaydi_ekle(kayit):
    kayitlar = _json_oku(VIDEOLAR_FILE, {"videolar": []})
    kayitlar.setdefault("videolar", []).append(kayit)
    _json_yaz(VIDEOLAR_FILE, kayitlar)


def video_kaydi_guncelle(paket_id, **alanlar):
    kayitlar = _json_oku(VIDEOLAR_FILE, {"videolar": []})
    for k in kayitlar.get("videolar", []):
        if k.get("paket_id") == paket_id:
            k.update(alanlar)
            break
    _json_yaz(VIDEOLAR_FILE, kayitlar)
    # gecmis.json'daki konu kaydina da video kimligini yaz (analiz eslestirmesi icin)
    if alanlar.get("video_id") and os.path.exists(GECMIS_FILE):
        g = _json_oku(GECMIS_FILE, {})
        for k in (g.get("videolar") or []):
            if k.get("paket_id") == paket_id:
                k["video_id"] = alanlar["video_id"]
        _json_yaz(GECMIS_FILE, g)


def aciklama_son_hali(aciklama, aile, kaynak, motor):
    """Kurgu etiketi / kaynak satiri / AI cizim notu: izleyiciyi yaniltmayan aciklama."""
    satirlar = [aciklama.strip()]
    if aile in ("hayatta_kalma", "ozgun_korku") and KURGU_NOTU not in aciklama:
        satirlar.insert(0, KURGU_NOTU)
    if aile == "gercek_vaka" and kaynak.get("url") and kaynak["url"] not in aciklama:
        satirlar.append("Source: " + kaynak["url"])
    if motor in ("cloudflare-flux", "pollinations"):
        satirlar.append("Illustrations created with AI image tools; story, edit and narration produced by Unsadark.")
    return "\n\n".join(s for s in satirlar if s)


def gorsel_on_tarama(data):
    """Sahne gorsellerini Gemini goruntu modeline gosterir: gorselde yazi/harf, bozuk el-yuz-nesne,
    anlatimla uyumsuzluk var mi? Ucretsiz katman, tek istek. Sonuc KESIN DEGILDIR: yalnizca uyari uretir.
    Donus: {'yapildi': bool, 'bulgular': [...], 'neden': str}"""
    eslesme = (data or {}).get("_sahne_medya") or []
    if not eslesme or not GEMINI_API_KEY or os.environ.get("GORSEL_TARAMA", "1") == "0":
        return {"yapildi": False, "bulgular": [], "neden": "tarama kapali ya da gorsel yok"}
    try:
        import io
        from google.genai import types
        from PIL import Image
        parcalar = [(
            "You are a strict visual QC reviewer for a vertical illustrated story video. For EACH numbered "
            "image check: (a) any visible text, letters, numbers or watermark inside the picture; (b) broken "
            "anatomy (extra/missing fingers, melted or duplicated faces, twisted limbs) or broken objects; "
            "(c) does the picture plausibly show the narration line given for it; (d) does the main character "
            "look consistent with this description: " + str(data.get("look_bible") or "-")[:300] + ". "
            'Answer ONLY JSON: {"images": [{"i": 1, "text": false, "anatomy": false, "matches": true, '
            '"consistent": true, "note": "max 12 words"}]}')]
        for i, (yol, plan) in enumerate(eslesme[:10], 1):
            with Image.open(yol) as im:
                k = im.convert("RGB")
                k.thumbnail((432, 768))
                tampon = io.BytesIO()
                k.save(tampon, "JPEG", quality=80)
            parcalar.append(f"Image {i}. Narration: {str(plan.get('narration') or '')[:200]}")
            parcalar.append(types.Part.from_bytes(data=tampon.getvalue(), mime_type="image/jpeg"))
        sonuc = _gemini_cagir(parcalar)
        bulgular = []
        for g in (sonuc.get("images") or []):
            if not isinstance(g, dict):
                continue
            sorun = [ad for ad, kotu in (("gorselde yazi", g.get("text")), ("bozuk anatomi/nesne", g.get("anatomy")),
                                          ("anlatimla uyumsuz", g.get("matches") is False),
                                          ("karakter tutarsiz", g.get("consistent") is False)) if kotu]
            if sorun:
                bulgular.append(f"sahne {g.get('i')}: {', '.join(sorun)} ({str(g.get('note') or '')[:60]})")
        print(f"      Gorsel on-tarama: {len(bulgular)} olasi sorun" + (" -> " + " | ".join(bulgular[:3]) if bulgular else ""))
        return {"yapildi": True, "bulgular": bulgular, "neden": ""}
    except Exception as e:
        print("      (gorsel on-tarama yapilamadi:", str(e)[:120], ")")
        return {"yapildi": False, "bulgular": [], "neden": "tarama hatasi: " + str(e)[:80]}


def _ekran_plani_ozeti(data, baslik, script):
    """meta.json'a yazilacak yonetmen plani ozeti + ekran yazisi cakisma kontrolu."""
    plan = dict((data or {}).get("_ekran_plani") or {})
    if not plan:
        return None
    sahneler = plan.get("sahneler") or []
    plan["sahneler"] = [{k: (os.path.basename(v) if k in ("src", "bg", "sfx") and v else v)
                         for k, v in sh.items()} for sh in sahneler]
    plan["band"] = False
    plan["yazi_sorunlari"] = ekran_yazilari_cakisma(baslik, plan.get("kanca"), [sh.get("text") for sh in sahneler], script)
    return plan


def yayin_paketi_hazirla(baslik, aciklama, etiketler, thumb, aile, konu, topic_type, script, kaynak, motor,
                         sahneler, notlar, data=None):
    import shutil
    import uuid
    import kalite_kontrol as kk

    if os.path.isdir(PAKET_KLASORU):
        shutil.rmtree(PAKET_KLASORU, ignore_errors=True)
    os.makedirs(PAKET_KLASORU, exist_ok=True)
    simdi = datetime.datetime.now(datetime.timezone.utc)
    paket_id = simdi.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    video = os.path.join(PAKET_KLASORU, "video.mp4")
    if os.path.exists(OUTPUT_FILE):
        shutil.copyfile(OUTPUT_FILE, video)
    if thumb and os.path.exists(thumb):
        shutil.copyfile(thumb, os.path.join(PAKET_KLASORU, "thumbnail.jpg"))

    medya_kaynagi = {"cloudflare-flux": ["cloudflare-flux"], "kod-cizim": ["kod-cizim"],
                     "pollinations": ["pollinations"], "stok": ["pexels", "pixabay", "pollinations"]}.get(motor, [])
    meta = {
        "paket_id": paket_id,
        "olusturma": simdi.isoformat(),
        "github_run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "aile": aile, "konu": konu, "topic_type": topic_type,
        "baslik": baslik, "aciklama": aciklama, "etiketler": etiketler,
        "script": script, "sahne_tarifleri": sahneler,
        "kaynak": kaynak, "gorsel_motoru": motor,
        "medya_kaynagi": medya_kaynagi + ["edge-tts", "sentetik-ses"],
        "maliyet_usd": 0.0,   # tum servisler ucretsiz katmanda
        "uretim_notlari": notlar,
        "gorsel_stil": GORSEL_STIL if motor == "cloudflare-flux" else "",
        "gorsel_sayisi": len((data or {}).get("_sahne_medya") or []),
        "kanca_yazisi": ((data or {}).get("_ekran_plani") or {}).get("kanca", ""),
        "look_bible": (data or {}).get("look_bible", ""),
        "sahne_plani": [{k: sh.get(k) for k in ("narration", "purpose", "focus", "emotion", "shot", "move", "light",
                                                 "on_screen_text", "continuity", "sfx")}
                        for sh in ((data or {}).get("scenes") or []) if isinstance(sh, dict)],
    }
    gorsel_klasoru = None
    if motor == "cloudflare-flux" and data is not None:
        meta["ekran_plani"] = _ekran_plani_ozeti(data, baslik, script)
        meta["gorsel_tarama"] = gorsel_on_tarama(data)
        # Sahne gorselleri pakete: inceleme ve A/B karsilastirmasi icin
        gorsel_klasoru = os.path.join(PAKET_KLASORU, "sahneler")
        os.makedirs(gorsel_klasoru, exist_ok=True)
        for yol, _ in (data.get("_sahne_medya") or []):
            if os.path.exists(yol):
                shutil.copyfile(yol, os.path.join(gorsel_klasoru, os.path.basename(yol)))
    print("[QC] Kalite + uygunluk kontrolu:")
    sonuc = kk.kontrol_et(video, meta, gorsel_klasoru=gorsel_klasoru)
    kk.ozet_yazdir(sonuc)
    meta["kalite"] = sonuc
    meta["sure_sn"] = round(kk.video_bilgisi(video)["sure"] or 0, 2) if os.path.exists(video) else 0
    _json_yaz(os.path.join(PAKET_KLASORU, "meta.json"), meta)

    video_kaydi_ekle({
        "paket_id": paket_id, "olusturma": meta["olusturma"], "aile": aile, "konu": konu,
        "topic_type": topic_type, "baslik": baslik, "sure_sn": meta["sure_sn"],
        "gorsel_motoru": motor, "gorsel_stil": meta["gorsel_stil"], "maliyet_usd": 0.0, "kalite_gecti": sonuc["gecti"],
        "kalite_hatalari": [k["kontrol"] for k in sonuc["kontroller"] if k["durum"] == "KALDI"],
        "uretim_notlari": notlar, "kaynak_url": kaynak.get("url", ""),
        "durum": "onay_bekliyor" if sonuc["gecti"] else "kalite_reddi",
        "video_id": "", "github_run_id": meta["github_run_id"],
    })
    return {"klasor": PAKET_KLASORU, "meta": meta}


# =========================================================
#  11) ANA AKIS
# =========================================================
def main():
    performans, viraller = None, []
    data = {}

    if MANUAL_MODE:
        script     = senaryo_metni
        baslik     = video_basligi
        aciklama   = video_aciklamasi
        etiket_lst = etiketler
        sorgular   = gorsel_sorgulari
        konu       = "manuel"
        thumb_yazi = thumbnail_yazisi
        print("MANUEL MOD: yapistirilan senaryo kullaniliyor.")
    else:
        print("[1/6] Kendini gelistirme: kanal performansi + nisteki viral videolar inceleniyor...")
        if UPLOAD_TO_YOUTUBE or os.path.exists(TOKEN_FILE):
            performans = kanal_performansi()
            gecmisi_kanaldan_tohumla(performans)   # yayinlanmis videolar da tekrar edilmesin
            viraller = viral_ornekleri_getir()
        else:
            print("      (YouTube yetkisi yok -> ogrenme katmani atlandi)")

        print("[2/6] Gemini ile BENZERSIZ konu + senaryo + gorsel kelimeleri uretiliyor...")
        data       = gemini_uret(performans, viraller)
        konu       = (data.get("topic") or "").strip()
        script     = data["script"]
        baslik     = data["title"]
        aciklama   = data["description"]
        etiket_lst = data.get("tags", [])
        thumb_yazi = (data.get("thumbnail_text") or "").strip()
        baslik, aciklama, etiket_lst = _seo_duzenle(baslik, aciklama, etiket_lst, konu, data.get("aile", "gercek_vaka"))
        sorgular   = data.get("visual_queries", []) or etiket_lst
        print("      Konu      :", konu)
        print("      Baslik    :", baslik)
        print("      Hook      :", _ilk_cumle(script))
        print("      Thumbnail :", thumb_yazi)
        print("      Gorseller :", ", ".join(sorgular))

    # Seslendirme + kelime zamanlamasi
    print("[3/6] Seslendiriliyor (edge-tts)...")
    words = asyncio.run(seslendir_ve_zamanla(script, VOICE, AUDIO_FILE))
    print(f"      {len(words)} kelime seslendirildi -> {AUDIO_FILE}")
    if not words:
        raise RuntimeError("edge-tts kelime zamanlamasi dondurmedi. Senaryo bos olabilir.")

    anim = RENDER_MOTORU == "remotion" and os.path.isdir(REMOTION_DIR)
    stick = anim and RENDER_STIL == "stickman"
    art = [str(a).strip() for a in (data.get("art_prompts") or []) if str(a).strip()]
    hazir = False
    medya = []
    motor = ""                 # hangi gorsel motoru kullanildi (lisans/kalite kaydi icin)
    uretim_notlari = []        # yedege dusmeler vb. (veri/videolar.json'a yazilir)
    if stick and cf_hazir():
        # Hikayeye ozel cizgi film sahneleri (Cloudflare FLUX, ucretsiz kota)
        print("[4/6] Hikaye sahneleri ciziliyor (Cloudflare FLUX)...")
        if GORSEL_STIL == "B":
            b_plani(data)
        medya = flux_sahneleri(data, sorgular)
        if len(medya) >= ANIM_MIN_GORSEL:
            print("[5/6] Video kurgulaniyor (Remotion)...")
            try:
                remotion_olustur(words, medya, data, thumb_yazi, OUTPUT_FILE, cizgi=True)
                hazir = True
                motor = "cloudflare-flux"
            except Exception as e:
                print("      (FLUX videosu render edilemedi, stickman yedegine geciliyor:", str(e)[:200], ")")
        else:
            print("      (yeterli FLUX sahnesi yok, stickman yedegine geciliyor)")
            uretim_notlari.append(f"FLUX yetersiz ({len(medya)} sahne), stickman yedegi")
        if not hazir:
            medya = []
    if stick and not hazir:
        # Gorsel indirme yok: karakterler ve dekor Remotion'da cizilir
        print("[4/6] Stickman animasyonu render ediliyor (Remotion)... (birkac dakika surebilir)")
        try:
            os.makedirs(MEDYA_KLASORU, exist_ok=True)
            kare = stickman_olustur(words, data, thumb_yazi, OUTPUT_FILE,
                                    thumb_path=os.path.join(MEDYA_KLASORU, "stickman_kare.png"))
            hazir = True
            motor = motor or "kod-cizim"
            if kare:
                medya = [(kare, "foto")]
        except Exception as e:
            print("      (Stickman render basarisiz, AI/stok yedegine geciliyor:", str(e)[:200], ")")
    if hazir:
        pass                      # stickman videosu hazir, gorsel gerekmez
    elif anim:
        # Storyboard yoksa (eski model yaniti / manuel mod) gorsel sorgulari cizim komutu olur
        art = art or [str(q) for q in sorgular]
        print("[4/6] Animasyon kareleri ciziliyor (AI, tek stil)...")
        medya = animasyon_gorselleri(art, sorgular)
    else:
        print("[4/6] Yuksek cozunurluklu arka plan medyasi indiriliyor...")
        medya = arka_plan_indir(sorgular)

    # Video + altyazi
    if anim and not hazir:
        print("[5/6] Animasyon render ediliyor (Remotion)... (birkac dakika surebilir)")
        try:
            remotion_olustur(words, medya, data, thumb_yazi, OUTPUT_FILE)
            hazir = True
            motor = "pollinations"
        except Exception as e:
            print("      (Remotion basarisiz, MoviePy yedek motoruna geciliyor:", str(e)[:200], ")")
            uretim_notlari.append("Remotion hatasi, MoviePy yedegi: " + str(e)[:120])
    if not hazir:
        print("[5/6] Video kurgulaniyor (MoviePy)... (biraz surebilir)")
        video_olustur(words, medya, OUTPUT_FILE)
        motor = "stok"
    print("      Video hazir ->", OUTPUT_FILE)

    # Thumbnail
    thumb = None
    try:
        thumb = thumbnail_olustur(medya, thumb_yazi or baslik, THUMB_FILE, OUTPUT_FILE)
    except Exception as e:
        print("      (thumbnail uretilemedi, video yine de yuklenecek:", str(e)[:140], ")")

    # --- Yayin paketi + kalite/uygunluk kontrolu (uretim ve yayin birbirinden ayri) ---
    aile = data.get("aile") or ("gercek_vaka" if not MANUAL_MODE else "")
    kaynak = data.get("kaynak") or {}
    aciklama = aciklama_son_hali(aciklama, aile, kaynak, motor)
    paket = yayin_paketi_hazirla(
        baslik=baslik, aciklama=aciklama, etiketler=etiket_lst, thumb=thumb, aile=aile, konu=konu,
        topic_type=(data.get("topic_type") or "").strip(), script=script, kaynak=kaynak, motor=motor,
        sahneler=[s.get("image_prompt", "") for s in (data.get("scenes") or []) if isinstance(s, dict)],
        notlar=uretim_notlari, data=data)
    gecti = paket["meta"]["kalite"]["gecti"]

    # YouTube: yalnizca acikca istenmisse (UPLOAD_TO_YOUTUBE=1) VE kalite kontrolu gectiyse.
    # Varsayilan akis 'onay': video paketlenir, kullanici yayinla.yml ile onaylayinca yuklenir.
    video_id = ""
    if UPLOAD_TO_YOUTUBE and gecti:
        print("[6/6] YouTube yukleme (dogrudan, UPLOAD_TO_YOUTUBE=1)...")
        video_id = youtube_yukle(OUTPUT_FILE, baslik, aciklama, etiket_lst, thumb) or ""
        video_kaydi_guncelle(paket["meta"]["paket_id"], video_id=video_id, durum="yayinlandi",
                             gizlilik=PRIVACY)
    elif UPLOAD_TO_YOUTUBE:
        print("[6/6] Kalite kontrolunden GECMEDI -> YouTube'a yuklenmedi.")
    else:
        print(f"[6/6] Onay bekliyor: paket -> {PAKET_KLASORU} (yayinlamak icin yayinla.yml)")

    # Hafizaya yaz -> bu hikaye BIR DAHA ASLA uretilmez
    if not MANUAL_MODE:
        gecmise_ekle({
            "topic": konu,
            "title": baslik,
            "description": (data.get("description") or "").strip(),
            "topic_type": (data.get("topic_type") or "").strip(),
            "aile": aile,
            "hook": _ilk_cumle(script),
            "kanca_yazisi": (data.get("_ekran_plani") or {}).get("kanca", ""),
            "tema": data.get("tema", ""),
            "gorsel_stil": GORSEL_STIL if motor == "cloudflare-flux" else "",
            "tarih": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "video_id": video_id,
            "paket_id": paket["meta"]["paket_id"],
        })
        print("      Konu kalici hafizaya yazildi (gecmis.json).")

    if not gecti:
        # Basarisiz video basarili gibi isaretlenmez: is KIRMIZI biter, paket 'kalite_reddi' kalir
        raise RuntimeError("Video kalite/uygunluk kontrolunden gecmedi (ayrintilar yukarida, paket meta.json'da).")
    print("\nBITTI - tamamlandi.")


if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception as e:
        print("\nHATA:", type(e).__name__, "-", e)
        traceback.print_exc()
        sys.exit(1)
