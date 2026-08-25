"""
Uygulama yapilandirmasi.

Tum ayarlar .env dosyasindan okunur. .env yoksa makul varsayimlar kullanilir,
boylece sistem hicbir yapilandirma yapilmadan da calisir.

Lead puanlama agirliklari da burada tanimlidir ve serbestce degistirilebilir.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Proje kokundeki .env dosyasini yukle (varsa).
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _get(key: str, default: str) -> str:
    value = os.getenv(key)
    return value if value not in (None, "") else default


def _get_float(key: str, default: float) -> float:
    try:
        return float(_get(key, str(default)))
    except (TypeError, ValueError):
        return default


class Settings:
    # --- Veritabani ---
    DATABASE_URL: str = _get("DATABASE_URL", "sqlite:///./lead_finder.db")

    # --- Uygulama ---
    APP_HOST: str = _get("APP_HOST", "127.0.0.1")
    APP_PORT: int = int(_get_float("APP_PORT", 8000))

    # --- Veri toplama ---
    OVERPASS_URL: str = _get("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
    NOMINATIM_URL: str = _get("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
    REQUEST_DELAY_SECONDS: float = _get_float("REQUEST_DELAY_SECONDS", 1.0)
    USER_AGENT: str = _get(
        "USER_AGENT", "LeadFinderMVP/1.0 (contact: example@example.com)"
    )

    # --- Web sitesi analizi ---
    WEBSITE_TIMEOUT_SECONDS: float = _get_float("WEBSITE_TIMEOUT_SECONDS", 12.0)
    SLOW_THRESHOLD_SECONDS: float = _get_float("SLOW_THRESHOLD_SECONDS", 3.0)

    # --- Yapay zeka (opsiyonel) ---
    AI_MODE: str = _get("AI_MODE", "none").lower().strip()
    OLLAMA_URL: str = _get("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = _get("OLLAMA_MODEL", "llama3.1")
    ANTHROPIC_API_KEY: str = _get("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = _get("CLAUDE_MODEL", "claude-sonnet-5")


settings = Settings()


# ============================================================
#  LEAD PUANLAMA YAPILANDIRMASI
#  Buradaki agirliklari degistirerek puanlamayi ozellestirebilirsiniz.
#  Her kural belirli bir kosul saglandiginda ilgili puani ekler.
#  Toplam ham puan daha sonra 0-100 arasina normalize edilir.
# ============================================================
SCORING_WEIGHTS: dict[str, int] = {
    "no_website": 40,          # Web sitesi yok
    "no_https": 10,            # HTTPS yok
    "not_mobile_friendly": 15, # Mobil uyumlu degil
    "slow_site": 10,           # Site cok yavas
    "outdated_design": 10,     # Modasi gecmis / eski HTML yapisi
    "missing_meta": 5,         # Meta etiketleri (title/description) eksik
    "poor_contact": 5,         # Iletisim bilgileri eksik/zayif
    "no_booking": 5,           # Online randevu / rezervasyon yok
}

# Ham puanin normalize edilecegi GERCEKCI maksimum.
# Onemli: bazi kurallar ayni anda gerceklesemez (ornek: bir site hem "yok"
# hem "yavas" olamaz). Bu yuzden teorik toplam (tum agirliklarin toplami)
# yerine, gercekte ulasilabilecek en yuksek iki senaryonun buyugunu kullaniriz:
#
#   1) Web sitesi YOK senaryosu:
#      no_website + no_https + not_mobile_friendly + missing_meta
#      + no_booking + poor_contact
#   2) Web sitesi VAR ama cok kotu senaryosu:
#      no_https + not_mobile_friendly + slow_site + outdated_design
#      + missing_meta + poor_contact + no_booking
#
# Boylece "web sitesi yok" isletmeler dogru sekilde HOT lead olarak siralanir.
_MAX_NO_WEBSITE = (
    SCORING_WEIGHTS["no_website"]
    + SCORING_WEIGHTS["no_https"]
    + SCORING_WEIGHTS["not_mobile_friendly"]
    + SCORING_WEIGHTS["missing_meta"]
    + SCORING_WEIGHTS["no_booking"]
    + SCORING_WEIGHTS["poor_contact"]
)
_MAX_BAD_WEBSITE = sum(SCORING_WEIGHTS.values()) - SCORING_WEIGHTS["no_website"]
SCORING_MAX_RAW: int = max(_MAX_NO_WEBSITE, _MAX_BAD_WEBSITE)  # 80

# Lead seviyeleri (alt sinir dahil).
LEAD_LEVELS = [
    (80, "HOT"),
    (60, "WARM"),
    (40, "POSSIBLE"),
    (0, "LOW"),
]

# Gecerli CRM durumlari.
CRM_STATUSES = [
    "NEW",
    "REVIEWED",
    "CONTACTED",
    "INTERESTED",
    "NEGOTIATING",
    "WON",
    "LOST",
    "NOT_INTERESTED",
]


def score_to_level(score: int) -> str:
    """0-100 arasi puani lead seviyesine cevirir (HOT/WARM/POSSIBLE/LOW)."""
    for threshold, level in LEAD_LEVELS:
        if score >= threshold:
            return level
    return "LOW"
