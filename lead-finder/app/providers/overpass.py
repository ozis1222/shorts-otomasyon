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

    def __init__(self) -> None:
        # Son aramanin teshis bilgisi (panelde gosterilir).
        self.last_diagnostics: dict = {}

    def search(
        self, city: str, district: str, sector: str, limit: int
    ) -> list[RawBusiness]:
        diag: dict = {"sector_recognized": True, "area": None, "scope": None,
                      "raw_count": 0, "error": None}
        self.last_diagnostics = diag

        tags = resolve_sector_tags(sector)
        if not tags:
            diag["sector_recognized"] = False
            diag["error"] = "Sektor OSM etiketine cevrilemedi."
            return []

        area = geocode_area(city, district, diag)
        if not area:
            reason = diag.get("http_error")
            diag["error"] = (
                "Konum bulunamadi (Nominatim). "
                + (f"Sebep: {reason}. " if reason else "")
                + "Sehir/ilce yazimini veya internet baglantinizi kontrol edin."
            )
            return []
        diag["area"] = area.display_name
        diag["area_type"] = area.osm_type

        # 1) Once idari alan (area) ile dene.
        area_scope = self._area_scope(area)
        results, raw_count = self._query_and_parse(
            tags, area_scope or self._bbox_scope(area),
            city, district, sector, limit, diag,
        )
        # 2) Alan sorgusu bos dondu ama elimizde bbox de varsa, bbox ile tekrar dene.
        if not results and area_scope and area.bbox:
            results, raw_count = self._query_and_parse(
                tags, self._bbox_scope(area),
                city, district, sector, limit, diag,
            )
        diag["raw_count"] = raw_count
        return results

    def _query_and_parse(self, tags, scope, city, district, sector, limit, diag):
        diag["scope"] = scope
        query = self._build_query(tags, scope, limit)
        data = http_post_json(settings.OVERPASS_URL, data={"data": query}, diag=diag)
        if data is None:
            reason = diag.get("http_error")
            diag["error"] = (
                "Overpass API'ye ulasilamadi. "
                + (f"Sebep: {reason}. " if reason else "")
                + "Birkac dakika sonra tekrar deneyin."
            )
            return [], 0
        if "elements" not in data:
            return [], 0

        elements = data["elements"]
        results: list[RawBusiness] = []
        seen: set[str] = set()
        for el in elements:
            rb = self._element_to_business(el, city, district, sector)
            if rb and rb.source_ref not in seen:
                seen.add(rb.source_ref)
                results.append(rb)
            if len(results) >= limit:
                break
        return results, len(elements)

    def _build_query(self, tags, scope: str, limit: int) -> str:
        # Her etiket icin ayri nwr satiri (OR mantigi).
        lines = [f'  nwr["{k}"="{v}"]({scope});' for (k, v) in tags]
        body = "\n".join(lines)
        # "out center": way/relation icin merkez nokta ekler; varsayilan "body"
        # verbosity zaten etiketleri getirir. Limit sona yazilir.
        return (
            f"[out:json][timeout:90];\n"
            f"(\n{body}\n);\n"
            f"out center {max(1, limit)};"
        )

    def _area_scope(self, area) -> str | None:
        aid = area.overpass_area_id
        return f"area:{aid}" if aid else None

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
