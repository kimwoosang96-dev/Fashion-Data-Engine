from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fashion_engine.database import Base

if TYPE_CHECKING:
    from fashion_engine.models.channel_brand import ChannelBrand


class Channel(Base):
    """판매채널 (편집샵, 브랜드 공식몰 등)"""

    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)       # 홈페이지 URL
    original_url: Mapped[str | None] = mapped_column(String(500))                    # 입력 원본 URL
    channel_type: Mapped[str | None] = mapped_column(String(50))                     # 'brand-store', 'edit-shop', ...
    platform: Mapped[str | None] = mapped_column(String(50))                         # 'shopify' | 'cafe24' | 'custom' | None
    country: Mapped[str | None] = mapped_column(String(50))                          # 'KR', 'US', 'JP', ...
    description: Mapped[str | None] = mapped_column(Text)
    instagram_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    channel_brands: Mapped[list["ChannelBrand"]] = relationship(back_populates="channel", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Channel {self.name} ({self.url})>"
