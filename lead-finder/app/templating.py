"""Paylasilan Jinja2 template motoru ve yardimci filtreler."""
from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _level_color(level: str) -> str:
    return {
        "HOT": "bg-red-100 text-red-700 border-red-200",
        "WARM": "bg-orange-100 text-orange-700 border-orange-200",
        "POSSIBLE": "bg-yellow-100 text-yellow-700 border-yellow-200",
        "LOW": "bg-slate-100 text-slate-600 border-slate-200",
    }.get(level, "bg-slate-100 text-slate-600 border-slate-200")


def _crm_color(status: str) -> str:
    return {
        "NEW": "bg-blue-100 text-blue-700",
        "REVIEWED": "bg-indigo-100 text-indigo-700",
        "CONTACTED": "bg-cyan-100 text-cyan-700",
        "INTERESTED": "bg-emerald-100 text-emerald-700",
        "NEGOTIATING": "bg-amber-100 text-amber-700",
        "WON": "bg-green-100 text-green-700",
        "LOST": "bg-rose-100 text-rose-700",
        "NOT_INTERESTED": "bg-slate-200 text-slate-600",
    }.get(status, "bg-slate-100 text-slate-600")


templates.env.filters["level_color"] = _level_color
templates.env.filters["crm_color"] = _crm_color
