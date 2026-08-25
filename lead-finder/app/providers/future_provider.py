"""
Ornek/sablon provider.

Ileride yeni bir veri kaynagi (baska bir acik dizin, resmi bir API vb.)
eklemek istediginizde bu dosyayi kopyalayip doldurmaniz ve registry.py
icine kaydetmeniz yeterlidir.

Bu provider varsayilan olarak devre disidir (bos liste dondurur).
"""
from __future__ import annotations

from .base import BaseProvider, RawBusiness


class FutureProvider(BaseProvider):
    name = "future_provider"

    def search(
        self, city: str, district: str, sector: str, limit: int
    ) -> list[RawBusiness]:
        # TODO: Yeni kaynak entegrasyonu buraya.
        # Ornek:
        #   data = http_get_json("https://acik-dizin.example/api", params={...})
        #   return [RawBusiness(name=..., source=self.name, source_ref=..., ...)]
        return []
