"""
Veritabani baglantisi (SQLAlchemy + SQLite).

SQLite kullaniyoruz: kurulum gerektirmez, tek dosyada saklanir.
Ileride Supabase/PostgreSQL'e gecmek icin sadece DATABASE_URL degistirilir.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

# SQLite tek is parcacigi (thread) kisitini asmak icin check_same_thread=False.
_connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: her istek icin bir veritabani oturumu acar/kapatir."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Tablolari (yoksa) olusturur. Uygulama basladiginda cagrilir."""
    from . import models  # noqa: F401  (modelleri kaydetmek icin import)

    Base.metadata.create_all(bind=engine)
