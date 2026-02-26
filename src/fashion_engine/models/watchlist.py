from datetime import datetime

from sqlalchemy import String, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from fashion_engine.database import Base


class WatchListItem(Base):
    """관심 목록 — 알림 필터링용 (브랜드/제품/채널 단위 구독)"""

    __tablename__ = "watchlist"
    __table_args__ = (
        UniqueConstraint("watch_type", "watch_value", name="uq_watchlist_item"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    watch_type: Mapped[str] = mapped_column(String(50))   # "brand" | "product_key" | "channel"
    watch_value: Mapped[str] = mapped_column(String(300)) # brand_slug / product_key / channel_url
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<WatchListItem {self.watch_type}:{self.watch_value}>"
