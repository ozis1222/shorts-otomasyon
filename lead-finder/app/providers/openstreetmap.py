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


def geocode_area(city: str, district: str, diag: dict | None = None) -> GeoArea | None:
    """Sehir/ilce icin bolge bilgisini dondurur; bulunamazsa None.

    Onemli: Nominatim ilk sonuc olarak bazen tek bir NOKTA (place node)
    dondurur; bunun sinir kutusu cok kucuktur ve Overpass sorgusu 0 sonuc
    verir. Bu yuzden birden fazla sonuc isteyip, mumkunse IDARI SINIR
    (relation/way boundary) olan sonucu tercih ederiz. Boylece ilcenin tamami
    taranir.
    """
    parts = [p for p in [district, city, "Turkiye"] if p and p.strip()]
    query = ", ".join(parts)

    params = {
        "q": query,
        "format": "jsonv2",
        "limit": "5",            # birden fazla sonuc: en iyisini seceriz
        "addressdetails": "0",
        "polygon_geojson": "0",
    }
    url = f"{settings.NOMINATIM_URL}/search"
    data = http_get_json(url, params=params, diag=diag)
    if not data:
        return None

    item = _pick_best_area(data)
    bbox = _parse_bbox(item.get("boundingbox"))

    return GeoArea(
        display_name=item.get("display_name", query),
        osm_type=item.get("osm_type"),
        osm_id=int(item["osm_id"]) if item.get("osm_id") else None,
        bbox=bbox,
        lat=float(item["lat"]) if item.get("lat") else None,
        lon=float(item["lon"]) if item.get("lon") else None,
    )


def _pick_best_area(results: list[dict]) -> dict:
    """Sonuclar arasindan en iyi 'alan'i secer:
    once idari sinir (boundary/relation veya way), yoksa ilk sonuc."""
    # 1) class=boundary olan bir sonuc (idari sinir) en idealidir.
    for r in results:
        if r.get("class") == "boundary" and r.get("osm_type") in ("relation", "way"):
            return r
    # 2) Herhangi bir relation/way (alan olusturabilir).
    for r in results:
        if r.get("osm_type") in ("relation", "way"):
            return r
    # 3) Son care: ilk sonuc (muhtemelen nokta; bbox ile aranir).
    return results[0]


def _parse_bbox(raw) -> tuple[float, float, float, float] | None:
    if raw and len(raw) == 4:
        try:
            s, n, w, e = (float(x) for x in raw)
            return (s, n, w, e)
        except (TypeError, ValueError):
            return None
    return None
