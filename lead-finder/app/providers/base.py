"""
Veri kaynagi (provider) altyapisi.

Her veri kaynagi BaseProvider'dan tureyip search() metodunu uygular.
Boylece ileride yeni kaynak eklemek (ornek: baska bir acik dizin) sadece
yeni bir dosya + register_provider() cagrisi ile mumkun olur.

Sektor -> OpenStreetMap etiketi eslemesi de burada tanimlidir ve genisletilebilir.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RawBusiness:
    """Provider'larin dondurdugu ham isletme kaydi (henuz normalize edilmemis)."""

    name: str
    source: str
    source_ref: str  # kaynak icindeki benzersiz kimlik (ornek: OSM node/123)
    category: str | None = None
    sector: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    city: str | None = None
    district: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    description: str | None = None
    opening_hours: str | None = None
    source_url: str | None = None
    extra: dict = field(default_factory=dict)


class BaseProvider(ABC):
    name: str = "base"

    @abstractmethod
    def search(
        self, city: str, district: str, sector: str, limit: int
    ) -> list[RawBusiness]:
        """Verilen sehir/ilce/sektor icin en fazla `limit` isletme dondurur."""
        raise NotImplementedError


# ============================================================
#  SEKTOR -> OpenStreetMap ETIKET ESLEMESI
#  Anahtar: kullanicinin girebilecegi sektor adi (kucuk harf, Turkce).
#  Deger: Overpass sorgusunda kullanilacak (key, value) etiket listesi.
#  Yeni sektor eklemek icin buraya bir satir eklemeniz yeterli.
# ============================================================
SECTOR_OSM_TAGS: dict[str, list[tuple[str, str]]] = {
    "dis klinigi": [("amenity", "dentist"), ("healthcare", "dentist")],
    "dis": [("amenity", "dentist"), ("healthcare", "dentist")],
    "dentist": [("amenity", "dentist"), ("healthcare", "dentist")],
    "guzellik merkezi": [("shop", "beauty"), ("shop", "cosmetics")],
    "guzellik": [("shop", "beauty"), ("shop", "cosmetics")],
    "restoran": [("amenity", "restaurant")],
    "restaurant": [("amenity", "restaurant")],
    "cafe": [("amenity", "cafe")],
    "kafe": [("amenity", "cafe")],
    "kuafor": [("shop", "hairdresser")],
    "berber": [("shop", "hairdresser")],
    "emlak": [("office", "estate_agent")],
    "emlakci": [("office", "estate_agent")],
    "oto servis": [("shop", "car_repair"), ("craft", "car_repair")],
    "oto tamir": [("shop", "car_repair"), ("craft", "car_repair")],
    "otel": [("tourism", "hotel")],
    "eczane": [("amenity", "pharmacy")],
    "veteriner": [("amenity", "veterinary")],
    "spor salonu": [("leisure", "fitness_centre")],
}


def resolve_sector_tags(sector: str) -> list[tuple[str, str]]:
    """Sektor adini OSM etiketlerine cevirir. Bilinmiyorsa bos liste dondurur."""
    key = _normalize_sector_key(sector)
    if key in SECTOR_OSM_TAGS:
        return SECTOR_OSM_TAGS[key]
    # Kismi eslesme dene (ornek: "ozel dis klinigi" -> "dis klinigi").
    for known, tags in SECTOR_OSM_TAGS.items():
        if known in key or key in known:
            return tags
    return []


def _normalize_sector_key(sector: str) -> str:
    s = (sector or "").strip().lower()
    # Turkce karakterleri sadelestir (eslesmeyi kolaylastirmak icin).
    trans = str.maketrans(
        {"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
         "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c"}
    )
    return s.translate(trans)
