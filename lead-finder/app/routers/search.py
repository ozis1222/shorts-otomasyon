"""Isletme arama: form gosterimi ve arama calistirma."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.collector import run_collection
from ..templating import templates

router = APIRouter()

# Panelde onerilecek sektorler (kullanici serbest metin de girebilir).
SUGGESTED_SECTORS = [
    "Dis Klinigi", "Guzellik Merkezi", "Restoran", "Kuafor",
    "Emlak", "Oto Servis", "Cafe", "Otel", "Eczane", "Veteriner", "Spor Salonu",
]


@router.get("/search")
def search_form(request: Request):
    return templates.TemplateResponse(
        "search.html",
        {"request": request, "sectors": SUGGESTED_SECTORS, "summary": None},
    )


@router.post("/search")
def run_search(
    request: Request,
    db: Session = Depends(get_db),
    city: str = Form(...),
    district: str = Form(""),
    sector: str = Form(...),
    max_results: int = Form(50),
):
    summary = run_collection(db, city.strip(), district.strip(), sector.strip(), max_results)
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "sectors": SUGGESTED_SECTORS,
            "summary": summary,
            "form": {"city": city, "district": district, "sector": sector,
                     "max_results": max_results},
        },
    )
