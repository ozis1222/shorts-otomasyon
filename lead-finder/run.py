"""
Basit calistirma betigi.

Kullanim:
    python run.py

Tarayicidan http://127.0.0.1:8000 adresini acin.
"""
from __future__ import annotations

import uvicorn

from app.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print("  Lead Finder baslatiliyor...")
    print(f"  Panel: http://{settings.APP_HOST}:{settings.APP_PORT}")
    print(f"  AI modu: {settings.AI_MODE}")
    print("  Durdurmak icin: CTRL + C")
    print("=" * 60)
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=False,
    )
