from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fashion_engine.database import Base

if TYPE_CHECKING:
    from fashion_engine.models.channel_brand import ChannelBrand


class Brand(Base):
    """패션 브랜드"""

    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)      # URL 친화적 식별자
    name_ko: Mapped[str | None] = mapped_column(String(255))                         # 한글 브랜드명
    origin_country: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    description_ko: Mapped[str | None] = mapped_column(Text)                         # 한국어 소개 (수동 큐레이션)
    official_url: Mapped[str | None] = mapped_column(String(500))
    instagram_url: Mapped[str | None] = mapped_column(String(500))
    tier: Mapped[str | None] = mapped_column(String(20))                              # high-end | premium | street | sports | spa
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    channel_brands: Mapped[list["ChannelBrand"]] = relationship(back_populates="brand", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Brand {self.name} ({self.slug})>"
