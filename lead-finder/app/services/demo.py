"""
Demo site servisi.

Her isletme icin sektore uygun, template tabanli bir demo sayfasi olusturur.
Sifirdan rastgele site URETMEZ; sadece hazir sablonlara isletme bilgilerini yerlestirir.

Kurallar:
  - Uydurma yorum / sahte calisan / sahte fiyat OLUSTURULMAZ.
  - Eksik bilgi icin "Bilgi eklenebilir" placeholder kullanilir.
  - Her demo sayfasinda gorunur "ornek/demo tasarim" ibaresi bulunur (template'te).
"""
from __future__ import annotations

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Business, DemoSite
from ..providers.base import _normalize_sector_key

# Sektor -> template dosya adi (templates/demo/ altinda).
SECTOR_TEMPLATE_MAP: dict[str, str] = {
    "dis klinigi": "dental",
    "dis": "dental",
    "dentist": "dental",
    "guzellik merkezi": "beauty",
    "guzellik": "beauty",
    "restoran": "restaurant",
    "restaurant": "restaurant",
    "cafe": "restaurant",
    "kafe": "restaurant",
    "kuafor": "hairdresser",
    "berber": "hairdresser",
    "emlak": "realestate",
    "emlakci": "realestate",
    "oto servis": "autoservice",
    "oto tamir": "autoservice",
}

TEMPLATE_TYPES = ("dental", "beauty", "restaurant", "hairdresser", "realestate", "autoservice")

PLACEHOLDER = "Bilgi eklenebilir"


def template_for_sector(sector: str | None) -> str:
    key = _normalize_sector_key(sector or "")
    if key in SECTOR_TEMPLATE_MAP:
        return SECTOR_TEMPLATE_MAP[key]
    for known, tmpl in SECTOR_TEMPLATE_MAP.items():
        if known in key or (key and key in known):
            return tmpl
    return "dental"  # makul varsayilan


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "isletme"


def _unique_slug(db: Session, base: str, business_id: int) -> str:
    slug = base
    n = 1
    while True:
        existing = db.execute(
            select(DemoSite).where(DemoSite.demo_slug == slug)
        ).scalar_one_or_none()
        if existing is None or existing.business_id == business_id:
            return slug
        n += 1
        slug = f"{base}-{n}"


def create_or_update_demo(db: Session, business: Business, base_url: str) -> DemoSite:
    template_type = template_for_sector(business.sector)
    base_slug = slugify(business.name)
    slug = _unique_slug(db, base_slug, business.id)
    demo_url = f"{base_url}/demo/{slug}"

    demo = business.demo
    if demo is None:
        demo = DemoSite(business_id=business.id)
        db.add(demo)
        business.demo = demo
    demo.template_type = template_type
    demo.demo_slug = slug
    demo.demo_url = demo_url
    demo.status = "ACTIVE"
    db.commit()
    return demo


def build_demo_context(business: Business) -> dict:
    """Template'e gonderilecek, guvenli/placeholder'li isletme verisi."""
    return {
        "name": business.name or PLACEHOLDER,
        "sector": business.sector or PLACEHOLDER,
        "phone": business.phone or PLACEHOLDER,
        "address": business.address or PLACEHOLDER,
        "city": business.city or "",
        "district": business.district or "",
        "description": business.description or PLACEHOLDER,
        "email": business.email or PLACEHOLDER,
        "placeholder": PLACEHOLDER,
    }
