from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fashion_engine.database import Base

if TYPE_CHECKING:
    from fashion_engine.models.brand import Brand
    from fashion_engine.models.channel import Channel
    from fashion_engine.models.product import Product


class ActivityFeed(Base):
    __tablename__ = "activity_feed"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), index=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id"), index=True)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"), index=True)
    product_name: Mapped[str | None] = mapped_column(String(500))
    price_krw: Mapped[int | None] = mapped_column(Integer)
    discount_rate: Mapped[int | None] = mapped_column(Integer)
    source_url: Mapped[str | None] = mapped_column(String(2000))
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)

    product: Mapped["Product | None"] = relationship()
    channel: Mapped["Channel | None"] = relationship()
    brand: Mapped["Brand | None"] = relationship()

    def __repr__(self) -> str:
        return f"<ActivityFeed {self.event_type} product={self.product_id}>"
