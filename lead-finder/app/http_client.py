"""
Ortak HTTP istemcisi.

Tum dis isteklerde:
  - Anlamli bir User-Agent gonderir.
  - Istekler arasinda REQUEST_DELAY_SECONDS kadar bekler (rate limit / nezaket).
  - Hatalari yutup guvenli varsayilan dondurur (sistem cokmez).
"""
from __future__ import annotations

import threading
import time
from typing import Any

import requests

from .config import settings

_last_request_ts = 0.0
_lock = threading.Lock()


def _respect_rate_limit() -> None:
    """Global olarak istekler arasi minimum bekleme uygular."""
    global _last_request_ts
    with _lock:
        now = time.monotonic()
        wait = settings.REQUEST_DELAY_SECONDS - (now - _last_request_ts)
        if wait > 0:
            time.sleep(wait)
        _last_request_ts = time.monotonic()


def _headers(extra: dict | None = None) -> dict:
    h = {"User-Agent": settings.USER_AGENT, "Accept-Language": "tr,en;q=0.8"}
    if extra:
        h.update(extra)
    return h


def http_get_json(
    url: str, params: dict | None = None, timeout: float | None = None
) -> Any | None:
    _respect_rate_limit()
    try:
        resp = requests.get(
            url,
            params=params,
            headers=_headers(),
            timeout=timeout or settings.WEBSITE_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def http_post_json(
    url: str, data: dict | None = None, timeout: float | None = None
) -> Any | None:
    _respect_rate_limit()
    try:
        resp = requests.post(
            url,
            data=data,
            headers=_headers(),
            timeout=timeout or 60,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None
