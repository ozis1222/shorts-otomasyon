"""
Provider kayit defteri.

Aktif veri kaynaklari burada listelenir. Collector servisi bu listeyi
sirayla kullanir. Yeni kaynak eklemek icin buraya bir satir ekleyin.
"""
from __future__ import annotations

from .base import BaseProvider
from .overpass import OverpassProvider

# Sirali: ilk kaynak once denenir. Overpass (OSM) birincil ve ucretsiz kaynak.
ACTIVE_PROVIDERS: list[BaseProvider] = [
    OverpassProvider(),
    # FutureProvider(),  # <- yeni kaynak hazir oldugunda acin
]


def get_providers() -> list[BaseProvider]:
    return ACTIVE_PROVIDERS
