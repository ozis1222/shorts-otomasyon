"""
Web sitesi teknik analiz servisi.

Bir isletmenin web sitesini (varsa) indirir ve tamamen ucretsiz, yerel
yontemlerle teknik sinyalleri cikarir. Hicbir ucretli servise ihtiyac yoktur.

Cikan tum sinyaller WebsiteAnalysis modeline yazilir ve lead puanlamada kullanilir.
Site erisilemezse guvenli varsayilanlarla (bos analiz) doner; sistem cokmez.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from ..config import settings


@dataclass
class AnalysisResult:
    website_exists: bool = False
    website_accessible: bool = False
    status_code: int | None = None
    https_enabled: bool = False
    ssl_ok: bool = False
    mobile_friendly: bool = False
    responsive_signals: bool = False
    load_time: float | None = None
    page_size: int | None = None
    has_title: bool = False
    has_meta_description: bool = False
    has_favicon: bool = False
    has_contact_page: bool = False
    has_phone: bool = False
    has_whatsapp: bool = False
    has_social_links: bool = False
    has_map: bool = False
    has_booking: bool = False
    looks_outdated: bool = False
    outdated_reasons: list[str] = field(default_factory=list)
    technical_score: int = 0
    design_score: int = 0


SOCIAL_DOMAINS = (
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "youtube.com", "tiktok.com",
)
BOOKING_KEYWORDS = (
    "randevu", "rezervasyon", "appointment", "booking", "reservation",
    "calendly", "book now", "online randevu", "hemen ara",
)
CONTACT_KEYWORDS = ("iletisim", "contact", "bize-ulasin", "ulasin")


def analyze_website(url: str | None) -> AnalysisResult:
    result = AnalysisResult()
    if not url or not url.strip():
        return result  # site yok

    result.website_exists = True
    url = _ensure_scheme(url.strip())

    start = time.monotonic()
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": settings.USER_AGENT},
            timeout=settings.WEBSITE_TIMEOUT_SECONDS,
            allow_redirects=True,
        )
        result.load_time = round(time.monotonic() - start, 3)
        result.status_code = resp.status_code
        result.website_accessible = resp.status_code < 400
        final_url = str(resp.url)
        result.https_enabled = final_url.lower().startswith("https://")
        result.ssl_ok = result.https_enabled  # basarili istek + https => SSL sorunsuz
        content = resp.text or ""
        result.page_size = len(resp.content or b"")
    except requests.exceptions.SSLError:
        # HTTPS var ama sertifika hatali -> SSL problemi.
        result.load_time = round(time.monotonic() - start, 3)
        result.https_enabled = url.lower().startswith("https://")
        result.ssl_ok = False
        result.website_accessible = False
        return _finalize(result)
    except Exception:
        result.load_time = round(time.monotonic() - start, 3)
        result.website_accessible = False
        return _finalize(result)

    if not result.website_accessible:
        return _finalize(result)

    _analyze_html(content, final_url, result)
    return _finalize(result)


def _analyze_html(html: str, base_url: str, result: AnalysisResult) -> None:
    soup = BeautifulSoup(html, "html.parser")
    lower = html.lower()

    # Baslik & meta description
    title = soup.title.string if soup.title and soup.title.string else None
    result.has_title = bool(title and title.strip())
    meta_desc = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    result.has_meta_description = bool(
        meta_desc and meta_desc.get("content", "").strip()
    )

    # Mobil viewport
    viewport = soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)})
    result.mobile_friendly = bool(viewport)

    # Responsive sinyaller: viewport + media query veya responsive framework izleri
    responsive = bool(viewport) and (
        "@media" in lower
        or "col-" in lower
        or "container" in lower
        or "flex" in lower
        or "grid" in lower
    )
    result.responsive_signals = responsive

    # Favicon
    icon = soup.find("link", rel=lambda v: v and "icon" in v.lower())
    result.has_favicon = bool(icon)

    # Iletisim sayfasi baglantisi
    result.has_contact_page = _has_link_matching(soup, CONTACT_KEYWORDS)

    # Telefon (tel: baglantisi veya metinde numara deseni)
    result.has_phone = bool(soup.find("a", href=re.compile(r"^tel:", re.I))) or bool(
        re.search(r"(\+?90[\s\-]?)?0?5\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}", html)
    )

    # WhatsApp
    result.has_whatsapp = bool(
        re.search(r"(wa\.me|api\.whatsapp\.com|whatsapp://)", lower)
    )

    # Harita entegrasyonu
    result.has_map = bool(
        re.search(r"(google\.com/maps|maps\.google|goo\.gl/maps|openstreetmap|yandex\.com/maps)", lower)
    ) or bool(soup.find("iframe", src=re.compile(r"maps", re.I)))

    # Sosyal medya baglantilari
    result.has_social_links = any(dom in lower for dom in SOCIAL_DOMAINS)

    # Online randevu / rezervasyon
    result.has_booking = any(k in lower for k in BOOKING_KEYWORDS)

    # Eskimislik sinyalleri
    _detect_outdated(soup, lower, result)


def _detect_outdated(soup, lower: str, result: AnalysisResult) -> None:
    reasons: list[str] = []

    if not soup.find(re.compile("^!doctype", re.I)) and "<!doctype html>" not in lower:
        reasons.append("Modern <!DOCTYPE html> bildirimi yok")
    if not result.mobile_friendly:
        reasons.append("Mobil viewport etiketi yok")
    if soup.find_all("font"):
        reasons.append("Eski <font> etiketleri kullanilmis")
    if soup.find_all("marquee") or soup.find_all("blink"):
        reasons.append("Cok eski <marquee>/<blink> etiketleri var")
    # Tablo ile sayfa duzeni (layout table) klasik eskimis isaretidir.
    tables = soup.find_all("table")
    if len(tables) >= 3 and not result.responsive_signals:
        reasons.append("Tablo tabanli sayfa duzeni (eski yontem)")
    if 'bgcolor="' in lower or "<center" in lower:
        reasons.append("Eski HTML bicimlendirme (bgcolor/center) kullanilmis")
    if "jquery-1." in lower or "jquery/1." in lower:
        reasons.append("Cok eski jQuery 1.x surumu")

    result.outdated_reasons = reasons
    # Iki veya daha fazla guclu sinyal varsa "eski" say.
    result.looks_outdated = len(reasons) >= 2


def _finalize(result: AnalysisResult) -> AnalysisResult:
    result.technical_score = _technical_score(result)
    result.design_score = _design_score(result)
    return result


def _technical_score(r: AnalysisResult) -> int:
    """0-100: sitenin teknik saglik puani (yuksek = iyi)."""
    if not r.website_exists:
        return 0
    if not r.website_accessible:
        return 5
    score = 0
    score += 20 if r.https_enabled and r.ssl_ok else 0
    score += 20 if r.mobile_friendly else 0
    score += 15 if r.responsive_signals else 0
    score += 10 if (r.load_time or 99) < settings.SLOW_THRESHOLD_SECONDS else 0
    score += 10 if r.has_title else 0
    score += 10 if r.has_meta_description else 0
    score += 5 if r.has_favicon else 0
    score += 10 if not r.looks_outdated else 0
    return min(100, score)


def _design_score(r: AnalysisResult) -> int:
    """0-100: kaba tasarim/olgunluk puani (ucretsiz sinyallerden)."""
    if not r.website_accessible:
        return 0
    score = 30  # erisilebilir taban
    score += 15 if r.mobile_friendly else 0
    score += 15 if r.responsive_signals else 0
    score += 10 if r.has_social_links else 0
    score += 10 if r.has_map else 0
    score += 10 if r.has_booking else 0
    score += 10 if r.has_contact_page else 0
    score -= 20 if r.looks_outdated else 0
    return max(0, min(100, score))


def _has_link_matching(soup, keywords) -> bool:
    for a in soup.find_all("a"):
        href = (a.get("href") or "").lower()
        text = (a.get_text() or "").lower()
        if any(k in href or k in text for k in keywords):
            return True
    return False


def _ensure_scheme(url: str) -> str:
    if not urlparse(url).scheme:
        return "http://" + url
    return url
