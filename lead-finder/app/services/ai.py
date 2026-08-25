"""
Opsiyonel yapay zeka katmani.

AI_MODE ile kontrol edilir:
  - none   : AI kapali (varsayilan). Sistem tamamen calisir, hicbir sey cagirilmaz.
  - ollama : Yerel Ollama modeli (ucretsiz). Once "ollama" kurulmalidir.
  - claude : Anthropic Claude API (UCRETLI). API anahtari gerekir.

AI kapali olsa bile proje eksiksiz calisir; bu katman yalnizca ekstra yorum uretir.
"""
from __future__ import annotations

import requests

from ..config import settings
from ..models import Business


def ai_enabled() -> bool:
    return settings.AI_MODE in ("ollama", "claude")


def ai_status() -> str:
    if settings.AI_MODE == "none":
        return "Kapali (AI_MODE=none)"
    if settings.AI_MODE == "ollama":
        return f"Ollama ({settings.OLLAMA_MODEL})"
    if settings.AI_MODE == "claude":
        return "Claude API" + ("" if settings.ANTHROPIC_API_KEY else " (API anahtari eksik!)")
    return f"Bilinmeyen mod: {settings.AI_MODE}"


def analyze_business_with_ai(business: Business) -> str | None:
    """Isletme + analiz ozetinden AI yorumu uretir. AI kapaliysa None."""
    if not ai_enabled():
        return None

    prompt = _build_prompt(business)
    try:
        if settings.AI_MODE == "ollama":
            return _ask_ollama(prompt)
        if settings.AI_MODE == "claude":
            return _ask_claude(prompt)
    except Exception as exc:  # AI hatasi sistemi durdurmasin
        return f"(AI yoruma su an ulasilamadi: {exc})"
    return None


def _build_prompt(business: Business) -> str:
    a = business.analysis
    lead = business.lead
    lines = [
        "Bir web tasarim ajansi icin potansiyel musteri degerlendirmesi yap.",
        "Kisa, net ve Turkce yanit ver. Uydurma bilgi ekleme.",
        "",
        f"Isletme: {business.name}",
        f"Sektor: {business.sector or '-'}",
        f"Sehir/Ilce: {business.city or '-'} / {business.district or '-'}",
        f"Telefon: {business.phone or '-'}",
        f"Web sitesi: {business.website or 'YOK'}",
    ]
    if a:
        lines += [
            f"Site erisilebilir: {a.website_accessible}",
            f"HTTPS: {a.https_enabled}, Mobil uyumlu: {a.mobile_friendly}",
            f"Yuklenme (sn): {a.load_time}, Eski gorunum: {a.looks_outdated}",
            f"Online randevu: {a.has_booking}, Iletisim sayfasi: {a.has_contact_page}",
        ]
    if lead:
        lines += [f"Hesaplanan lead puani: {lead.lead_score}/100 ({lead.lead_level})"]
    lines += [
        "",
        "Su 3 basligi kisa maddelerle ver:",
        "1) Genel web varligi degerlendirmesi",
        "2) Bu isletme neden (veya neden degil) iyi bir potansiyel musteri",
        "3) Bu isletmeye ozel 1-2 somut satis firsati",
    ]
    return "\n".join(lines)


def _ask_ollama(prompt: str) -> str:
    resp = requests.post(
        f"{settings.OLLAMA_URL}/api/generate",
        json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    return (resp.json().get("response") or "").strip()


def _ask_claude(prompt: str) -> str:
    if not settings.ANTHROPIC_API_KEY:
        return "(Claude API anahtari tanimli degil. .env icinde ANTHROPIC_API_KEY ayarlayin.)"
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": settings.CLAUDE_MODEL,
            "max_tokens": 700,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    blocks = data.get("content", [])
    return "".join(b.get("text", "") for b in blocks).strip()
