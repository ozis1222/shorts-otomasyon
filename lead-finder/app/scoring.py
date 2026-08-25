"""
Lead puanlama motoru.

Bir isletme + web sitesi analizini alir, config.SCORING_WEIGHTS agirliklarina
gore ham puan hesaplar, 0-100 arasina normalize eder ve insan tarafindan
okunabilir sebepler uretir.

Puanlama tamamen config.py uzerinden ozellestirilebilir.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import SCORING_MAX_RAW, SCORING_WEIGHTS, score_to_level
from .models import Business, WebsiteAnalysis


@dataclass
class ScoreResult:
    score: int
    level: str
    reasons: list[str]


def compute_lead_score(
    business: Business, analysis: WebsiteAnalysis | None
) -> ScoreResult:
    w = SCORING_WEIGHTS
    raw = 0
    reasons: list[str] = []

    has_website = bool(business.website) and (
        analysis.website_exists if analysis else False
    )

    if not has_website:
        # Web sitesi yok -> en guclu sinyal. Ayrica sitesi olmayan bir isletme
        # dogal olarak HTTPS, mobil uyum, meta etiket, online randevu ve online
        # iletisim kanallarindan da yoksundur; bu eksiklikler de puana yansir.
        # Boylece "web sitesi yok" bir HOT lead olarak dogru siralanir.
        raw += w["no_website"]
        raw += w["no_https"]
        raw += w["not_mobile_friendly"]
        raw += w["missing_meta"]
        raw += w["no_booking"]
        reasons.append("Web sitesi yok (yuksek potansiyel)")
        if business.phone:
            reasons.append("Telefon bilgisi mevcut")
        else:
            raw += w["poor_contact"]
            reasons.append("Iletisim bilgileri eksik")
        reasons.append("Online varlik tamamen eksik (HTTPS/mobil/randevu yok)")
        reasons.append("Sektor web sitesi satisina uygun")
    else:
        # Web sitesi var -> teknik zayifliklara gore puanla.
        if not analysis.https_enabled or not analysis.ssl_ok:
            raw += w["no_https"]
            reasons.append("HTTPS / SSL problemi")
        if not analysis.mobile_friendly:
            raw += w["not_mobile_friendly"]
            reasons.append("Mobil uyumluluk zayif")
        if analysis.load_time and analysis.load_time > 0 and _is_slow(analysis):
            raw += w["slow_site"]
            reasons.append("Site cok yavas")
        if analysis.looks_outdated:
            raw += w["outdated_design"]
            reasons.append("Modasi gecmis / eski tasarim")
        if not (analysis.has_title and analysis.has_meta_description):
            raw += w["missing_meta"]
            reasons.append("Meta etiketleri eksik")
        if not _has_good_contact(business, analysis):
            raw += w["poor_contact"]
            reasons.append("Iletisim bilgileri yetersiz")
        if not analysis.has_booking:
            raw += w["no_booking"]
            reasons.append("Online randevu / rezervasyon yok")

        if not reasons:
            reasons.append("Site teknik olarak iyi durumda (dusuk oncelik)")

    score = _normalize(raw)
    return ScoreResult(score=score, level=score_to_level(score), reasons=reasons)


def _is_slow(analysis: WebsiteAnalysis) -> bool:
    from .config import settings

    return (analysis.load_time or 0) >= settings.SLOW_THRESHOLD_SECONDS


def _has_good_contact(business: Business, analysis: WebsiteAnalysis) -> bool:
    # Telefon (isletmede veya sitede) + iletisim sayfasi/haritasi varsa yeterli sayilir.
    has_phone = bool(business.phone) or analysis.has_phone
    has_channel = analysis.has_contact_page or analysis.has_map or analysis.has_whatsapp
    return has_phone and has_channel


def _normalize(raw: int) -> int:
    if SCORING_MAX_RAW <= 0:
        return 0
    score = round(100 * raw / SCORING_MAX_RAW)
    return max(0, min(100, score))
