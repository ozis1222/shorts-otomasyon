# -*- coding: utf-8 -*-
"""Ortak yardimcilar: yumusatma (easing), deterministik gurultu, renk, cizim kisayollari."""
import math
import os

import skia

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_YOLU = os.path.join(KOK, "fonts", "Anton-Regular.ttf")

W, H = 1080, 1920
KONTUR = (20, 20, 20)


def kis(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def yumusak(t):
    """smoothstep: hiz 0'dan baslar 0'da biter -> sicramasiz gecis."""
    t = kis(t)
    return t * t * (3 - 2 * t)


def ease_in(t):
    t = kis(t)
    return t * t


def ease_out(t):
    t = kis(t)
    return 1 - (1 - t) * (1 - t)


def ease_in_out(t):
    t = kis(t)
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def trapez(u, rampa=0.18):
    """Hiz profili: rampa boyunca hizlan, sabit git, rampa boyunca yavasla. Konum (0..1) dondurur."""
    u = kis(u)
    r = kis(rampa, 0.001, 0.5)
    vmax = 1.0 / (1.0 - r)
    if u < r:
        return 0.5 * vmax * u * u / r
    if u > 1 - r:
        k = 1 - u
        return 1 - 0.5 * vmax * k * k / r
    return 0.5 * vmax * r + vmax * (u - r)


def gurultu(t, tohum=0):
    """Puruzsuz, deterministik 1B gurultu (-1..1): farkli frekansli sinuslerin toplami."""
    s = 0.0
    for i, f in enumerate((1.0, 2.13, 4.37, 7.91)):
        faz = math.sin((tohum + 1) * 12.9898 * (i + 1)) * 43758.5453
        faz -= math.floor(faz)
        s += math.sin(t * f * 2 * math.pi + faz * 2 * math.pi) / (i + 1)
    return s / 2.08


def hash01(*args):
    """Argumanlardan 0..1 arasi tekrar uretilebilir sayi."""
    x = math.sin(sum((i + 1) * 78.233 * float(a) for i, a in enumerate(args)) + 12.9898) * 43758.5453
    return x - math.floor(x)


def renk(r, g=None, b=None, a=255):
    if isinstance(r, str):
        h = r.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    elif isinstance(r, tuple):
        r, g, b = r[:3]
    return skia.Color(int(r), int(g), int(b), int(kis(a, 0, 255)))


def karistir(c1, c2, t):
    """Iki '#rrggbb' rengini karistirir -> (r,g,b)."""
    a = [int(c1.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(c2.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return tuple(int(lerp(x, y, t)) for x, y in zip(a, b))


def boya(c, kalinlik=None, alfa=255, yuvarlak=True):
    """Dolgu (kalinlik=None) veya cizgi boyasi."""
    p = skia.Paint(AntiAlias=True, Color=renk(c, a=alfa) if not isinstance(c, int) else c)
    if kalinlik is not None:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(kalinlik)
        if yuvarlak:
            p.setStrokeCap(skia.Paint.kRound_Cap)
            p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def cokgen(noktalar):
    p = skia.Path()
    p.moveTo(*noktalar[0])
    for n in noktalar[1:]:
        p.lineTo(*n)
    p.close()
    return p


def konturlu(canvas, yol, dolgu, kalinlik=8, kontur=KONTUR):
    canvas.drawPath(yol, boya(dolgu))
    canvas.drawPath(yol, boya(kontur, kalinlik))


_FONT_CACHE = {}


def font(boyut):
    if boyut not in _FONT_CACHE:
        tf = skia.Typeface.MakeFromFile(FONT_YOLU) if os.path.exists(FONT_YOLU) else skia.Typeface()
        _FONT_CACHE[boyut] = skia.Font(tf, boyut)
    return _FONT_CACHE[boyut]
