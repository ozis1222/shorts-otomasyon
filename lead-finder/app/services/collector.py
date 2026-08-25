"""
Toplama servisi (orkestrasyon).

Ana is akisi:
  1. Aktif provider'lardan isletmeleri bul.
  2. Telefonu normalize et, kaydet (duplicate'leri atla).
  3. Web sitesini analiz et.
  4. Lead puanini hesapla ve kaydet.

Bu servis panelin "Ara" butonundan cagrilir ve ozet dondurur.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Business, Lead, WebsiteAnalysis
from ..phone import normalize_tr_phone
from ..providers.base import RawBusiness, resolve_sector_tags
from ..providers.registry import get_providers
from ..scoring import compute_lead_score
from .website_analyzer import AnalysisResult, analyze_website


@dataclass
class CollectSummary:
    requested: int
    found: int = 0
    new_businesses: int = 0
    duplicates: int = 0
    analyzed: int = 0
    error: str | None = None
    # Teshis: sistemin konumu nasil anladigini ve neyi taradigini gosterir.
    resolved_area: str | None = None
    scope: str | None = None
    provider_note: str | None = None


def run_collection(
    db: Session, city: str, district: str, sector: str, limit: int
) -> CollectSummary:
    limit = max(1, min(limit, 500))
    summary = CollectSummary(requested=limit)

    if not resolve_sector_tags(sector):
        summary.error = (
            f"'{sector}' sektoru henuz taninmiyor. "
            "Desteklenen sektorler: dis klinigi, guzellik merkezi, restoran, "
            "kuafor, emlak, oto servis, cafe, otel, eczane, veteriner, spor salonu."
        )
        return summary

    raw_items: list[RawBusiness] = []
    for provider in get_providers():
        remaining = limit - len(raw_items)
        if remaining <= 0:
            break
        try:
            raw_items.extend(provider.search(city, district, sector, remaining))
        except Exception as exc:
            # Bir kaynak patlarsa digerleriyle devam et; teshis notu birak.
            summary.provider_note = f"Kaynak hatasi: {type(exc).__name__}: {exc}"
            continue
        # Provider teshis bilgisini ozete tasi (konum/kapsam/hata).
        diag = getattr(provider, "last_diagnostics", None)
        if diag:
            summary.resolved_area = diag.get("area") or summary.resolved_area
            summary.scope = diag.get("scope") or summary.scope
            if diag.get("error"):
                summary.provider_note = diag["error"]

    summary.found = len(raw_items)

    for raw in raw_items:
        business, is_new = _upsert_business(db, raw)
        if is_new:
            summary.new_businesses += 1
        else:
            summary.duplicates += 1

        analysis = analyze_website(business.website)
        _save_analysis(db, business, analysis)
        _save_lead(db, business)
        summary.analyzed += 1

    db.commit()
    return summary


def _upsert_business(db: Session, raw: RawBusiness) -> tuple[Business, bool]:
    """Kaynak + kaynak kimligine gore mevcut kayidi bulur; yoksa olusturur.
    Duplicate detection burada yapilir."""
    existing = db.execute(
        select(Business).where(
            Business.source == raw.source,
            Business.source_ref == raw.source_ref,
        )
    ).scalar_one_or_none()

    phone = normalize_tr_phone(raw.phone)

    if existing:
        # Bilgileri tazele (eksikse doldur).
        existing.name = raw.name or existing.name
        existing.phone = phone or existing.phone
        existing.website = raw.website or existing.website
        existing.email = raw.email or existing.email
        existing.address = raw.address or existing.address
        existing.opening_hours = raw.opening_hours or existing.opening_hours
        return existing, False

    business = Business(
        name=raw.name,
        category=raw.category,
        sector=raw.sector,
        phone=phone,
        email=raw.email,
        website=raw.website,
        address=raw.address,
        city=raw.city,
        district=raw.district,
        latitude=raw.latitude,
        longitude=raw.longitude,
        description=raw.description,
        opening_hours=raw.opening_hours,
        source=raw.source,
        source_ref=raw.source_ref,
        source_url=raw.source_url,
    )
    db.add(business)
    db.flush()  # id almak icin
    return business, True


def _save_analysis(
    db: Session, business: Business, result: AnalysisResult
) -> None:
    analysis = business.analysis or WebsiteAnalysis(business_id=business.id)
    analysis.website_exists = result.website_exists
    analysis.website_accessible = result.website_accessible
    analysis.status_code = result.status_code
    analysis.https_enabled = result.https_enabled
    analysis.ssl_ok = result.ssl_ok
    analysis.mobile_friendly = result.mobile_friendly
    analysis.responsive_signals = result.responsive_signals
    analysis.load_time = result.load_time
    analysis.page_size = result.page_size
    analysis.has_title = result.has_title
    analysis.has_meta_description = result.has_meta_description
    analysis.has_favicon = result.has_favicon
    analysis.has_contact_page = result.has_contact_page
    analysis.has_phone = result.has_phone
    analysis.has_whatsapp = result.has_whatsapp
    analysis.has_social_links = result.has_social_links
    analysis.has_map = result.has_map
    analysis.has_booking = result.has_booking
    analysis.looks_outdated = result.looks_outdated
    analysis.outdated_reasons = "\n".join(result.outdated_reasons) or None
    analysis.technical_score = result.technical_score
    analysis.design_score = result.design_score
    if business.analysis is None:
        db.add(analysis)
        business.analysis = analysis


def _save_lead(db: Session, business: Business) -> None:
    score = compute_lead_score(business, business.analysis)
    lead = business.lead
    if lead is None:
        lead = Lead(business_id=business.id, crm_status="NEW")
        db.add(lead)
        business.lead = lead
    lead.lead_score = score.score
    lead.lead_level = score.level
    lead.lead_reasons = "\n".join(score.reasons)


def reanalyze_business(db: Session, business: Business) -> None:
    """Tek bir isletmeyi yeniden analiz eder ve puanini gunceller."""
    result = analyze_website(business.website)
    _save_analysis(db, business, result)
    _save_lead(db, business)
    db.commit()
