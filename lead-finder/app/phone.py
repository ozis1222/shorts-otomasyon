"""
Turkiye telefon numarasi normalizasyonu.

Amac: farkli formatlardaki numaralari mumkunse +90XXXXXXXXXX bicimine cevirmek.
Cevrilemeyen (gecersiz) numaralarda orijinal metin korunur.
"""
from __future__ import annotations

import re


def normalize_tr_phone(raw: str | None) -> str | None:
    if not raw:
        return None

    # Sadece rakamlari ve bas "+" isaretini tut.
    text = raw.strip()
    plus = text.startswith("+")
    digits = re.sub(r"\D", "", text)

    if not digits:
        return None

    # Ulke kodu / bas sifir varyasyonlarini sadelestir.
    if plus and digits.startswith("90"):
        digits = digits[2:]
    elif digits.startswith("0090"):
        digits = digits[4:]
    elif digits.startswith("90") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]

    # Gecerli TR numarasi: 10 hane, ilk hane 0 degil (ornek: 5XXXXXXXXX veya 2XXXXXXXXX).
    if len(digits) == 10 and digits[0] != "0":
        return "+90" + digits

    # Cevrilemedi -> orijinali dondur (bilgi kaybetme).
    return raw.strip()
