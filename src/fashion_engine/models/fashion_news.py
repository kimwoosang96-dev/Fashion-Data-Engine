from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from fashion_engine.database import Base


class FashionNews(Base):
    """브랜드·채널 관련 뉴스 및 업데이트"""

    __tablename__ = "fashion_news"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)              # 'brand' | 'channel'
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)                   # brands.id 또는 channels.id
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    source: Mapped[str] = mapped_column(String(50), nullable=False)                   # 'instagram' | 'website' | 'press' | 'youtube'
    crawled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<FashionNews {self.entity_type}:{self.entity_id} — {self.title[:40]}>"
