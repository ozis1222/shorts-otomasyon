"""Demo site olusturma ve gosterme."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Business, DemoSite
from ..services.demo import build_demo_context, create_or_update_demo
from ..templating import templates

router = APIRouter()


@router.post("/business/{business_id}/demo")
def make_demo(business_id: int, request: Request, db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(404, "Isletme bulunamadi")
    base_url = str(request.base_url).rstrip("/")
    create_or_update_demo(db, business, base_url)
    return RedirectResponse(f"/business/{business_id}", status_code=303)


@router.get("/demo/{slug}")
def view_demo(slug: str, request: Request, db: Session = Depends(get_db)):
    demo = db.execute(
        select(DemoSite).where(DemoSite.demo_slug == slug)
    ).scalar_one_or_none()
    if not demo:
        raise HTTPException(404, "Demo bulunamadi")
    business = db.get(Business, demo.business_id)
    ctx = build_demo_context(business)
    ctx["request"] = request
    return templates.TemplateResponse(f"demo/{demo.template_type}.html", ctx)
