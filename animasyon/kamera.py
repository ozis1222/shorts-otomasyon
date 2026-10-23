# -*- coding: utf-8 -*-
"""
Kamera: anahtar kareler (x, y, zoom) + karakter takibi + olaya bagli sarsinti.
Takip yumusatmasi sabit 1/240 sn adimlarla onceden hesaplanir: sonuc FPS'ten bagimsizdir.
"""
import math

from .temel import ease_in_out, gurultu, kis, lerp

MERKEZ = (540, 1100)   # dunyadaki kamera noktasinin ekranda dustugu yer


class Kamera:
    def __init__(self, anahtarlar, sarsintilar=(), takip=None):
        """
        anahtarlar: [(t, x, y, zoom)] — aralarda ease-in-out.
        takip: {'t0','t1','hedef': fonk(t)->x, 'sertlik': 3.0, 'onde': 120}  (x'i karaktere kilitler)
        sarsintilar: [(t0, guc_px, sure)]
        """
        self.k = sorted(anahtarlar)
        self.s = list(sarsintilar)
        self.takip = takip
        self._takip_cache = None

    def _anahtar(self, t):
        k = self.k
        if t <= k[0][0]:
            return k[0][1:]
        for a, b in zip(k, k[1:]):
            if a[0] <= t <= b[0]:
                u = ease_in_out((t - a[0]) / max(1e-6, b[0] - a[0]))
                return tuple(lerp(x, y, u) for x, y in zip(a[1:], b[1:]))
        return k[-1][1:]

    def _takip_x(self, t):
        tk = self.takip
        if self._takip_cache is None:
            dt = 1 / 240
            n = int((tk["t1"] - tk["t0"]) / dt) + 2
            x = tk["hedef"](tk["t0"]) + tk.get("onde", 0)
            dizi = []
            for i in range(n):
                tt = tk["t0"] + i * dt
                hedef = tk["hedef"](tt) + tk.get("onde", 0)
                x += (hedef - x) * (1 - math.exp(-tk.get("sertlik", 3.0) * dt))
                dizi.append(x)
            self._takip_cache = (dt, dizi)
        dt, dizi = self._takip_cache
        i = int(kis((t - tk["t0"]) / dt, 0, len(dizi) - 1))
        return dizi[i]

    def durum(self, t):
        x, y, z = self._anahtar(t)
        tk = self.takip
        if tk and tk["t0"] <= t <= tk["t1"]:
            # takipten anahtar kareye yumusak gecis (ilk/son 0.4 sn)
            agirlik = min(kis((t - tk["t0"]) / 0.4), kis((tk["t1"] - t) / 0.4)) if tk.get("yumusak_kenar", True) else 1
            x = lerp(x, self._takip_x(t), agirlik)
        dx = dy = rot = 0.0
        for t0, guc, sure in self.s:
            if t0 <= t <= t0 + sure:
                u = (t - t0) / sure
                g = guc * (1 - u) ** 2
                dx += g * gurultu(t * 23, 1)
                dy += g * gurultu(t * 27, 2)
                rot += g * 0.04 * gurultu(t * 19, 3)
        return x + dx, y + dy, z, rot


def uygula(canvas, durum, p=1.0):
    """Katmanin parallax katsayisi p ile kamera donusumunu canvas'a uygular."""
    x, y, z, rot = durum
    zl = 1 + (z - 1) * p if p < 1 else z * (1 + (p - 1) * 0.15)
    canvas.translate(*MERKEZ)
    if rot:
        canvas.rotate(rot)
    canvas.scale(zl, zl)
    canvas.translate(-x * p, -y * (p if p < 1 else 1))
