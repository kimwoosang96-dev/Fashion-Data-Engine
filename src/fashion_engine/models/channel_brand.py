from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fashion_engine.database import Base

if TYPE_CHECKING:
    from fashion_engine.models.channel import Channel
    from fashion_engine.models.brand import Brand


class ChannelBrand(Base):
    """채널-브랜드 N:M 관계 (어느 채널이 어느 브랜드를 취급하는지)"""

    __tablename__ = "channel_brands"

    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), primary_key=True)
    crawled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    channel: Mapped["Channel"] = relationship(back_populates="channel_brands")
    brand: Mapped["Brand"] = relationship(back_populates="channel_brands")
