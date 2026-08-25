"""
Baglanti testi.

OpenStreetMap servislerine (Nominatim + Overpass) dogrudan istek atar ve
ham sonucu / gercek hatayi ekrana yazar. Arama 0 sonuc verdiginde sebebini
hizlica gormek icin kullanilir.

Calistirma:
    .venv\\Scripts\\python.exe baglanti_testi.py         (Windows)
    .venv/bin/python baglanti_testi.py                    (Mac/Linux)
"""
from __future__ import annotations

import requests

from app.config import settings

UA = settings.USER_AGENT
print("=" * 60)
print("  Lead Finder - Baglanti Testi")
print(f"  User-Agent: {UA}")
print("=" * 60)


def test_nominatim() -> None:
    print("\n[1] Nominatim (konum servisi) test ediliyor...")
    url = f"{settings.NOMINATIM_URL}/search"
    params = {"q": "Beyoglu, Istanbul, Turkiye", "format": "jsonv2", "limit": "3"}
    try:
        r = requests.get(
            url, params=params,
            headers={"User-Agent": UA, "Accept": "application/json"},
            timeout=25,
        )
        print(f"    HTTP durum kodu: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"    Donen sonuc sayisi: {len(data)}")
            for item in data[:3]:
                print(f"      - {item.get('osm_type')}/{item.get('osm_id')} "
                      f"| {item.get('class')} | {item.get('display_name')}")
            if data:
                print("    ✓ Nominatim CALISIYOR.")
            else:
                print("    ⚠ Baglanti var ama sonuc bos dondu.")
        else:
            print(f"    ✗ Beklenmeyen durum. Yanit (ilk 300 karakter):")
            print("     ", (r.text or "")[:300].replace("\n", " "))
    except Exception as e:
        print(f"    ✗ HATA: {type(e).__name__}: {e}")


def test_overpass() -> None:
    print("\n[2] Overpass (isletme verisi) test ediliyor...")
    query = (
        "[out:json][timeout:60];"
        'node["amenity"="dentist"](41.02,28.94,41.06,28.99);'
        "out center 5;"
    )
    try:
        r = requests.post(
            settings.OVERPASS_URL, data={"data": query},
            headers={"User-Agent": UA}, timeout=90,
        )
        print(f"    HTTP durum kodu: {r.status_code}")
        if r.status_code == 200:
            els = r.json().get("elements", [])
            print(f"    Beyoglu civari bulunan dis noktasi: {len(els)}")
            print("    ✓ Overpass CALISIYOR." if els is not None else "")
        else:
            print(f"    ✗ Beklenmeyen durum. Yanit (ilk 300 karakter):")
            print("     ", (r.text or "")[:300].replace("\n", " "))
    except Exception as e:
        print(f"    ✗ HATA: {type(e).__name__}: {e}")


if __name__ == "__main__":
    test_nominatim()
    test_overpass()
    print("\n" + "=" * 60)
    print("  Test bitti. Yukaridaki ciktinin tamamini kopyalayip paylasin.")
    print("=" * 60)
