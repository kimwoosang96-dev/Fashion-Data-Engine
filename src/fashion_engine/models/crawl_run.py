from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fashion_engine.database import Base

if TYPE_CHECKING:
    from fashion_engine.models.channel import Channel


class CrawlRun(Base):
    """크롤 실행 단위 — 전체 크롤 세션 하나를 나타냄"""

    __tablename__ = "crawl_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running/done/failed
    total_channels: Mapped[int] = mapped_column(Integer, default=0)
    done_channels: Mapped[int] = mapped_column(Integer, default=0)
    new_products: Mapped[int] = mapped_column(Integer, default=0)
    updated_products: Mapped[int] = mapped_column(Integer, default=0)
    error_channels: Mapped[int] = mapped_column(Integer, default=0)

    logs: Mapped[list["CrawlChannelLog"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class CrawlChannelLog(Base):
    """채널별 크롤 결과 — 채널 하나당 하나의 레코드"""

    __tablename__ = "crawl_channel_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("crawl_runs.id"), index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))  # success/failed/skipped
    products_found: Mapped[int] = mapped_column(Integer, default=0)
    products_new: Mapped[int] = mapped_column(Integer, default=0)
    products_updated: Mapped[int] = mapped_column(Integer, default=0)
    error_msg: Mapped[str | None] = mapped_column(String(500), nullable=True)
    strategy: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    crawled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped["CrawlRun"] = relationship(back_populates="logs")
    channel: Mapped["Channel"] = relationship()
