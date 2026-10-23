# -*- coding: utf-8 -*-
"""
Ses tasarimi: TUM efektler ve muzik numpy/scipy ile SENTEZLENIR.
Disaridan indirilen ses dosyasi yoktur -> lisans sorunu yoktur, cevrimdisi calisir.

Olaylar [(t, tur, guc)] zaman cizelgesinden gelir (adimlar render sirasinda iskeletten tespit edilir),
her olay tam o anda miks'e yerlestirilir. Son miks: tepe -1 dBFS, ortalama ~-16 dBFS (RMS).
"""
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 44100
_rng = np.random.default_rng(7)


def _gurultu(n, tohum=0):
    return np.random.default_rng(tohum).standard_normal(n).astype(np.float32)


def _filtre(x, tur, f):
    sos = butter(2, f, btype=tur, fs=SR, output="sos")
    return sosfilt(sos, x).astype(np.float32)


def _zarf(n, atak=0.005, sonum=0.2):
    t = np.arange(n) / SR
    a = np.minimum(1.0, t / max(atak, 1e-4))
    return (a * np.exp(-t / max(sonum, 1e-4))).astype(np.float32)


def _norm(x, tepe=1.0):
    m = np.max(np.abs(x)) or 1.0
    return (x / m * tepe).astype(np.float32)


# ------------------------------------------------------------------ efektler
def adim(tohum=0, sert=1.0):
    n = int(0.11 * SR)
    t = np.arange(n) / SR
    darbe = _filtre(_gurultu(n, tohum), "lowpass", 900) * _zarf(n, 0.002, 0.025)
    gum = np.sin(2 * np.pi * 75 * t) * _zarf(n, 0.003, 0.04)
    return _norm(darbe * 0.8 + gum * 0.7, 0.55 * sert)


def kapi_gicirti(sure=1.0):
    """Takil-kay surtunmesi: degisen hizda darbe dizisi rezonanstan gecer."""
    n = int(sure * SR)
    t = np.arange(n) / SR
    hiz = 35 + 120 * (t / sure) + 25 * np.sin(2 * np.pi * 3 * t)
    faz = np.cumsum(hiz / SR)
    darbeler = (np.diff(np.floor(faz), prepend=0) > 0).astype(np.float32)
    darbeler *= 0.6 + 0.4 * _rng.random(n).astype(np.float32)
    ton = _filtre(darbeler, "bandpass", [700, 1600])
    ton += 0.35 * _filtre(darbeler, "bandpass", [1800, 2600])
    zarf = np.minimum(1, t / 0.08) * np.minimum(1, (sure - t) / 0.15)
    return _norm(ton * zarf, 0.6)


def zombi_inilti(sure=1.5, perde=82.0, tohum=1):
    n = int(sure * SR)
    t = np.arange(n) / SR
    f = perde * (1 + 0.07 * np.sin(2 * np.pi * 5.3 * t) + 0.15 * np.sin(2 * np.pi * 0.7 * t))
    faz = np.cumsum(f / SR)
    testere = 2 * (faz - np.floor(faz)) - 1
    x = _filtre(testere.astype(np.float32), "lowpass", 700) + 0.25 * _filtre(_gurultu(n, tohum), "bandpass", [200, 900])
    # agiz acilip kapanmasi (formant gibi) + kaba hirilti
    x *= 0.6 + 0.4 * np.sin(2 * np.pi * 2.1 * t) ** 2
    zarf = np.minimum(1, t / 0.15) * np.minimum(1, (sure - t) / 0.4)
    return _norm(np.tanh(2.2 * x) * zarf, 0.7)


def vurus_sting(sure=1.8):
    """Korku 'sting'i: alcak patlama + uyumsuz tiz kume."""
    n = int(sure * SR)
    t = np.arange(n) / SR
    bum = np.sin(2 * np.pi * (48 - 14 * t) * t) * _zarf(n, 0.002, 0.45)
    bum += 0.6 * _filtre(_gurultu(n, 3), "lowpass", 160) * _zarf(n, 0.002, 0.3)
    kume = sum(np.sin(2 * np.pi * f * t) for f in (1180, 1252, 1331, 1409)) / 4
    kume *= _zarf(n, 0.01, 0.7) * (0.7 + 0.3 * np.sin(2 * np.pi * 9 * t))
    return _norm(np.tanh(1.5 * bum) + 0.35 * kume, 0.95)


def whoosh(sure=0.5):
    n = int(sure * SR)
    t = np.arange(n) / SR
    g = _gurultu(n, 5)
    alcak = _filtre(g, "bandpass", [300, 1200])
    yuksek = _filtre(g, "bandpass", [1500, 5000])
    u = t / sure
    x = alcak * (1 - u) + yuksek * u
    zarf = np.sin(np.pi * u) ** 2
    return _norm(x * zarf, 0.6)


def dusme_gumu():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * (70 - 30 * t) * t) * _zarf(n, 0.002, 0.12)
    x += 0.7 * _filtre(_gurultu(n, 8), "lowpass", 500) * _zarf(n, 0.001, 0.06)
    return _norm(np.tanh(2 * x), 0.85)


def nefes_cigligi(sure=0.6):
    """Kisa korku nefesi (sentetik): filtreli gurultu, hizli atak."""
    n = int(sure * SR)
    t = np.arange(n) / SR
    x = _filtre(_gurultu(n, 11), "bandpass", [900, 3200]) * _zarf(n, 0.02, 0.25)
    return _norm(x, 0.45)


EFEKTLER = {
    "adim": lambda g, i: adim(i, g), "kapi": lambda g, i: kapi_gicirti(1.0),
    "zombi": lambda g, i: zombi_inilti(1.5, 78 + 8 * (i % 3), i), "sting": lambda g, i: vurus_sting(),
    "whoosh": lambda g, i: whoosh(0.5), "dusme": lambda g, i: dusme_gumu(), "nefes": lambda g, i: nefes_cigligi(),
}
EFEKT_SEVIYE = {"adim": 0.35, "kapi": 0.6, "zombi": 0.75, "sting": 0.9, "whoosh": 0.5, "dusme": 0.8, "nefes": 0.5}


# ------------------------------------------------------------------ muzik yataklari
def ambiyans(sure, tohum=0):
    n = int(sure * SR)
    t = np.arange(n) / SR
    x = _filtre(np.cumsum(_gurultu(n, tohum)) * 0.02, "lowpass", 220)   # kahverengi gurultu
    x = _filtre(x, "highpass", 30)
    drone = 0.5 * np.sin(2 * np.pi * 55 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * t))
    return _norm(x * 0.7 + drone * 0.5, 0.5)


def gerilim_muzigi(sure, bpm_bas=70, bpm_son=140):
    """Hizlanan kalp atisi + alcak ostinato: kovalamaca gerilimi."""
    n = int(sure * SR)
    t = np.arange(n) / SR
    bpm = bpm_bas + (bpm_son - bpm_bas) * (t / sure)
    vurus_faz = np.cumsum(bpm / 60 / SR)
    x = np.zeros(n, dtype=np.float32)
    k = int(0.18 * SR)
    kt = np.arange(k) / SR
    lub = (np.sin(2 * np.pi * 52 * kt) * np.exp(-kt / 0.07)).astype(np.float32)
    for i in np.nonzero(np.diff(np.floor(vurus_faz), prepend=0) > 0)[0]:
        for gecikme, g in ((0, 1.0), (int(0.16 * SR), 0.7)):   # lub-dub
            j = i + gecikme
            m = min(k, n - j)
            if m > 0:
                x[j:j + m] += lub[:m] * g
    # alcak ostinato (re - mi bemol - re): yari tonluk tedirginlik
    notalar = np.array([73.4, 77.8, 73.4, 69.3])
    nota = notalar[(np.floor(vurus_faz * 2) % 4).astype(int)]
    ost = np.sin(2 * np.pi * np.cumsum(nota / SR)) * 0.25
    return _norm(x + ost.astype(np.float32), 0.6)


# ------------------------------------------------------------------ miks
def miksle(sure, olaylar, yataklar, cikis_wav, stem_klasoru=None):
    """
    olaylar: [(t, tur, guc)] ; yataklar: [(t0, t1, dizi_np, seviye)]
    Ses dosyasini yazar, kullanilan olay listesini dondurur (kalite kontrol icin).
    """
    n = int(sure * SR) + SR
    efekt = np.zeros(n, dtype=np.float32)
    yatak = np.zeros(n, dtype=np.float32)
    for i, (t, tur, guc) in enumerate(sorted(olaylar)):
        if tur not in EFEKTLER:
            raise ValueError(f"bilinmeyen ses efekti: {tur}")
        s = EFEKTLER[tur](guc, i) * EFEKT_SEVIYE[tur] * guc
        j = int(t * SR)
        m = min(len(s), n - j)
        if m > 0:
            efekt[j:j + m] += s[:m]
    for t0, t1, dizi, seviye in yataklar:
        j0, j1 = int(t0 * SR), min(n, int(t1 * SR))
        m = min(j1 - j0, len(dizi))
        parca = dizi[:m].copy()
        kenar = int(0.25 * SR)   # yataklar arasi yumusak gecis
        if m > 2 * kenar:
            parca[:kenar] *= np.linspace(0, 1, kenar)
            parca[-kenar:] *= np.linspace(1, 0, kenar)
        yatak[j0:j0 + m] += parca * seviye
    # Efekt varken yatak hafifce kisilir (ducking) -> olaylar net duyulur
    zarf = np.abs(efekt)
    pencere = int(0.08 * SR)
    zarf = np.convolve(zarf, np.ones(pencere) / pencere, mode="same")
    yatak *= 1 - 0.45 * np.clip(zarf / (zarf.max() or 1) * 3, 0, 1)
    miks = (efekt + yatak)[: int(sure * SR)]
    # seviye: RMS ~ -16 dBFS, tepe -1 dBFS (yumusak limiter)
    rms = float(np.sqrt(np.mean(miks ** 2))) or 1e-6
    miks *= 10 ** (-16 / 20) / rms
    miks = np.tanh(miks * 1.2) / np.tanh(1.2)
    miks = _norm(miks, 10 ** (-1 / 20))
    stereo = np.stack([miks, miks], axis=1)
    wavfile.write(cikis_wav, SR, (stereo * 32767).astype(np.int16))
    if stem_klasoru:
        wavfile.write(f"{stem_klasoru}/efektler.wav", SR, (_norm(efekt) * 32767).astype(np.int16))
        wavfile.write(f"{stem_klasoru}/muzik.wav", SR, (_norm(yatak) * 32767).astype(np.int16))
    return {"rms_dbfs": round(20 * np.log10(float(np.sqrt(np.mean(miks ** 2))) or 1e-9), 1),
            "tepe_dbfs": round(20 * np.log10(float(np.max(np.abs(miks))) or 1e-9), 1),
            "olay_sayisi": len(olaylar)}
