# -*- coding: utf-8 -*-
"""
Blok karakter cizimi. Iskelet noktalarindan her parca ayri cizilir:
arka kol/bacak -> govde -> on bacak -> kafa (+yuz, sac) -> on kol.
Ayni videoda kontur kalinligi, palet ve oranlar sabittir (stil tutarliligi).
"""
import math
from dataclasses import dataclass, field

import skia

from . import iskelet as isk
from .temel import KONTUR, boya, cokgen, hash01, renk

KONTUR_K = 9


@dataclass
class Palet:
    ten: str = "#f1c27d"
    gomlek: str = "#3b82c4"
    pantolon: str = "#2f3b52"
    ayakkabi: str = "#3a2a1e"
    sac: str = "#4a2f1b"
    sac_tipi: str = "kisa"      # kisa | kasket | kel | uzun
    kasket: str = "#c0392b"


@dataclass
class Karakter:
    ad: str
    palet: Palet = field(default_factory=Palet)
    zombi: bool = False
    olcek: float = 1.0
    tohum: int = 1


def _uzuv(canvas, a, b, kalinlik, renk_hex, kontur=KONTUR_K):
    """Kalin, uclari yuvarlak, konturlu kemik."""
    canvas.drawLine(a[0], a[1], b[0], b[1], boya(KONTUR, kalinlik + kontur * 2))
    canvas.drawLine(a[0], a[1], b[0], b[1], boya(renk_hex, kalinlik))


def _dortgen_eksen(a, b, gen_a, gen_b):
    """a->b ekseni boyunca, uclarda farkli genislikte dortgen (govde)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    return [(a[0] + nx * gen_a / 2, a[1] + ny * gen_a / 2), (b[0] + nx * gen_b / 2, b[1] + ny * gen_b / 2),
            (b[0] - nx * gen_b / 2, b[1] - ny * gen_b / 2), (a[0] - nx * gen_a / 2, a[1] - ny * gen_a / 2)]


def _yuvarlak_kose_yol(noktalar, r):
    yol = skia.Path()
    n = len(noktalar)
    for i in range(n):
        p0, p1, p2 = noktalar[i - 1], noktalar[i], noktalar[(i + 1) % n]
        v1 = (p0[0] - p1[0], p0[1] - p1[1])
        v2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1, l2 = math.hypot(*v1) or 1, math.hypot(*v2) or 1
        a = (p1[0] + v1[0] / l1 * r, p1[1] + v1[1] / l1 * r)
        b = (p1[0] + v2[0] / l2 * r, p1[1] + v2[1] / l2 * r)
        if i == 0:
            yol.moveTo(*a)
        else:
            yol.lineTo(*a)
        yol.quadTo(p1[0], p1[1], b[0], b[1])
    yol.close()
    return yol


def golge(canvas, n, zemin_y, poz):
    o = n["olcek"]
    yuk = max(0.0, poz.get("ziplama", 0.0))
    s = max(0.35, 1 - yuk / 400)
    genis = 190 * o * s * (1 + abs(math.sin(math.radians(poz.get("donme", 0)))) * 1.6)
    canvas.drawOval(skia.Rect(n["kalca"][0] - genis / 2, zemin_y - 16 * o, n["kalca"][0] + genis / 2, zemin_y + 16 * o),
                    boya("#000000", alfa=int(70 * s)))


def _yuz(canvas, k, poz, t, o, yon):
    """Kafa yerel koordinatinda (merkez 0,0; kafa donusu uygulanmis) yuz."""
    p = k.palet
    ifade = "zombi" if k.zombi and poz.get("ifade") in ("normal", "zombi") else poz.get("ifade", "normal")
    gx = poz.get("goz_x", 0.35) * 26 * o * yon
    gy = poz.get("goz_y", 0.0) * 14 * o
    # Goz kirpma: her 2.5-4 sn'de 0.12 sn (karaktere ozel tohum)
    periyot = 2.6 + hash01(k.tohum) * 1.5
    kirp = ((t + hash01(k.tohum, 3) * 3) % periyot) < 0.11 and ifade not in ("sok", "korku", "zombi")
    ex = 34 * o
    ey = -6 * o + gy
    if ifade == "uyku" or kirp:
        for sx in (-1, 1):
            canvas.drawLine(gx + sx * ex - 14 * o, ey, gx + sx * ex + 14 * o, ey, boya(KONTUR, 7 * o))
    elif ifade in ("sok", "korku"):
        for sx in (-1, 1):
            canvas.drawRect(skia.Rect(gx + sx * ex - 19 * o, ey - 22 * o, gx + sx * ex + 19 * o, ey + 22 * o), boya("#ffffff"))
            canvas.drawRect(skia.Rect(gx + sx * ex - 19 * o, ey - 22 * o, gx + sx * ex + 19 * o, ey + 22 * o), boya(KONTUR, 6 * o))
            canvas.drawRect(skia.Rect(gx * 1.25 + sx * ex - 7 * o, ey - 5 * o, gx * 1.25 + sx * ex + 7 * o, ey + 9 * o), boya(KONTUR))
    elif ifade == "zombi":
        for sx in (-1, 1):
            canvas.drawRect(skia.Rect(gx + sx * ex - 18 * o, ey - 14 * o, gx + sx * ex + 18 * o, ey + 14 * o), boya("#f5f5dc"))
            canvas.drawRect(skia.Rect(gx + sx * ex - 18 * o, ey - 14 * o, gx + sx * ex + 18 * o, ey + 14 * o), boya(KONTUR, 5 * o))
            canvas.drawRect(skia.Rect(gx + sx * ex - 5 * o, ey - 4 * o, gx + sx * ex + 5 * o, ey + 6 * o), boya("#c0392b"))
    else:
        for sx in (-1, 1):
            canvas.drawRect(skia.Rect(gx + sx * ex - 9 * o, ey - 16 * o, gx + sx * ex + 9 * o, ey + 16 * o), boya(KONTUR))
            canvas.drawRect(skia.Rect(gx + sx * ex - 3 * o, ey - 12 * o, gx + sx * ex + 3 * o, ey - 5 * o), boya("#ffffff"))

    # Kaslar
    kas_y = ey - 38 * o
    for sx in (-1, 1):
        ic = gx + sx * (ex - 20 * o)
        dis = gx + sx * (ex + 20 * o)
        ic_y = dis_y = kas_y
        if ifade in ("korku", "aci"):
            ic_y -= 12 * o
            dis_y += 4 * o
        elif ifade in ("sinir", "zombi"):
            ic_y += 12 * o
        elif ifade == "sok":
            ic_y -= 16 * o
            dis_y -= 16 * o
        canvas.drawLine(dis, dis_y, ic, ic_y, boya(KONTUR, 8 * o))

    # Agiz: konusma acikligi ifadenin uzerine biner
    ay = 48 * o
    ax = gx * 0.8
    acik = poz.get("agiz", 0.0)
    if ifade == "zombi":
        h = (18 + 22 * acik) * o
        canvas.drawRect(skia.Rect(ax - 30 * o, ay - h / 2, ax + 30 * o, ay + h / 2), boya("#2b0d0d"))
        for i in range(4):
            dx = ax - 24 * o + i * 16 * o
            canvas.drawRect(skia.Rect(dx, ay - h / 2, dx + 8 * o, ay - h / 2 + 8 * o), boya("#f5f5dc"))
        canvas.drawRect(skia.Rect(ax - 30 * o, ay - h / 2, ax + 30 * o, ay + h / 2), boya(KONTUR, 5 * o))
    elif acik > 0.06 or ifade in ("sok", "korku", "aci"):
        a = max(acik, 0.75 if ifade == "sok" else 0.45 if ifade in ("korku", "aci") else 0)
        h = (8 + 34 * a) * o
        w = (34 - 8 * a) * o
        canvas.drawRoundRect(skia.Rect(ax - w / 2, ay - h / 2, ax + w / 2, ay + h / 2), 6 * o, 6 * o, boya("#3a1010"))
        canvas.drawRoundRect(skia.Rect(ax - w / 2, ay - h / 2, ax + w / 2, ay + h / 2), 6 * o, 6 * o, boya(KONTUR, 6 * o))
    elif ifade == "mutlu":
        yol = skia.Path()
        yol.moveTo(ax - 26 * o, ay - 6 * o)
        yol.quadTo(ax, ay + 22 * o, ax + 26 * o, ay - 6 * o)
        canvas.drawPath(yol, boya(KONTUR, 7 * o))
    elif ifade == "sinir":
        canvas.drawLine(ax - 24 * o, ay + 6 * o, ax + 24 * o, ay - 2 * o, boya(KONTUR, 7 * o))
    else:
        canvas.drawLine(ax - 22 * o, ay, ax + 22 * o, ay, boya(KONTUR, 7 * o))


def _kafa(canvas, k, n, poz, t):
    o = n["olcek"]
    yon = n["yon"]
    p = k.palet
    ten = "#8fb87a" if k.zombi else p.ten
    s = isk.KAFA * o
    canvas.save()
    canvas.translate(*n["kafa"])
    canvas.rotate(n["kafa_aci"])
    kare = [(-s / 2, -s / 2), (s / 2, -s / 2), (s / 2, s / 2), (-s / 2, s / 2)]
    yol = _yuvarlak_kose_yol(kare, 16 * o)
    canvas.drawPath(yol, boya(ten))
    # Hafif hacim: alt-arka kosede golge
    canvas.save()
    canvas.clipPath(yol, doAntiAlias=True)
    canvas.drawRect(skia.Rect(-s / 2 if yon < 0 else s * 0.22, -s / 2, -s * 0.22 if yon < 0 else s / 2, s / 2),
                    boya("#000000", alfa=26))
    if k.zombi:
        canvas.drawCircle(-s * 0.18 * yon, s * 0.28, 18 * o, boya("#5f8a52"))
        canvas.drawCircle(s * 0.25 * yon, -s * 0.3, 12 * o, boya("#6e9a60"))
    canvas.restore()
    canvas.drawPath(yol, boya(KONTUR, KONTUR_K * o))

    # Sac / sapka (kafanin ustu + bakis yonunun tersinde arka kisim)
    tip = "zombi" if k.zombi else p.sac_tipi
    if tip in ("kisa", "zombi"):
        sac_renk = "#3d3d2e" if k.zombi else p.sac
        ust = [(-s / 2 - 4 * o, -s / 2 - 10 * o), (s / 2 + 4 * o, -s / 2 - 10 * o), (s / 2 + 4 * o, -s * 0.24),
               (-s / 2 - 4 * o, -s * 0.24)]
        arka_x = -s / 2 - 4 * o if yon > 0 else s / 2 + 4 * o
        arka = [(arka_x, -s * 0.3), (arka_x + yon * s * 0.24, -s * 0.3), (arka_x + yon * s * 0.24, s * 0.05), (arka_x, s * 0.05)]
        if k.zombi:   # seyrek, daginik sac
            ust = [(-s / 2, -s / 2 - 6 * o), (-s * 0.1, -s / 2 - 14 * o), (s * 0.15, -s / 2 - 4 * o), (s / 2, -s / 2 - 12 * o),
                   (s / 2, -s * 0.34), (-s / 2, -s * 0.34)]
        for parca in (ust, arka):
            y = _yuvarlak_kose_yol(parca, 8 * o)
            canvas.drawPath(y, boya(sac_renk))
            canvas.drawPath(y, boya(KONTUR, 7 * o))
    elif tip == "kasket":
        govde = [(-s / 2 - 6 * o, -s / 2 - 34 * o), (s / 2 + 6 * o, -s / 2 - 34 * o), (s / 2 + 6 * o, -s * 0.22),
                 (-s / 2 - 6 * o, -s * 0.22)]
        siper_x0 = s * 0.2 * yon
        siper = [(siper_x0, -s * 0.3), (siper_x0 + yon * s * 0.62, -s * 0.27), (siper_x0 + yon * s * 0.62, -s * 0.18),
                 (siper_x0, -s * 0.2)]
        for parca in (govde, siper):
            y = _yuvarlak_kose_yol(parca, 8 * o)
            canvas.drawPath(y, boya(p.kasket))
            canvas.drawPath(y, boya(KONTUR, 7 * o))
    _yuz(canvas, k, poz, t, o, yon)
    canvas.restore()


def ciz(canvas, k, n, poz, t):
    """Karakteri iskelet noktalarina gore cizer."""
    o = n["olcek"]
    p = k.palet
    gomlek = "#5b6b4a" if k.zombi else p.gomlek
    pantolon = "#3b3f35" if k.zombi else p.pantolon
    ten = "#8fb87a" if k.zombi else p.ten
    kol_k, bacak_k = 44 * o, 50 * o

    # Arka uzuvlar biraz koyu: derinlik hissi
    def koyu(h, f=0.78):
        h = h.lstrip("#")
        return "#" + "".join(f"{int(int(h[i:i + 2], 16) * f):02x}" for i in (0, 2, 4))

    # arka bacak + arka kol
    _uzuv(canvas, n["kalca"], n["diz_arka"], bacak_k, koyu(pantolon))
    _uzuv(canvas, n["diz_arka"], n["bilek_arka"], bacak_k, koyu(pantolon))
    _uzuv(canvas, n["bilek_arka"], n["parmak_arka"], bacak_k * 0.8, koyu(p.ayakkabi))
    _uzuv(canvas, n["omuz"], n["dirsek_arka"], kol_k, koyu(gomlek))
    _uzuv(canvas, n["dirsek_arka"], n["el_arka"], kol_k * 0.92, koyu(ten if k.zombi else gomlek))
    canvas.drawCircle(*n["el_arka"], 24 * o, boya(KONTUR))
    canvas.drawCircle(*n["el_arka"], 17 * o, boya(koyu(ten)))

    # on bacak (govdenin arkasinda kalan kalca bolgesi govdeyle ortulur)
    _uzuv(canvas, n["kalca"], n["diz_on"], bacak_k, pantolon)
    _uzuv(canvas, n["diz_on"], n["bilek_on"], bacak_k, pantolon)
    _uzuv(canvas, n["bilek_on"], n["parmak_on"], bacak_k * 0.8, p.ayakkabi)

    # govde: kalcadan boyuna blok, omuzda biraz genis
    kalca_alt = (n["kalca"][0] - (n["boyun"][0] - n["kalca"][0]) * 0.12,
                 n["kalca"][1] - (n["boyun"][1] - n["kalca"][1]) * 0.12)
    dort = _dortgen_eksen(kalca_alt, n["boyun"], 132 * o, 150 * o)
    yol = _yuvarlak_kose_yol(dort, 18 * o)
    canvas.drawPath(yol, boya(gomlek))
    canvas.save()
    canvas.clipPath(yol, doAntiAlias=True)
    # kemer
    kb = _dortgen_eksen(kalca_alt, (lambda a, b: (a[0] + (b[0] - a[0]) * 0.16, a[1] + (b[1] - a[1]) * 0.16))(kalca_alt, n["boyun"]), 200 * o, 200 * o)
    canvas.drawPath(cokgen(kb), boya(pantolon))
    if k.zombi:   # yirtik gomlek lekeleri
        for i in range(3):
            cx = n["kalca"][0] + (hash01(k.tohum, i) - 0.5) * 90 * o
            cy = n["kalca"][1] - (60 + 90 * hash01(i, k.tohum)) * o
            canvas.drawCircle(cx, cy, (10 + 8 * hash01(i)) * o, boya("#7a2a22", alfa=200))
    canvas.restore()
    canvas.drawPath(yol, boya(KONTUR, KONTUR_K * o))

    _kafa(canvas, k, n, poz, t)

    # on kol en ustte
    _uzuv(canvas, n["omuz"], n["dirsek_on"], kol_k, gomlek)
    _uzuv(canvas, n["dirsek_on"], n["el_on"], kol_k * 0.92, ten if k.zombi else gomlek)
    canvas.drawCircle(*n["el_on"], 24 * o, boya(KONTUR))
    canvas.drawCircle(*n["el_on"], 17 * o, boya(ten))


def sinir_kutusu(n):
    """Ekran disi kontrolu icin kaba sinir kutusu (kafa dahil)."""
    o = n["olcek"]
    xs = [v[0] for k, v in n.items() if isinstance(v, tuple)]
    ys = [v[1] for k, v in n.items() if isinstance(v, tuple)]
    yar = isk.KAFA * o * 0.75
    return (min(xs + [n["kafa"][0] - yar]), min(ys + [n["kafa"][1] - yar]),
            max(xs + [n["kafa"][0] + yar]), max(ys + [n["kafa"][1] + yar]))
