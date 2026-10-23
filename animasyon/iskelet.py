# -*- coding: utf-8 -*-
"""
Eklem tabanli iskelet + ileri kinematik.

Poz = eklem acilari sozlugu (derece). Her uzuv ayri bir kemiktir:
  govde (kalca->boyun), kafa, ust kol / alt kol (on ve arka), ust bacak / alt bacak, ayak.
Aci kurali: 0 = kemik asagi bakar, + = karakterin baktigi yone (ileri) doner.
  govde: 0 = dik; + = one egilir.   *_alt: ust kemige gore ek bukulme (dirsek/diz).
Kalca yuksekligi elle verilmez: en alttaki nokta otomatik olarak zemine oturtulur
(yururken dogal inip kalkma, yere yatinca dogru temas). 'ziplama' bunun ustune eklenir.
"""
import math

from .temel import lerp

# Blok karakter kemik uzunluklari (px, olcek 1)
GOVDE = 200
OMUZ = 28        # omuz, boyundan bu kadar asagida
KAFA = 172       # kare kafa kenari
BOYUN = 6
KOL_UST = 104
KOL_ALT = 100
BACAK_UST = 128
BACAK_ALT = 124
AYAK = 52

ACILAR = ("govde", "kafa",
          "kol_on_ust", "kol_on_alt", "kol_arka_ust", "kol_arka_alt",
          "bacak_on_ust", "bacak_on_alt", "bacak_arka_ust", "bacak_arka_alt",
          "ayak_on", "ayak_arka", "donme")
SAYISAL = ACILAR + ("ziplama", "agiz", "goz_x", "goz_y", "titreme")

BAZ = {
    "govde": 0.0, "kafa": 0.0,
    "kol_on_ust": 8.0, "kol_on_alt": 12.0, "kol_arka_ust": -8.0, "kol_arka_alt": 12.0,
    "bacak_on_ust": 3.0, "bacak_on_alt": 0.0, "bacak_arka_ust": -3.0, "bacak_arka_alt": 0.0,
    "ayak_on": 0.0, "ayak_arka": 0.0, "donme": 0.0,
    "ziplama": 0.0, "agiz": 0.0, "goz_x": 0.35, "goz_y": 0.0, "titreme": 0.0,
    "ifade": "normal",
}


def yeni_poz(**degisen):
    p = dict(BAZ)
    p.update(degisen)
    return p


def poz_karistir(a, b, t):
    """Iki pozu eklem eklem karistirir (gecislerde uzuvlar sicramaz)."""
    p = {k: lerp(a.get(k, BAZ[k]), b.get(k, BAZ[k]), t) for k in SAYISAL}
    p["ifade"] = b.get("ifade", "normal") if t >= 0.5 else a.get("ifade", "normal")
    for k in b:
        if k not in p:
            p[k] = b[k] if t >= 0.5 else a.get(k, b[k])
    return p


def _asagi(aci):
    r = math.radians(aci)
    return math.sin(r), math.cos(r)


def _ekle(p, uzunluk, aci):
    dx, dy = _asagi(aci)
    return (p[0] + dx * uzunluk, p[1] + dy * uzunluk)


def kinematik(poz, x, zemin_y, yon=1, olcek=1.0):
    """
    Pozdan tum eklem noktalarini (ekran/dunya koordinati) hesaplar.
    Donus: {'kalca','boyun','omuz','kafa','kafa_aci', 'dirsek_on','el_on', ..., 'diz_on','bilek_on','parmak_on', ...}
    """
    g = poz["govde"]
    kalca = (0.0, 0.0)
    yukari = (math.sin(math.radians(g)), -math.cos(math.radians(g)))
    boyun = (yukari[0] * GOVDE, yukari[1] * GOVDE)
    omuz = (yukari[0] * (GOVDE - OMUZ), yukari[1] * (GOVDE - OMUZ))
    kafa_aci = g + poz["kafa"]
    ku = (math.sin(math.radians(kafa_aci)), -math.cos(math.radians(kafa_aci)))
    kafa = (boyun[0] + ku[0] * (BOYUN + KAFA / 2), boyun[1] + ku[1] * (BOYUN + KAFA / 2))

    n = {"kalca": kalca, "boyun": boyun, "omuz": omuz, "kafa": kafa}
    for taraf in ("on", "arka"):
        a1 = g + poz[f"kol_{taraf}_ust"]
        dirsek = _ekle(omuz, KOL_UST, a1)
        el = _ekle(dirsek, KOL_ALT, a1 + poz[f"kol_{taraf}_alt"])
        b1 = poz[f"bacak_{taraf}_ust"]
        diz = _ekle(kalca, BACAK_UST, b1)
        b2 = b1 + poz[f"bacak_{taraf}_alt"]
        bilek = _ekle(diz, BACAK_ALT, b2)
        parmak = _ekle(bilek, AYAK, b2 + 90 + poz[f"ayak_{taraf}"])
        n.update({f"dirsek_{taraf}": dirsek, f"el_{taraf}": el, f"diz_{taraf}": diz,
                  f"bilek_{taraf}": bilek, f"parmak_{taraf}": parmak})

    # Tum vucut donusu (dusme, yere yatma) kalca etrafinda
    d = poz["donme"]
    if abs(d) > 1e-6:
        c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
        n = {k: (v[0] * c - v[1] * s, v[0] * s + v[1] * c) for k, v in n.items()}
        kafa_aci += d

    # Zemine oturt: en alttaki temas noktasi zemin cizgisine gelir
    kafa_alt = n["kafa"][1] + KAFA * 0.62
    taban = max([n[k][1] for k in ("bilek_on", "bilek_arka", "parmak_on", "parmak_arka",
                                     "el_on", "el_arka", "boyun")] + [kafa_alt])
    dy = zemin_y / olcek - taban - poz["ziplama"]
    cikis = {}
    for k, v in n.items():
        cikis[k] = (x + yon * v[0] * olcek, (v[1] + dy) * olcek)
    cikis["kafa_aci"] = kafa_aci * yon
    cikis["yon"] = yon
    cikis["olcek"] = olcek
    return cikis


KEMIKLER = [("kalca", "boyun", GOVDE), ("omuz", "dirsek_on", KOL_UST), ("dirsek_on", "el_on", KOL_ALT),
            ("omuz", "dirsek_arka", KOL_UST), ("dirsek_arka", "el_arka", KOL_ALT),
            ("kalca", "diz_on", BACAK_UST), ("diz_on", "bilek_on", BACAK_ALT),
            ("kalca", "diz_arka", BACAK_UST), ("diz_arka", "bilek_arka", BACAK_ALT),
            ("bilek_on", "parmak_on", AYAK), ("bilek_arka", "parmak_arka", AYAK)]


def kemik_hatasi(n):
    """Kalite kontrol: kemik uzunluklarinin tanimdan en buyuk sapmasi (px). Kopuk uzuv = buyuk hata."""
    o = n["olcek"]
    en = 0.0
    for a, b, L in KEMIKLER:
        d = math.dist(n[a], n[b])
        en = max(en, abs(d - L * o))
    return en
