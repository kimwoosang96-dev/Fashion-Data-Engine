from __future__ import annotations

from datetime import datetime, date

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fashion_engine.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    key_prefix: Mapped[str] = mapped_column(String(16), index=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    tier: Mapped[str] = mapped_column(String(20), default="free", nullable=False)
    rpm_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    daily_limit: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    endpoint_scope: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)

    daily_usage: Mapped[list["ApiKeyDailyUsage"]] = relationship(
        back_populates="api_key",
        cascade="all, delete-orphan",
    )


class ApiKeyDailyUsage(Base):
    __tablename__ = "api_key_daily_usage"
    __table_args__ = (
        UniqueConstraint("api_key_id", "usage_date", name="uq_api_key_daily_usage"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id", ondelete="CASCADE"), index=True)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    api_key: Mapped[ApiKey] = relationship(back_populates="daily_usage")
