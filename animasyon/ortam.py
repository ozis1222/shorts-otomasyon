# -*- coding: utf-8 -*-
"""
Kodla cizilen ortamlar. Her ortam katmanlardan olusur; katmanin parallax katsayisi p:
  p<1 uzak (kameradan yavas kayar), p=1 karakter duzlemi, p>1 on plan (hizli kayar).
Z sirasi: ortam.katmanlar() -> [(z, p, cizim_fonk)], karakterler kendi z degerleriyle araya girer.
"""
import math

import skia

from .temel import KONTUR, boya, cokgen, ease_in_out, gurultu, hash01, kis, renk


class Kapi:
    """Mentese etrafinda donen kapi. acilma: [(t0, t1, aci_bas, aci_son)] (derece, 0=kapali, 80=acik)."""

    def __init__(self, x, zemin_y, gen=290, yuk=700, acilma=()):
        self.x, self.zemin, self.gen, self.yuk = x, zemin_y, gen, yuk
        self.acilma = list(acilma)

    def aci(self, t):
        a = 0.0
        for t0, t1, a0, a1 in self.acilma:
            if t >= t0:
                a = a0 + (a1 - a0) * ease_in_out((t - t0) / max(1e-6, t1 - t0))
        return a

    def ciz_bosluk(self, c, t):
        x0, y0 = self.x - self.gen / 2, self.zemin - self.yuk
        # kasa
        c.drawRect(skia.Rect(x0 - 26, y0 - 26, x0 + self.gen + 26, self.zemin), boya("#5a3d2b"))
        c.drawRect(skia.Rect(x0 - 26, y0 - 26, x0 + self.gen + 26, self.zemin), boya(KONTUR, 9))
        # karanlik koridor
        gr = skia.GradientShader.MakeLinear([skia.Point(x0, y0), skia.Point(x0, self.zemin)],
                                            [renk("#0b0f14"), renk("#1d2630")])
        c.drawRect(skia.Rect(x0, y0, x0 + self.gen, self.zemin), skia.Paint(Shader=gr, AntiAlias=True))

    def ciz_kanat(self, c, t):
        """Mentese SAG kenarda. Kanat perspektifle daralir: acildikca serbest (sol) kenar
        izleyiciye yaklastigi icin uzar."""
        xr, y0 = self.x + self.gen / 2, self.zemin - self.yuk
        a = math.radians(self.aci(t))
        gen = self.gen * math.cos(a)
        uzama = 60 * math.sin(a)
        x0 = xr - gen
        nokt = [(x0, y0 - uzama), (xr, y0), (xr, self.zemin), (x0, self.zemin + uzama * 0.3)]
        if gen < 4:
            c.drawLine(xr, y0, xr, self.zemin, boya(KONTUR, 10))
            return
        yol = cokgen(nokt)
        c.drawPath(yol, boya("#8b5a3c"))
        c.save()
        c.clipPath(yol, doAntiAlias=True)
        for i in range(2):   # panel
            py = y0 + 70 + i * 300
            c.drawPath(cokgen([(x0 + gen * 0.15, py - uzama * 0.85), (x0 + gen * 0.85, py - uzama * 0.15),
                               (x0 + gen * 0.85, py + 230), (x0 + gen * 0.15, py + 230 - uzama * 0.6)]), boya("#7a4c31"))
        c.restore()
        c.drawPath(yol, boya(KONTUR, 9))
        kol_x, kol_y = x0 + gen * 0.14, self.zemin - self.yuk * 0.45 - uzama * 0.5
        c.drawCircle(kol_x, kol_y, 15, boya("#e6c35c"))
        c.drawCircle(kol_x, kol_y, 15, boya(KONTUR, 6))


class Oda:
    """Karanlik oda: duvar, pencere + ay isigi huzmesi, sallanan avize, tablo, kapi, on planda koltuk."""
    zemin_y = 1500

    def __init__(self, kapi_acilma=()):
        self.kapi = Kapi(1180, self.zemin_y, acilma=kapi_acilma)

    def lamba_isigi(self, t):
        f = 0.82 + 0.18 * gurultu(t * 3.0, 4)
        if (t * 7.3) % 5.1 < 0.12:   # ara sira titreme
            f *= 0.45
        return kis(f, 0.25, 1.0)

    def _duvar(self, c, t):
        c.drawRect(skia.Rect(-1500, -800, 3500, self.zemin_y), boya("#4b5a63"))
        for i in range(-12, 30):   # soluk duvar kagidi seritleri
            x = i * 110
            c.drawRect(skia.Rect(x, -800, x + 46, self.zemin_y - 160), boya("#53646e"))
        c.drawRect(skia.Rect(-1500, self.zemin_y - 170, 3500, self.zemin_y), boya("#3d3029"))  # lambri
        c.drawLine(-1500, self.zemin_y - 170, 3500, self.zemin_y - 170, boya(KONTUR, 8))
        # pencere
        px, py = 360, 760
        c.drawRect(skia.Rect(px, py, px + 300, py + 380), boya("#16233a"))
        c.drawCircle(px + 205, py + 95, 46, boya("#f2ecc4"))
        c.drawRect(skia.Rect(px, py, px + 300, py + 380), boya(KONTUR, 12))
        c.drawLine(px + 150, py, px + 150, py + 380, boya(KONTUR, 10))
        c.drawLine(px, py + 190, px + 300, py + 190, boya(KONTUR, 10))
        # tablo
        c.drawRect(skia.Rect(-160, 820, 60, 1010), boya("#c9b07a"))
        c.drawPath(cokgen([(-130, 990), (-70, 900), (-20, 950), (20, 880), (35, 990)]), boya("#556b4f"))
        c.drawRect(skia.Rect(-160, 820, 60, 1010), boya(KONTUR, 9))
        self.kapi.ciz_bosluk(c, t)

    def _zemin(self, c, t):
        c.drawRect(skia.Rect(-1500, self.zemin_y, 3500, 2600), boya("#5b4334"))
        for i in range(8):
            y = self.zemin_y + 40 + i * i * 14
            c.drawLine(-1500, y, 3500, y, boya("#4a362a", 5))
        # ay isigi huzmesi pencereden zemine
        yol = cokgen([(360, 1140), (660, 1140), (980, self.zemin_y + 160), (420, self.zemin_y + 160)])
        c.drawPath(yol, boya("#cfe3ff", alfa=28))
        c.drawLine(-1500, self.zemin_y, 3500, self.zemin_y, boya(KONTUR, 8))

    def _avize(self, c, t):
        aci = 7 * math.sin(t * 1.4)
        c.save()
        c.translate(760, -200)
        c.rotate(aci)
        c.drawLine(0, 0, 0, 760, boya(KONTUR, 6))
        c.drawPath(cokgen([(-70, 820), (70, 820), (40, 760), (-40, 760)]), boya("#2e2e2e"))
        f = self.lamba_isigi(t)
        c.drawCircle(0, 832, 22, boya("#ffe8a3", alfa=int(255 * f)))
        c.restore()

    def _isik(self, c, t):
        # avizenin sicak isigi (sahneye radyal parlama)
        f = self.lamba_isigi(t)
        x = 760 + 760 * math.sin(math.radians(7 * math.sin(t * 1.4)))
        gr = skia.GradientShader.MakeRadial(skia.Point(x, 640), 900,
                                            [renk("#ffd98a", a=int(70 * f)), renk("#ffd98a", a=0)])
        c.drawRect(skia.Rect(-1500, -800, 3500, 2600), skia.Paint(Shader=gr, BlendMode=skia.BlendMode.kScreen))

    def _on_plan(self, c, t):
        # karanlik koltuk ve saksi silueti (on plan, bulanik)
        p = boya("#0e1114")
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
        c.drawRoundRect(skia.Rect(-520, 1560, 40, 2200), 80, 80, p)
        c.drawRoundRect(skia.Rect(-560, 1440, -380, 2200), 60, 60, p)
        c.drawPath(cokgen([(1900, 2200), (1940, 1700), (2140, 1700), (2180, 2200)]), p)
        for i in range(5):
            a = -0.9 + i * 0.45
            c.drawLine(2040, 1700, 2040 + math.sin(a) * 260, 1700 - math.cos(a) * 300, boya("#0e1114", 34))

    def katmanlar(self):
        return [(0, 1.0, self._duvar), (1, 1.0, self._zemin), (2, 1.0, self._avize),
                (5, 1.0, self.kapi.ciz_kanat), (20, 1.0, self._isik), (30, 1.35, self._on_plan)]


class Sokak:
    """Zombi istilasina ugramis gece sokagi: gokyuzu, uzak/yakin binalar, lambalar, terk edilmis araba,
    yanan varil, on planda yikik cit. Uzunluk ~5000 px (kamera takip eder)."""
    zemin_y = 1500

    def _gok(self, c, t):
        gr = skia.GradientShader.MakeLinear([skia.Point(0, -900), skia.Point(0, 1500)],
                                            [renk("#070d18"), renk("#1d2b45"), renk("#3a2c3a")], [0, 0.7, 1])
        c.drawRect(skia.Rect(-3000, -1500, 9000, 2600), skia.Paint(Shader=gr))
        for i in range(70):
            x = -2500 + hash01(i, 1) * 9000
            y = -900 + hash01(i, 2) * 1300
            c.drawCircle(x, y, 2 + 2 * hash01(i, 3), boya("#ffffff", alfa=int(120 + 120 * math.sin(t * 2 + i))))
        c.drawCircle(1500, -350, 120, boya("#f3ecc8"))
        c.drawCircle(1460, -380, 22, boya("#ddd5a8"))
        c.drawCircle(1540, -310, 15, boya("#ddd5a8"))
        gr2 = skia.GradientShader.MakeRadial(skia.Point(1500, -350), 520, [renk("#f3ecc8", a=60), renk("#f3ecc8", a=0)])
        c.drawCircle(1500, -350, 520, skia.Paint(Shader=gr2))

    def _uzak_bina(self, c, t):
        x = -2500
        i = 0
        while x < 9000:
            g = 180 + hash01(i, 7) * 220
            h = 500 + hash01(i, 8) * 700
            c.drawRect(skia.Rect(x, 1450 - h, x + g, 1500), boya("#121b2b"))
            if hash01(i, 9) > 0.6:   # anten / yikik tepe
                c.drawLine(x + g * 0.5, 1450 - h, x + g * 0.5, 1450 - h - 90, boya("#121b2b", 8))
            x += g + 10
            i += 1

    def _orta_bina(self, c, t):
        x = -2000
        i = 0
        while x < 8000:
            g = 360 + hash01(i, 11) * 260
            h = 650 + hash01(i, 12) * 500
            top = 1500 - h
            c.drawRect(skia.Rect(x, top, x + g, 1500), boya("#24314a"))
            c.drawRect(skia.Rect(x, top, x + g, 1500), boya(KONTUR, 7))
            for r in range(int((h - 120) // 130)):
                for k in range(int((g - 60) // 95)):
                    wx, wy = x + 40 + k * 95, top + 50 + r * 130
                    h0 = hash01(i, r, k)
                    if h0 > 0.82:
                        yan = 0.75 + 0.25 * gurultu(t * 2 + h0 * 10, i)
                        c.drawRect(skia.Rect(wx, wy, wx + 50, wy + 70), boya("#f2c66d", alfa=int(230 * yan)))
                    elif h0 < 0.12:   # kirik pencere
                        c.drawPath(cokgen([(wx, wy), (wx + 50, wy), (wx + 20, wy + 40), (wx, wy + 70)]), boya("#0b0f14"))
                    else:
                        c.drawRect(skia.Rect(wx, wy, wx + 50, wy + 70), boya("#141c2b"))
            x += g + 40
            i += 1

    def _yol(self, c, t):
        c.drawRect(skia.Rect(-3000, 1500, 9000, 1560), boya("#4a4a52"))
        c.drawRect(skia.Rect(-3000, 1560, 9000, 2600), boya("#2a2a30"))
        for i in range(-10, 40):
            x = i * 320
            c.drawRect(skia.Rect(x, 1760, x + 160, 1782), boya("#8a8456"))
        c.drawLine(-3000, 1500, 9000, 1500, boya(KONTUR, 8))
        c.drawLine(-3000, 1560, 9000, 1560, boya(KONTUR, 6))
        # sokak lambalari (biri titrer)
        for i, x in enumerate(range(-600, 6000, 1100)):
            c.drawRect(skia.Rect(x - 10, 900, x + 10, 1500), boya("#1b1b1f"))
            c.drawLine(x, 900, x + 110, 880, boya("#1b1b1f", 16))
            yan = 1.0 if i % 3 else (1.0 if (t * 5.7) % 3.1 > 0.4 else 0.15)
            c.drawCircle(x + 120, 895, 20, boya("#ffe6a0", alfa=int(255 * yan)))
            koni = cokgen([(x + 100, 900), (x + 140, 900), (x + 330, 1520), (x - 90, 1520)])
            c.drawPath(koni, boya("#ffe6a0", alfa=int(36 * yan)))
        # terk edilmis araba (yatik, kapisi acik)
        c.save()
        c.translate(2600, 1500)
        c.rotate(-4)
        govde = cokgen([(-300, -40), (-300, -170), (-180, -180), (-110, -290), (130, -290), (210, -180), (300, -160), (300, -40)])
        c.drawPath(govde, boya("#7d2f2a"))
        c.drawPath(cokgen([(-90, -270), (110, -270), (170, -190), (-160, -190)]), boya("#1c2a33"))
        c.drawPath(govde, boya(KONTUR, 9))
        c.drawPath(cokgen([(-40, -180), (-40, -50), (-150, -10), (-150, -150)]), boya("#6b2622"))
        c.drawPath(cokgen([(-40, -180), (-40, -50), (-150, -10), (-150, -150)]), boya(KONTUR, 7))
        for wx in (-170, 170):
            c.drawCircle(wx, -40, 58, boya("#1b1b1b"))
            c.drawCircle(wx, -40, 58, boya(KONTUR, 8))
        c.restore()
        self._varil(c, t, 1350)

    def _varil(self, c, t, x):
        c.drawRect(skia.Rect(x - 60, 1340, x + 60, 1500), boya("#5a4a3a"))
        c.drawRect(skia.Rect(x - 60, 1340, x + 60, 1500), boya(KONTUR, 8))
        # ates: deterministik, titreyen alev dillari
        for i in range(9):
            faz = t * (3 + hash01(i) * 2) + i
            h = 120 + 90 * (0.5 + 0.5 * math.sin(faz * 2.1)) * (0.6 + 0.4 * hash01(i, 5))
            ox = (hash01(i, 2) - 0.5) * 90 + 10 * math.sin(faz * 3)
            renk_h = "#ffcf5a" if i % 3 == 0 else "#ff8a2a" if i % 3 == 1 else "#e8471c"
            c.drawPath(cokgen([(x + ox - 26, 1345), (x + ox + 26, 1345), (x + ox + 8 * math.sin(faz * 4), 1345 - h)]),
                       boya(renk_h, alfa=220))
        gr = skia.GradientShader.MakeRadial(skia.Point(x, 1300), 600, [renk("#ff9a40", a=70), renk("#ff9a40", a=0)])
        c.drawCircle(x, 1300, 600, skia.Paint(Shader=gr, BlendMode=skia.BlendMode.kScreen))

    def _sis(self, c, t):
        for i in range(6):
            x = -1500 + i * 1300 + (t * 60 * (0.5 + hash01(i))) % 1300
            y = 1350 + 120 * hash01(i, 4)
            p = boya("#9fb0c8", alfa=34)
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 60))
            c.drawOval(skia.Rect(x - 700, y - 110, x + 700, y + 110), p)

    def _on_plan(self, c, t):
        p = boya("#0b0d10")
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8))
        for i, x in enumerate(range(-1200, 9000, 1500)):
            # yikik tahta cit parcalari
            for k in range(4):
                h = 320 + 160 * hash01(i, k)
                xx = x + k * 70
                c.drawPath(cokgen([(xx, 2100), (xx, 2100 - h), (xx + 22, 2100 - h - 30), (xx + 44, 2100 - h), (xx + 44, 2100)]), p)
            c.drawRect(skia.Rect(x - 20, 1860, x + 300, 1890), p)

    def katmanlar(self):
        return [(0, 0.05, self._gok), (1, 0.25, self._uzak_bina), (2, 0.55, self._orta_bina),
                (3, 0.8, self._sis), (4, 1.0, self._yol), (30, 1.4, self._on_plan)]
