"""
Overpass API provider'i (OpenStreetMap verisi).

Acik ve izinli veri kaynagidir. Google Maps gibi kapali/agresif kaynaklara
DOKUNMAZ. Sadece OSM'de zaten herkese acik olan isletme bilgilerini ceker.

Akis:
  1. Nominatim ile sehir/ilce bolgesini bul.
  2. Sektore karsilik gelen OSM etiketleriyle Overpass sorgusu kur.
  3. node/way/relation sonuclarini RawBusiness listesine cevir.
"""
from __future__ import annotations

from ..http_client import http_post_json
from ..config import settings
from .base import BaseProvider, RawBusiness, resolve_sector_tags
from .openstreetmap import geocode_area


class OverpassProvider(BaseProvider):
    name = "overpass"

    def search(
        self, city: str, district: str, sector: str, limit: int
    ) -> list[RawBusiness]:
        tags = resolve_sector_tags(sector)
        if not tags:
            # Bilinmeyen sektor: bos don, cagiran taraf kullaniciyi bilgilendirir.
            return []

        area = geocode_area(city, district)
        if not area:
            return []

        query = self._build_query(tags, area, limit)
        data = http_post_json(settings.OVERPASS_URL, data={"data": query})
        if not data or "elements" not in data:
            return []

        results: list[RawBusiness] = []
        seen: set[str] = set()
        for el in data["elements"]:
            rb = self._element_to_business(el, city, district, sector)
            if rb and rb.source_ref not in seen:
                seen.add(rb.source_ref)
                results.append(rb)
            if len(results) >= limit:
                break
        return results

    def _build_query(self, tags, area, limit: int) -> str:
        area_id = area.overpass_area_id
        # Her etiket icin ayri nwr satiri (OR mantigi).
        lines = []
        scope = f"area:{area_id}" if area_id else self._bbox_scope(area)
        for (k, v) in tags:
            lines.append(f'  nwr["{k}"="{v}"]({scope});')
        body = "\n".join(lines)
        # timeout ve maxsize makul tutuldu; out center: way/relation icin merkez nokta.
        return (
            f"[out:json][timeout:60];\n"
            f"(\n{body}\n);\n"
            f"out center tags {max(1, limit)};"
        )

    def _bbox_scope(self, area) -> str:
        if area.bbox:
            s, n, w, e = area.bbox
            return f"{s},{w},{n},{e}"
        # Son care: nokta etrafinda ~5km yaricap.
        if area.lat is not None and area.lon is not None:
            return f"around:5000,{area.lat},{area.lon}"
        return "around:5000,41.0,29.0"  # Istanbul merkez (guvenli varsayilan)

    def _element_to_business(
        self, el: dict, city: str, district: str, sector: str
    ) -> RawBusiness | None:
        t = el.get("tags", {})
        name = t.get("name") or t.get("brand")
        if not name:
            return None  # ismi olmayan kaydi atla

        osm_type = el.get("type", "node")
        osm_id = el.get("id")
        source_ref = f"{osm_type}/{osm_id}"

        # Koordinat (node icin lat/lon; way/relation icin center).
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")

        phone = t.get("phone") or t.get("contact:phone") or t.get("contact:mobile")
        website = (
            t.get("website")
            or t.get("contact:website")
            or t.get("url")
        )
        email = t.get("email") or t.get("contact:email")

        address = self._build_address(t)
        category = self._build_category(t)

        return RawBusiness(
            name=name,
            source=self.name,
            source_ref=source_ref,
            category=category,
            sector=sector,
            phone=phone,
            email=email,
            website=website,
            address=address or None,
            city=t.get("addr:city") or city,
            district=t.get("addr:district") or t.get("addr:suburb") or district,
            latitude=float(lat) if lat is not None else None,
            longitude=float(lon) if lon is not None else None,
            description=t.get("description"),
            opening_hours=t.get("opening_hours"),
            source_url=f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
        )

    @staticmethod
    def _build_address(t: dict) -> str:
        parts = [
            t.get("addr:street"),
            t.get("addr:housenumber"),
            t.get("addr:suburb"),
            t.get("addr:district"),
            t.get("addr:city"),
            t.get("addr:postcode"),
        ]
        return " ".join(p for p in parts if p).strip()

    @staticmethod
    def _build_category(t: dict) -> str | None:
        for key in ("amenity", "shop", "office", "craft", "healthcare",
                    "tourism", "leisure"):
            if key in t:
                return f"{key}={t[key]}"
        return None
