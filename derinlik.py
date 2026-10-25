# -*- coding: utf-8 -*-
"""
2.5D PARALAKS: tek bir illustrasyonu derinlik haritasiyla iki katmana ayirir.

  on plan  -> karakter / yakin nesne, yumusak kenarli kesik (RGBA PNG)
  arka plan -> on planin yeri doldurulmus (inpaint) tam kare (JPG)

Remotion bu iki katmani farkli hizlarda hareket ettirir: kamera yaklasirken on plan arka
plandan daha hizli buyur/kayar -> "yasayan" derinlik hissi. Tamamen ucretsiz ve CPU'da calisir:
Depth-Anything-V2-Small (ONNX, ~99 MB, Apache-2.0) + onnxruntime + OpenCV.

Model ilk kullanimda Hugging Face'ten indirilir ve DERINLIK_MODEL yoluna (varsayilan
~/.cache/unsadark/) kaydedilir; GitHub Actions bu klasoru onbellege alir.
"""
import os

MODEL_URL = "https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx"
MODEL_YOLU = os.environ.get("DERINLIK_MODEL") or os.path.join(os.path.expanduser("~"), ".cache", "unsadark",
                                                                "depth_anything_v2_small.onnx")
GIRIS = (294, 518)            # 14'un katlari, 9:16'ya yakin (genislik, yukseklik)
ON_PLAN_ALAN = (0.10, 0.60)   # on plan bu oran disinda kalirsa paralaks yapilmaz (ayrim guvenilmez)

_oturum = None


def model_hazirla():
    """Modeli (gerekirse indirip) yukler. Basarisizsa None."""
    global _oturum
    if _oturum is not None:
        return _oturum
    try:
        import onnxruntime as ort
    except ImportError:
        print("  (paralaks kapali: onnxruntime kurulu degil)")
        return None
    if not os.path.exists(MODEL_YOLU) or os.path.getsize(MODEL_YOLU) < 50_000_000:
        try:
            import requests
            os.makedirs(os.path.dirname(MODEL_YOLU), exist_ok=True)
            print("  Derinlik modeli indiriliyor (~99 MB, bir kez)...")
            gecici = MODEL_YOLU + ".part"
            with requests.get(MODEL_URL, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(gecici, "wb") as f:
                    for parca in r.iter_content(1 << 20):
                        f.write(parca)
            os.replace(gecici, MODEL_YOLU)
        except Exception as e:
            print("  (derinlik modeli indirilemedi, paralaks kapali:", str(e)[:100], ")")
            return None
    secenek = ort.SessionOptions()
    secenek.intra_op_num_threads = os.cpu_count() or 2
    _oturum = ort.InferenceSession(MODEL_YOLU, secenek, providers=["CPUExecutionProvider"])
    return _oturum


def derinlik_haritasi(rgb):
    """rgb: HxWx3 uint8 -> HxW float32, 0 = uzak, 1 = yakin."""
    import cv2
    import numpy as np
    oturum = model_hazirla()
    if oturum is None:
        return None
    h, w = rgb.shape[:2]
    x = cv2.resize(rgb, GIRIS, interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255.0
    x = (x - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
    x = x.transpose(2, 0, 1)[None]
    d = oturum.run(None, {"pixel_values": x})[0][0]
    d = cv2.resize(d, (w, h), interpolation=cv2.INTER_CUBIC)
    lo, hi = np.percentile(d, 2), np.percentile(d, 98)
    return np.clip((d - lo) / max(1e-6, hi - lo), 0, 1).astype(np.float32)


def _esik(d):
    """On plan esigi: Otsu (derinlik histogrami), alan sinirlarina kistirilmis."""
    import cv2
    import numpy as np
    d8 = (d * 255).astype(np.uint8)
    t, _ = cv2.threshold(d8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    t = t / 255.0
    alan = float((d > t).mean())
    if alan > ON_PLAN_ALAN[1]:
        t = float(np.percentile(d, 100 * (1 - ON_PLAN_ALAN[1])))
    elif alan < ON_PLAN_ALAN[0]:
        t = float(np.percentile(d, 100 * (1 - ON_PLAN_ALAN[0])))
    return t


def katmanlara_ayir(yol, hedef_klasor, ad):
    """Gorseli on/arka plan katmanina ayirir. Donus: {'fg': yol, 'bg': yol, 'alan': oran} ya da None."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None
    bgr = cv2.imread(yol)
    if bgr is None:
        return None
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    d = derinlik_haritasi(rgb)
    if d is None:
        return None
    t = _esik(d)
    maske = (d > t).astype(np.uint8)
    # kucuk adaciklari at, en buyuk parcalari tut (gurultulu tek pikseller kesik gibi gorunmesin)
    n, etiket, ist, _ = cv2.connectedComponentsWithStats(maske, 8)
    min_alan = maske.size * 0.01
    temiz = np.zeros_like(maske)
    for i in range(1, n):
        if ist[i, cv2.CC_STAT_AREA] >= min_alan:
            temiz[etiket == i] = 1
    alan = float(temiz.mean())
    if not (ON_PLAN_ALAN[0] * 0.8 <= alan <= ON_PLAN_ALAN[1]):
        return None
    # Kenarlar: hafif kapama + yumusak gecis (sert kesik kenari "cikartma" gibi gorunur)
    cekirdek = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    temiz = cv2.morphologyEx(temiz, cv2.MORPH_CLOSE, cekirdek)
    alfa = cv2.GaussianBlur(temiz.astype(np.float32), (0, 0), 5.0)
    alfa = np.clip(alfa * 1.15, 0, 1)
    # Zemin/su gibi kareyi alttan kaplayan yakin yuzeyler ayri hareket edince yatay dikis izi
    # birakiyordu: on plan karenin alt kismina dogru yumusakca soner (orada iki katman ayni kalir).
    h0 = alfa.shape[0]
    rampa = np.clip((0.92 - np.arange(h0, dtype=np.float32) / h0) / 0.32, 0, 1)[:, None]
    alfa = alfa * rampa

    # Arka plan: on planin yeri (genisletilmis) yarim cozunurlukte doldurulur, sonra buyutulur
    genis = cv2.dilate(temiz, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
    h, w = genis.shape
    kucuk = cv2.resize(bgr, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    kucuk_m = cv2.resize(genis, (w // 2, h // 2), interpolation=cv2.INTER_NEAREST)
    dolu = cv2.inpaint(kucuk, kucuk_m * 255, 9, cv2.INPAINT_TELEA)
    dolu = cv2.resize(dolu, (w, h), interpolation=cv2.INTER_CUBIC)
    dolu = cv2.GaussianBlur(dolu, (0, 0), 1.2)
    gm = cv2.GaussianBlur(genis.astype(np.float32), (0, 0), 6)[..., None]
    # On planin sondugu alt bolgede arka plan orijinal kalir (doldurulmus bulanik alan gorunmesin)
    gm = gm * np.clip(rampa * 1.6, 0, 1)[..., None]
    arka = (bgr * (1 - gm) + dolu * gm).astype(np.uint8)

    os.makedirs(hedef_klasor, exist_ok=True)
    fg_yol = os.path.join(hedef_klasor, f"{ad}_fg.png")
    bg_yol = os.path.join(hedef_klasor, f"{ad}_bgp.jpg")
    rgba = np.dstack([bgr, (alfa * 255).astype(np.uint8)])
    cv2.imwrite(fg_yol, rgba, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    cv2.imwrite(bg_yol, arka, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return {"fg": fg_yol, "bg": bg_yol, "alan": round(alan, 3)}


# ------------------------------------------------------------------ ortam efektleri
_IC_MEKAN = ("basement", "cellar", "room", "indoor", "inside", "interior", "cabin", "hallway", "kitchen", "office",
             "corridor", "attic", "elevator", "apartment", "hotel", "ward", "store", "mall", "car interior")
_EFEKT_KELIME = [
    ("yagmur", ("rain", "downpour", "drizzle", "rainy")),
    ("kar", ("snow", "blizzard", "snowy", "snowfall")),
    ("kabarcik", ("underwater", "scuba", "under the surface", "beneath the water", "air bubbles")),
    ("kivilcim", ("fire", "candle", "fireplace", "ember", "torch", "wildfire", "burning", "hearth")),
    ("sis", ("fog", "mist", "haze", "smoke", "steam", "foggy")),
]


def ortam_efektleri(metin, en_fazla=2):
    """Sahne tarifinden ortam efekti secimi (deterministik). Hicbiri yoksa ic mekan icin 'toz'."""
    t = " " + str(metin or "").lower() + " "
    sec = [ad for ad, kelimeler in _EFEKT_KELIME if any(k in t for k in kelimeler)]
    if any(k in t for k in _IC_MEKAN):
        # kapali mekanda gokten yagan efekt olmaz (pencereden gorunse bile kareye yayilirdi)
        sec = [e for e in sec if e not in ("yagmur", "kar")]
    if not sec:
        sec = ["sis"] if any(k in t for k in ("outside", "forest", "road", "street", "field", "night sky")) else ["toz"]
    return sec[:en_fazla]
