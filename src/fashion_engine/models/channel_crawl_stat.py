from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fashion_engine.database import Base

if TYPE_CHECKING:
    from fashion_engine.models.channel import Channel
    from fashion_engine.models.crawl_run import CrawlRun


class ChannelCrawlStat(Base):
    __tablename__ = "channel_crawl_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    crawl_run_id: Mapped[int] = mapped_column(ForeignKey("crawl_runs.id"), index=True, nullable=False)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), index=True, nullable=False)
    products_found: Mapped[int] = mapped_column(Integer, default=0)
    parse_method: Mapped[str | None] = mapped_column(String(30))
    error_msg: Mapped[str | None] = mapped_column(Text)
    crawled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    run: Mapped["CrawlRun"] = relationship()
    channel: Mapped["Channel"] = relationship()
