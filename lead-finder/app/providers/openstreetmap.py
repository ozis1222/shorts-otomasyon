"""
Nominatim (OpenStreetMap geokodlama) yardimcisi.

Sehir + ilce adini alir, ilgili bolgenin OSM alan kimligini (area id) veya
sinir kutusunu (bounding box) dondurur. Bu bilgi Overpass sorgusunu
dogru bolgeyle sinirlamak icin kullanilir.

Nominatim kullanim kurallari geregi:
  - Anlamli bir User-Agent gonderilir.
  - Istekler arasinda bekleme uygulanir (bkz. HttpClient).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import settings
from ..http_client import http_get_json


@dataclass
class GeoArea:
    display_name: str
    osm_type: str | None      # "relation" | "way" | "node"
    osm_id: int | None
    bbox: tuple[float, float, float, float] | None  # (south, north, west, east)
    lat: float | None
    lon: float | None

    @property
    def overpass_area_id(self) -> int | None:
        """OSM relation/way -> Overpass area id.
        relation: 3600000000 + id, way: 2400000000 + id."""
        if self.osm_type == "relation" and self.osm_id:
            return 3_600_000_000 + self.osm_id
        if self.osm_type == "way" and self.osm_id:
            return 2_400_000_000 + self.osm_id
        return None


def geocode_area(city: str, district: str) -> GeoArea | None:
    """Sehir/ilce icin bolge bilgisini dondurur; bulunamazsa None."""
    parts = [p for p in [district, city, "Turkiye"] if p and p.strip()]
    query = ", ".join(parts)

    params = {
        "q": query,
        "format": "jsonv2",
        "limit": "1",
        "addressdetails": "0",
        "polygon_geojson": "0",
    }
    url = f"{settings.NOMINATIM_URL}/search"
    data = http_get_json(url, params=params)
    if not data:
        return None

    item = data[0]
    bbox = None
    if item.get("boundingbox") and len(item["boundingbox"]) == 4:
        try:
            s, n, w, e = (float(x) for x in item["boundingbox"])
            bbox = (s, n, w, e)
        except (TypeError, ValueError):
            bbox = None

    return GeoArea(
        display_name=item.get("display_name", query),
        osm_type=item.get("osm_type"),
        osm_id=int(item["osm_id"]) if item.get("osm_id") else None,
        bbox=bbox,
        lat=float(item["lat"]) if item.get("lat") else None,
        lon=float(item["lon"]) if item.get("lon") else None,
    )
