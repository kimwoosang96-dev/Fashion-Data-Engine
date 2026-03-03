from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fashion_engine.database import Base

if TYPE_CHECKING:
    from fashion_engine.models.brand import Brand
    from fashion_engine.models.channel import Channel
    from fashion_engine.models.product import Product


class IntelEvent(Base):
    __tablename__ = "intel_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    layer: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    event_time: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    confidence: Mapped[str] = mapped_column(String(20), default="medium")

    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"), index=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), index=True)
    product_key: Mapped[str | None] = mapped_column(String(300), index=True)

    geo_country: Mapped[str | None] = mapped_column(String(2))
    geo_city: Mapped[str | None] = mapped_column(String(120))
    geo_lat: Mapped[float | None] = mapped_column(Float)
    geo_lng: Mapped[float | None] = mapped_column(Float)
    geo_precision: Mapped[str] = mapped_column(String(20), default="global")

    source_url: Mapped[str | None] = mapped_column(String(1000))
    source_domain: Mapped[str | None] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(30), default="crawler")

    dedup_key: Mapped[str] = mapped_column(String(400), unique=True, nullable=False)
    details_json: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    brand: Mapped["Brand | None"] = relationship()
    channel: Mapped["Channel | None"] = relationship()
    product: Mapped["Product | None"] = relationship()
    sources: Mapped[list["IntelEventSource"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class IntelIngestRun(Base):
    __tablename__ = "intel_ingest_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False, index=True)
    inserted_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    note: Mapped[str | None] = mapped_column(Text)

    logs: Mapped[list["IntelIngestLog"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    event_sources: Mapped[list["IntelEventSource"]] = relationship(back_populates="run")


class IntelIngestLog(Base):
    __tablename__ = "intel_ingest_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("intel_ingest_runs.id"), index=True, nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source_table: Mapped[str | None] = mapped_column(String(50))
    source_pk: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    run: Mapped["IntelIngestRun"] = relationship(back_populates="logs")


class IntelEventSource(Base):
    __tablename__ = "intel_event_sources"
    __table_args__ = (
        UniqueConstraint("source_table", "source_pk", name="uq_intel_event_sources_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("intel_events.id"), index=True, nullable=False)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("intel_ingest_runs.id"), index=True)
    source_table: Mapped[str] = mapped_column(String(50), nullable=False)
    source_pk: Mapped[int] = mapped_column(Integer, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    source_published_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    event: Mapped["IntelEvent"] = relationship(back_populates="sources")
    run: Mapped["IntelIngestRun | None"] = relationship(back_populates="event_sources")
