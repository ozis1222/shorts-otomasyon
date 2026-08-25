"""
Veritabani modelleri (ORM).

Dort ana tablo:
  - businesses         : bulunan isletmeler
  - website_analysis   : her isletmenin web sitesi teknik analizi
  - leads              : lead puani + CRM durumu + notlar
  - demo_sites         : isletmeye ozel demo site kayitlari
"""
from __future__ import annotations

from datetime import datetime, date

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now() -> datetime:
    return datetime.utcnow()


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(255))
    sector: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(64))
    email: Mapped[str | None] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(512))
    address: Mapped[str | None] = mapped_column(String(512))
    city: Mapped[str | None] = mapped_column(String(128))
    district: Mapped[str | None] = mapped_column(String(128))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text)
    opening_hours: Mapped[str | None] = mapped_column(String(512))
    source: Mapped[str | None] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(String(512))
    # Ayni isletmeyi tekrar kaydetmemek icin kaynak+kaynak kimligi benzersiz.
    source_ref: Mapped[str | None] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    analysis: Mapped["WebsiteAnalysis | None"] = relationship(
        back_populates="business",
        uselist=False,
        cascade="all, delete-orphan",
    )
    lead: Mapped["Lead | None"] = relationship(
        back_populates="business",
        uselist=False,
        cascade="all, delete-orphan",
    )
    demo: Mapped["DemoSite | None"] = relationship(
        back_populates="business",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("source", "source_ref", name="uq_source_ref"),
    )


class WebsiteAnalysis(Base):
    __tablename__ = "website_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), unique=True
    )
    website_exists: Mapped[bool] = mapped_column(Boolean, default=False)
    website_accessible: Mapped[bool] = mapped_column(Boolean, default=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    https_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    ssl_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    mobile_friendly: Mapped[bool] = mapped_column(Boolean, default=False)
    responsive_signals: Mapped[bool] = mapped_column(Boolean, default=False)
    load_time: Mapped[float | None] = mapped_column(Float)
    page_size: Mapped[int | None] = mapped_column(Integer)
    has_title: Mapped[bool] = mapped_column(Boolean, default=False)
    has_meta_description: Mapped[bool] = mapped_column(Boolean, default=False)
    has_favicon: Mapped[bool] = mapped_column(Boolean, default=False)
    has_contact_page: Mapped[bool] = mapped_column(Boolean, default=False)
    has_phone: Mapped[bool] = mapped_column(Boolean, default=False)
    has_whatsapp: Mapped[bool] = mapped_column(Boolean, default=False)
    has_social_links: Mapped[bool] = mapped_column(Boolean, default=False)
    has_map: Mapped[bool] = mapped_column(Boolean, default=False)
    has_booking: Mapped[bool] = mapped_column(Boolean, default=False)
    looks_outdated: Mapped[bool] = mapped_column(Boolean, default=False)
    outdated_reasons: Mapped[str | None] = mapped_column(Text)
    technical_score: Mapped[int | None] = mapped_column(Integer)
    design_score: Mapped[int | None] = mapped_column(Integer)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    analysis_date: Mapped[datetime] = mapped_column(DateTime, default=_now)

    business: Mapped["Business"] = relationship(back_populates="analysis")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), unique=True
    )
    lead_score: Mapped[int] = mapped_column(Integer, default=0)
    lead_level: Mapped[str] = mapped_column(String(16), default="LOW")
    lead_reasons: Mapped[str | None] = mapped_column(Text)  # satir satir sebepler
    crm_status: Mapped[str] = mapped_column(String(32), default="NEW")
    notes: Mapped[str | None] = mapped_column(Text)
    follow_up_date: Mapped[date | None] = mapped_column(Date)
    last_contact_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    business: Mapped["Business"] = relationship(back_populates="lead")


class DemoSite(Base):
    __tablename__ = "demo_sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), unique=True
    )
    template_type: Mapped[str] = mapped_column(String(64))
    demo_slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    demo_url: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    business: Mapped["Business"] = relationship(back_populates="demo")
