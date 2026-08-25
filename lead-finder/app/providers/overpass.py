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

import re

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

        results: list[RawBusiness] = []

        # 1) Nominatim ile bolgeyi cozmeyi dene.
        area = geocode_area(city, district, diag)
        if area:
            diag["area"] = area.display_name
            diag["area_type"] = area.osm_type
            area_scope = self._area_scope(area)
            results, raw_count = self._query_and_parse(
                tags, area_scope or self._bbox_scope(area),
                city, district, sector, limit, diag,
            )
            # Alan sorgusu bos dondu ama bbox de varsa, bbox ile tekrar dene.
            if not results and area_scope and area.bbox:
                results, raw_count = self._query_and_parse(
                    tags, self._bbox_scope(area),
                    city, district, sector, limit, diag,
                )
            diag["raw_count"] = raw_count

        # 2) Nominatim basarisiz VEYA 0 sonuc -> Overpass'in kendi isim-tabanli
        #    alan bulmasina dus (Nominatim'e hic bagimli kalmadan).
        if not results:
            results = self._search_by_area_name(
                tags, city, district, sector, limit, diag
            )

        # Hala bir sey yoksa ve Nominatim de cozememisse, anlamli hata yaz.
        if not results and not area and not diag.get("error"):
            reason = diag.get("http_error")
            diag["error"] = (
                "Konum bulunamadi. "
                + (f"Sebep: {reason}. " if reason else "")
                + "Sehir/ilce yazimini (Turkce karakterlerle) veya internet "
                + "baglantinizi kontrol edin."
            )
        return results

    def _search_by_area_name(self, tags, city, district, sector, limit, diag):
        """Nominatim'e ihtiyac duymadan, alani ISMINE gore Overpass icinde bulur.
        Once ilce adini, olmazsa sehir adini dener."""
        candidates = [n.strip() for n in (district, city) if n and n.strip()]
        for name in candidates:
            query = self._build_named_area_query(tags, name, limit)
            data = self._overpass_request(query, diag)
            if not data or "elements" not in data:
                continue
            elements = data["elements"]
            results = self._parse_elements(elements, city, district, sector, limit)
            if results:
                # Basarili: onceki Nominatim hatasini temizle, teshisi guncelle.
                diag["error"] = None
                diag["area"] = diag.get("area") or f"{name} (Overpass isim eslemesi)"
                diag["scope"] = f'area name~"^{name}$" (idari sinir)'
                diag["raw_count"] = len(elements)
                return results
        return []

    def _build_named_area_query(self, tags, name: str, limit: int) -> str:
        esc = self._escape_regex(name)
        lines = [f'  nwr["{k}"="{v}"](area.searchArea);' for (k, v) in tags]
        body = "\n".join(lines)
        # Ismi idari sinir olarak eslestir (buyuk/kucuk harf duyarsiz).
        return (
            f"[out:json][timeout:90];\n"
            f'area["name"~"^{esc}$",i]["boundary"="administrative"]->.searchArea;\n'
            f"(\n{body}\n);\n"
            f"out center {max(1, limit)};"
        )

    @staticmethod
    def _escape_regex(s: str) -> str:
        s = s.replace("\\", "").replace('"', "")
        return re.sub(r"([.^$*+?()\[\]{}|])", r"\\\1", s)

    def _parse_elements(self, elements, city, district, sector, limit):
        results: list[RawBusiness] = []
        seen: set[str] = set()
        for el in elements:
            rb = self._element_to_business(el, city, district, sector)
            if rb and rb.source_ref not in seen:
                seen.add(rb.source_ref)
                results.append(rb)
            if len(results) >= limit:
                break
        return results

    def _query_and_parse(self, tags, scope, city, district, sector, limit, diag):
        diag["scope"] = scope
        query = self._build_query(tags, scope, limit)
        data = self._overpass_request(query, diag)
        if data is None:
            reason = diag.get("http_error")
            diag["error"] = (
                "Overpass API'ye ulasilamadi (tum sunucular denendi). "
                + (f"Sebep: {reason}. " if reason else "")
                + "Birkac dakika sonra tekrar deneyin."
            )
            return [], 0
        if "elements" not in data:
            return [], 0

        elements = data["elements"]
        return self._parse_elements(elements, city, district, sector, limit), len(elements)

    def _overpass_request(self, query: str, diag: dict):
        """Overpass sorgusunu sirayla yedek sunucularda dener; ilk basariliyi doner."""
        last_error = None
        for url in settings.OVERPASS_MIRRORS:
            local: dict = {}
            data = http_post_json(url, data={"data": query}, diag=local)
            if data is not None:
                diag["overpass_server"] = url
                return data
            last_error = local.get("http_error")
        if last_error:
            diag["http_error"] = last_error
        return None

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
