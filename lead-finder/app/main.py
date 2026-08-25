"""
Lead Finder - FastAPI uygulama giris noktasi.

Tum router'lari baglar, veritabanini hazirlar ve statik dosyalari sunar.
Calistirmak icin: `python run.py` veya `uvicorn app.main:app --reload`.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routers import businesses, dashboard, demo, search

app = FastAPI(title="Lead Finder", docs_url="/api-docs")

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def _startup() -> None:
    init_db()


app.include_router(dashboard.router)
app.include_router(search.router)
app.include_router(businesses.router)
app.include_router(demo.router)
