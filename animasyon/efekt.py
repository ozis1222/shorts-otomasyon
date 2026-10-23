# -*- coding: utf-8 -*-
"""Ekran uzayi efektleri: toz/kul parcaciklari, vinyet, renk ortusu, konusma balonu, gecisler."""
import math

import skia

from .temel import H, KONTUR, W, boya, font, hash01, kis, renk


def parcaciklar(c, t, adet=40, renk_hex="#ffe9c4", yukari=False, alfa=110, tohum=0):
    """Deterministik suzulen parcaciklar (toz veya kul)."""
    for i in range(adet):
        hiz = 20 + 50 * hash01(i, tohum, 1)
        x = (hash01(i, tohum, 2) * W + math.sin(t * 0.7 + i) * 40) % W
        y0 = hash01(i, tohum, 3) * H
        y = (y0 - t * hiz) % H if yukari else (y0 + t * hiz) % H
        r = 2 + 4 * hash01(i, tohum, 4)
        a = alfa * (0.5 + 0.5 * math.sin(t * 2 + i))
        c.drawCircle(x, y, r, boya(renk_hex, alfa=int(a)))


def vinyet(c, guc=0.75):
    gr = skia.GradientShader.MakeRadial(skia.Point(W / 2, H * 0.48), H * 0.62,
                                        [renk("#000000", a=0), renk("#000000", a=0), renk("#000000", a=int(255 * guc))],
                                        [0, 0.55, 1])
    c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=gr))


def renk_ortu(c, hex_renk, alfa):
    c.drawRect(skia.Rect(0, 0, W, H), boya(hex_renk, alfa=int(alfa)))


def kararma(c, guc):
    if guc > 0:
        c.drawRect(skia.Rect(0, 0, W, H), boya("#000000", alfa=int(255 * kis(guc))))


def flas(c, guc, hex_renk="#ffffff"):
    if guc > 0:
        c.drawRect(skia.Rect(0, 0, W, H), boya(hex_renk, alfa=int(255 * kis(guc))))


def konusma_balonu(c, x, y, metin, ilerleme=1.0, boyut=64, sol_kuyruk=True):
    """Ekran koordinatinda balon. ilerleme 0..1: balon 'pop' eder (olcek), metin harf harf belirir."""
    f = font(boyut)
    gorunen = metin[: max(1, int(len(metin) * kis(ilerleme * 1.6)))]
    gen = f.measureText(metin) + 70
    yuk = boyut * 1.45
    olcek = 0.6 + 0.4 * kis(ilerleme * 4) + 0.08 * math.sin(kis(ilerleme * 4) * math.pi)
    x = kis(x, gen / 2 + 30, W - gen / 2 - 30)
    c.save()
    c.translate(x, y)
    c.scale(olcek, olcek)
    kutu = skia.Rect(-gen / 2, -yuk, gen / 2, 0)
    kuyruk_x = -gen * 0.18 if sol_kuyruk else gen * 0.18
    yol = skia.Path()
    yol.addRoundRect(kutu, 36, 36)
    k = skia.Path()
    k.moveTo(kuyruk_x - 26, -4)
    k.lineTo(kuyruk_x + 4, 54)
    k.lineTo(kuyruk_x + 30, -4)
    k.close()
    birlesik = skia.Op(yol, k, skia.PathOp.kUnion_PathOp) or yol
    c.drawPath(birlesik, boya("#fffdf4"))
    c.drawPath(birlesik, boya(KONTUR, 8))
    c.drawString(gorunen, -gen / 2 + 35, -yuk * 0.3, f, boya(KONTUR))
    c.restore()


def baslik(c, metin, y, boyut=120, alfa=255, renk_hex="#ffffff"):
    f = font(boyut)
    gen = f.measureText(metin)
    p_kontur = boya(KONTUR, 16, alfa=alfa)
    c.drawString(metin, (W - gen) / 2, y, f, p_kontur)
    c.drawString(metin, (W - gen) / 2, y, f, boya(renk_hex, alfa=alfa))
