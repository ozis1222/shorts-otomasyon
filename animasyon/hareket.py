# -*- coding: utf-8 -*-
"""
Hareket kutuphanesi + zaman cizelgesi (iz).

Her hareket bir fonksiyondur: (tau, faz, param) -> poz
  tau  : hareketin basindan beri gecen sure (sn)
  faz  : yurume dongusu; ZAMANDAN degil KAT EDILEN MESAFEDEN hesaplanir
         -> ayak kaymaz, FPS ne olursa olsun ayni gorunur.
Iz (Iz sinifi) aksiyonlari zamana yerlestirir; aksiyonlar arasinda BLEND suresi boyunca
eski ve yeni poz eklem eklem karistirilir -> uzuvlar asla sicramaz.
"""
import math

from .iskelet import poz_karistir, yeni_poz
from .temel import ease_in, ease_in_out, ease_out, gurultu, kis, lerp, trapez, yumusak

BLEND = 0.22   # aksiyon gecis suresi (sn)


def _sin(f):
    return math.sin(2 * math.pi * f)


def _cos(f):
    return math.cos(2 * math.pi * f)


# ---------------------------------------------------------------- temel hareketler
def bekle(tau, faz, p):
    nefes = math.sin(tau * 2.1)
    return yeni_poz(govde=1.5 * nefes, kafa=-1.0 * nefes,
                    kol_on_ust=8 + 2.5 * nefes, kol_arka_ust=-8 - 2.5 * nefes,
                    ifade=p.get("ifade", "normal"))


def etrafa_bak(tau, faz, p):
    q = bekle(tau, faz, p)
    bak = math.sin(tau * 1.6)
    q.update(goz_x=0.9 * bak, kafa=6 * bak, ifade=p.get("ifade", "dusunce"))
    return q


def konus(tau, faz, p):
    q = bekle(tau, faz, p)
    hece = abs(math.sin(tau * 11.0)) * (0.5 + 0.5 * abs(math.sin(tau * 2.7)))
    jest = math.sin(tau * 3.2)
    q.update(agiz=0.15 + 0.85 * hece, kol_on_ust=38 + 14 * jest, kol_on_alt=65 - 10 * jest,
             kafa=3 * math.sin(tau * 4), ifade=p.get("ifade", "normal"))
    return q


def isaret(tau, faz, p):
    q = konus(tau, faz, p) if p.get("konus") else bekle(tau, faz, p)
    q.update(kol_on_ust=95 + 4 * math.sin(tau * 5), kol_on_alt=-4, ifade=p.get("ifade", q["ifade"]))
    return q


def yuru(tau, faz, p):
    s, c = _sin(faz), _cos(faz)
    gen = p.get("adim_aci", 26)
    return yeni_poz(
        govde=4 + 1.5 * _sin(2 * faz),
        kafa=-2,
        bacak_on_ust=gen * s, bacak_arka_ust=-gen * s,
        # salinimdaki (one giden) bacak dizden bukulur
        bacak_on_alt=-42 * max(0.0, c), bacak_arka_alt=-42 * max(0.0, -c),
        ayak_on=-8 * max(0.0, c), ayak_arka=-8 * max(0.0, -c),
        kol_on_ust=-22 * s, kol_arka_ust=22 * s, kol_on_alt=18 + 8 * max(0.0, -s), kol_arka_alt=18 + 8 * max(0.0, s),
        ifade=p.get("ifade", "normal"), goz_x=0.6)


def kos(tau, faz, p):
    s, c = _sin(faz), _cos(faz)
    return yeni_poz(
        govde=15 + 2 * _sin(2 * faz),
        kafa=-8,
        bacak_on_ust=48 * s, bacak_arka_ust=-48 * s,
        bacak_on_alt=-95 * max(0.0, c) - 15, bacak_arka_alt=-95 * max(0.0, -c) - 15,
        ayak_on=-15 * max(0.0, c), ayak_arka=-15 * max(0.0, -c),
        kol_on_ust=-50 * s, kol_arka_ust=50 * s, kol_on_alt=85, kol_arka_alt=85,
        ziplama=18 * abs(_sin(2 * faz)),
        agiz=p.get("agiz", 0.0),
        ifade=p.get("ifade", "korku"), goz_x=0.8)


def kork(tau, faz, p):
    tit = gurultu(tau * 9, 3) * 2.5
    return yeni_poz(
        govde=-9 + tit, kafa=-6 + tit,
        kol_on_ust=125, kol_on_alt=75, kol_arka_ust=115, kol_arka_alt=85,
        bacak_on_ust=12, bacak_on_alt=-20, bacak_arka_ust=-6, bacak_arka_alt=-14,
        titreme=1.0, ifade="korku", goz_x=p.get("goz_x", 0.9),
        agiz=0.4 + 0.2 * abs(math.sin(tau * 13)))


def geri_cekil(tau, faz, p):
    """Geriye yuru (faz azalir) + korkmus ust govde."""
    q = yuru(tau, faz, p)
    k = kork(tau, faz, p)
    for a in ("govde", "kafa", "kol_on_ust", "kol_on_alt", "kol_arka_ust", "kol_arka_alt", "agiz", "titreme"):
        q[a] = k[a]
    q["govde"] = -12 + gurultu(tau * 7) * 2
    q["ifade"] = "korku"
    q["goz_x"] = 0.9
    return q


def zipla(tau, faz, p):
    """Comel -> havalan (yercekimi parabolu) -> yere in (sonum). Toplam ~0.85 sn."""
    h = p.get("yukseklik", 170)
    if tau < 0.16:          # comelme
        u = ease_out(tau / 0.16)
        return yeni_poz(govde=10 * u, bacak_on_ust=35 * u, bacak_on_alt=-70 * u, bacak_arka_ust=25 * u,
                        bacak_arka_alt=-60 * u, kol_on_ust=-30 * u, kol_arka_ust=-35 * u,
                        ifade=p.get("ifade", "sok"))
    if tau < 0.66:          # havada: y = 4h u(1-u)
        u = (tau - 0.16) / 0.5
        return yeni_poz(govde=-4, ziplama=4 * h * u * (1 - u), bacak_on_ust=30, bacak_on_alt=-60,
                        bacak_arka_ust=-10, bacak_arka_alt=-50, kol_on_ust=150, kol_on_alt=20,
                        kol_arka_ust=140, kol_arka_alt=20, ifade=p.get("ifade", "sok"))
    u = kis((tau - 0.66) / 0.2)   # inis: dizler yayi emer
    b = math.sin(u * math.pi)
    return yeni_poz(govde=8 * b, bacak_on_ust=28 * b, bacak_on_alt=-55 * b, bacak_arka_ust=20 * b,
                    bacak_arka_alt=-45 * b, kol_on_ust=lerp(150, 40, u), kol_arka_ust=lerp(140, 30, u),
                    ifade=p.get("ifade", "sok"))


def dus(tau, faz, p):
    """One dogru dusus: donme yercekimiyle hizlanir, yere carpinca kucuk sekme."""
    T = p.get("sure", 0.5)
    if tau < T:
        u = ease_in(tau / T)
        d = 92 * u
        kol = lerp(20, 150, ease_out(tau / T))
    else:
        k = tau - T
        d = 92 - 7 * math.exp(-k * 9) * abs(math.sin(k * 22))
        kol = 150 - 40 * kis(k / 0.3)
    return yeni_poz(donme=d, govde=6, kafa=-10, kol_on_ust=kol, kol_on_alt=20, kol_arka_ust=kol - 20, kol_arka_alt=30,
                    bacak_on_ust=-10, bacak_arka_ust=10, bacak_on_alt=-20, ifade="aci",
                    agiz=0.5 if tau < T + 0.3 else 0.2)


def kalk(tau, faz, p):
    """Yerden kalkma: once dizler, sonra govde dikilir."""
    T = p.get("sure", 0.8)
    u = kis(tau / T)
    d = 92 * (1 - ease_in_out(u))
    diz = math.sin(u * math.pi)
    return yeni_poz(donme=d, govde=20 * diz, bacak_on_ust=50 * diz, bacak_on_alt=-90 * diz,
                    bacak_arka_ust=-10 * diz, bacak_arka_alt=-40 * diz,
                    kol_on_ust=lerp(110, 10, u), kol_on_alt=40, kol_arka_ust=lerp(90, -10, u),
                    ifade=p.get("ifade", "aci"))


def yumruk(tau, faz, p):
    if tau < 0.14:
        u = ease_out(tau / 0.14)
        return yeni_poz(govde=-6 * u, kol_on_ust=lerp(10, -35, u), kol_on_alt=lerp(10, 110, u),
                        kol_arka_ust=60, kol_arka_alt=100, bacak_on_ust=15, bacak_arka_ust=-15, ifade="sinir")
    if tau < 0.24:
        u = ease_out((tau - 0.14) / 0.1)
        return yeni_poz(govde=lerp(-6, 14, u), kol_on_ust=lerp(-35, 92, u), kol_on_alt=lerp(110, 0, u),
                        kol_arka_ust=60, kol_arka_alt=100, bacak_on_ust=22, bacak_arka_ust=-20, ifade="sinir")
    u = yumusak((tau - 0.24) / 0.3)
    return yeni_poz(govde=lerp(14, 2, u), kol_on_ust=lerp(92, 30, u), kol_on_alt=lerp(0, 70, u),
                    kol_arka_ust=60, kol_arka_alt=100, bacak_on_ust=15, bacak_arka_ust=-15, ifade="sinir")


def savun(tau, faz, p):
    tit = gurultu(tau * 5) * 2
    return yeni_poz(govde=-5 + tit, kafa=-8, kol_on_ust=110, kol_on_alt=95, kol_arka_ust=100, kol_arka_alt=105,
                    bacak_on_ust=18, bacak_on_alt=-25, bacak_arka_ust=-12, ifade="korku", goz_x=0.6)


def tasi(tau, faz, p):
    q = yuru(tau, faz, p) if p.get("yuruyerek") else bekle(tau, faz, p)
    q.update(kol_on_ust=62, kol_on_alt=38, kol_arka_ust=58, kol_arka_alt=42, govde=q["govde"] - 4)
    return q


def kapi_ac(tau, faz, p):
    """Kola uzan (0-0.35 sn), tut ve cek (0.35-0.9 sn): kol ve govde koordineli."""
    if tau < 0.35:
        u = ease_in_out(tau / 0.35)
        return yeni_poz(govde=6 * u, kol_on_ust=lerp(8, 82, u), kol_on_alt=lerp(12, -6, u),
                        bacak_on_ust=8 * u, bacak_arka_ust=-6 * u, ifade=p.get("ifade", "dusunce"), goz_x=0.8)
    u = ease_in_out(kis((tau - 0.35) / 0.55))
    return yeni_poz(govde=lerp(6, -4, u), kol_on_ust=lerp(82, 62, u), kol_on_alt=lerp(-6, 30, u),
                    bacak_on_ust=lerp(8, 2, u), bacak_arka_ust=lerp(-6, -10, u),
                    ifade=p.get("ifade", "dusunce"), goz_x=0.8)


def zombi_yuru(tau, faz, p):
    """Sendeleyen yuruyus: aksak adim, kollar onde, govde one egik, kafa sallanir."""
    s, c = _sin(faz), _cos(faz)
    aksak = 0.55 + 0.45 * max(0.0, s)
    return yeni_poz(
        govde=13 + 4 * _sin(2 * faz) + 2 * gurultu(tau * 0.8, 9),
        kafa=16 + 9 * math.sin(tau * 2.3),
        bacak_on_ust=20 * s * aksak, bacak_arka_ust=-14 * s,
        bacak_on_alt=-30 * max(0.0, c), bacak_arka_alt=-12 * max(0.0, -c) - 6,
        ayak_arka=12,
        kol_on_ust=84 + 5 * math.sin(tau * 3.1), kol_on_alt=6 + 6 * math.sin(tau * 2.2),
        kol_arka_ust=76 + 6 * math.sin(tau * 2.7 + 1), kol_arka_alt=12,
        agiz=0.5 + 0.4 * abs(math.sin(tau * 1.7)),
        ifade="zombi", goz_x=0.5)


def olu_taklidi(tau, faz, p):
    return yeni_poz(donme=-92, kol_on_ust=10, kol_arka_ust=-6, bacak_on_ust=4, ifade="uyku",
                    govde=0.6 * math.sin(tau * 1.3))


HAREKETLER = {
    "bekle": bekle, "etrafa_bak": etrafa_bak, "konus": konus, "isaret": isaret,
    "yuru": yuru, "kos": kos, "kork": kork, "geri_cekil": geri_cekil, "zipla": zipla,
    "dus": dus, "kalk": kalk, "yumruk": yumruk, "savun": savun, "tasi": tasi,
    "kapi_ac": kapi_ac, "zombi_yuru": zombi_yuru, "olu_taklidi": olu_taklidi,
}

# Adim uzunlugu (px): faz = mesafe / adim. Ayak kaymamasi icin hareket bazinda.
ADIM = {"yuru": 300, "geri_cekil": 230, "kos": 560, "zombi_yuru": 210, "tasi": 260}
ADIM_ATAN = {"yuru", "geri_cekil", "kos", "zombi_yuru", "tasi"}


class Iz:
    """Bir karakterin zaman cizelgesi. aksiyonlar: [{t0,t1,hareket,x0?,x1?,yon?,param?}]"""

    def __init__(self, aksiyonlar, x_bas=0.0, yon_bas=1, onceki_poz=None):
        self.a = sorted(aksiyonlar, key=lambda a: a["t0"])
        x, yon = x_bas, yon_bas
        for a in self.a:
            if a["hareket"] not in HAREKETLER:
                raise ValueError(f"bilinmeyen hareket: {a['hareket']}")
            a["_x0"] = a.get("x0", x)
            a["_x1"] = a.get("x1", a["_x0"])
            if "yon" in a:
                yon = a["yon"]
            elif abs(a["_x1"] - a["_x0"]) > 1:
                yon = 1 if a["_x1"] > a["_x0"] else -1
                if a["hareket"] == "geri_cekil":
                    yon = -yon
            a["_yon"] = yon
            x = a["_x1"]
        self.onceki_poz = onceki_poz

    def _x(self, a, t):
        sure = max(1e-6, a["t1"] - a["t0"])
        u = (t - a["t0"]) / sure
        egri = trapez(u, a.get("rampa", 0.12)) if a["hareket"] in ADIM else ease_in_out(u)
        return lerp(a["_x0"], a["_x1"], egri)

    def _poz(self, a, t):
        tau = max(0.0, t - a["t0"])
        x = self._x(a, min(t, a["t1"]))
        mesafe = abs(x - a["_x0"])
        faz = mesafe / ADIM.get(a["hareket"], 300)
        if a["hareket"] == "geri_cekil":
            faz = -faz
        p = HAREKETLER[a["hareket"]](tau, faz, a.get("param", {}))
        if "ifade" in a:
            p["ifade"] = a["ifade"]
        return p, x, faz

    def durum(self, t):
        """t anindaki (poz, x, yon, adim_sayaci) — adim_sayaci ses efekti icin."""
        if not self.a:
            from .iskelet import yeni_poz as yp
            return yp(), 0.0, 1, 0
        aktif_i = 0
        for i, a in enumerate(self.a):
            if t >= a["t0"]:
                aktif_i = i
        a = self.a[aktif_i]
        poz, x, faz = self._poz(a, t)
        # Gecis: onceki aksiyonun (devam eden) pozundan yenisine yumusak karisim
        gecen = t - a["t0"]
        if gecen < BLEND:
            if aktif_i > 0:
                onceki, _, _ = self._poz(self.a[aktif_i - 1], t)
            else:
                onceki = self.onceki_poz
            if onceki is not None:
                poz = poz_karistir(onceki, poz, yumusak(gecen / BLEND))
        adim = int(math.floor(abs(faz) * 2)) if a["hareket"] in ADIM_ATAN and t <= a["t1"] else -1
        return poz, x, a["_yon"], (aktif_i, adim)
