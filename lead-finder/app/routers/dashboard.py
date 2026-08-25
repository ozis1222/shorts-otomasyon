"""Ana panel (dashboard) ve bugun takip edilecekler."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Business, Lead, WebsiteAnalysis
from ..services.ai import ai_status
from ..templating import templates

router = APIRouter()


@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(Business.id))) or 0

    # Web sitesi olmayan isletmeler
    no_website = db.scalar(
        select(func.count(Business.id)).where(
            (Business.website.is_(None)) | (Business.website == "")
        )
    ) or 0

    hot = db.scalar(select(func.count(Lead.id)).where(Lead.lead_level == "HOT")) or 0
    warm = db.scalar(select(func.count(Lead.id)).where(Lead.lead_level == "WARM")) or 0

    week_ago = date.today() - timedelta(days=7)
    this_week = db.scalar(
        select(func.count(Business.id)).where(Business.created_at >= week_ago)
    ) or 0

    # En iyi lead'ler (ilk 10)
    top_leads = db.execute(
        select(Business).join(Lead).order_by(Lead.lead_score.desc()).limit(10)
    ).scalars().all()

    # Bugun ve gecmis takipler
    today = date.today()
    follow_ups = db.execute(
        select(Business)
        .join(Lead)
        .where(Lead.follow_up_date.is_not(None), Lead.follow_up_date <= today)
        .order_by(Lead.follow_up_date.asc())
    ).scalars().all()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": {
                "total": total,
                "no_website": no_website,
                "hot": hot,
                "warm": warm,
                "this_week": this_week,
            },
            "top_leads": top_leads,
            "follow_ups": follow_ups,
            "today": today,
            "ai_status": ai_status(),
        },
    )
