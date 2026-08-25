"""Lead listesi (filtre/siralama), detay sayfasi ve CRM islemleri."""
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from ..config import CRM_STATUSES
from ..database import get_db
from ..models import Business, Lead
from ..services.ai import analyze_business_with_ai, ai_enabled
from ..services.collector import reanalyze_business
from ..services.messages import build_drafts
from ..templating import templates

router = APIRouter()


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


@router.get("/leads")
def lead_list(
    request: Request,
    db: Session = Depends(get_db),
    sector: str = Query(""),
    city: str = Query(""),
    district: str = Query(""),
    min_score: int = Query(0),
    has_website: str = Query(""),   # "", "yes", "no"
    crm_status: str = Query(""),
    sort: str = Query("score"),     # score | newest | name
):
    stmt = select(Business).join(Lead)

    if sector:
        stmt = stmt.where(Business.sector == sector)
    if city:
        stmt = stmt.where(Business.city == city)
    if district:
        stmt = stmt.where(Business.district == district)
    if min_score:
        stmt = stmt.where(Lead.lead_score >= min_score)
    if crm_status:
        stmt = stmt.where(Lead.crm_status == crm_status)
    if has_website == "yes":
        stmt = stmt.where(Business.website.is_not(None), Business.website != "")
    elif has_website == "no":
        stmt = stmt.where((Business.website.is_(None)) | (Business.website == ""))

    if sort == "newest":
        stmt = stmt.order_by(Business.created_at.desc())
    elif sort == "name":
        stmt = stmt.order_by(Business.name.asc())
    else:
        stmt = stmt.order_by(Lead.lead_score.desc())

    businesses = db.execute(stmt.limit(500)).scalars().all()

    # Filtre secenekleri
    sectors = db.execute(
        select(distinct(Business.sector)).where(Business.sector.is_not(None))
    ).scalars().all()
    cities = db.execute(
        select(distinct(Business.city)).where(Business.city.is_not(None))
    ).scalars().all()
    districts = db.execute(
        select(distinct(Business.district)).where(Business.district.is_not(None))
    ).scalars().all()

    return templates.TemplateResponse(
        "leads.html",
        {
            "request": request,
            "businesses": businesses,
            "sectors": sorted(s for s in sectors if s),
            "cities": sorted(c for c in cities if c),
            "districts": sorted(d for d in districts if d),
            "crm_statuses": CRM_STATUSES,
            "filters": {
                "sector": sector, "city": city, "district": district,
                "min_score": min_score, "has_website": has_website,
                "crm_status": crm_status, "sort": sort,
            },
        },
    )


@router.get("/business/{business_id}")
def business_detail(
    business_id: int, request: Request, db: Session = Depends(get_db)
):
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(404, "Isletme bulunamadi")

    drafts = build_drafts(business, _base_url(request))
    reasons = (business.lead.lead_reasons or "").split("\n") if business.lead else []
    outdated = (
        (business.analysis.outdated_reasons or "").split("\n")
        if business.analysis and business.analysis.outdated_reasons else []
    )

    return templates.TemplateResponse(
        "business_detail.html",
        {
            "request": request,
            "b": business,
            "drafts": drafts,
            "reasons": [r for r in reasons if r.strip()],
            "outdated_reasons": [o for o in outdated if o.strip()],
            "crm_statuses": CRM_STATUSES,
            "ai_enabled": ai_enabled(),
        },
    )


@router.post("/business/{business_id}/crm")
def update_crm(
    business_id: int,
    db: Session = Depends(get_db),
    crm_status: str = Form(...),
    notes: str = Form(""),
    follow_up_date: str = Form(""),
    last_contact_date: str = Form(""),
):
    business = db.get(Business, business_id)
    if not business or not business.lead:
        raise HTTPException(404, "Lead bulunamadi")

    lead = business.lead
    if crm_status in CRM_STATUSES:
        lead.crm_status = crm_status
    lead.notes = notes or None
    lead.follow_up_date = _parse_date(follow_up_date)
    lead.last_contact_date = _parse_date(last_contact_date)
    db.commit()
    return RedirectResponse(f"/business/{business_id}", status_code=303)


@router.post("/business/{business_id}/reanalyze")
def reanalyze(business_id: int, db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(404, "Isletme bulunamadi")
    reanalyze_business(db, business)
    return RedirectResponse(f"/business/{business_id}", status_code=303)


@router.post("/business/{business_id}/ai")
def run_ai(business_id: int, db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(404, "Isletme bulunamadi")
    summary = analyze_business_with_ai(business)
    if summary and business.analysis:
        business.analysis.ai_summary = summary
        db.commit()
    return RedirectResponse(f"/business/{business_id}", status_code=303)


@router.post("/business/{business_id}/delete")
def delete_business(business_id: int, db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if business:
        db.delete(business)
        db.commit()
    return RedirectResponse("/leads", status_code=303)


def _parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
