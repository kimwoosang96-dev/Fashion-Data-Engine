from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fashion_engine.database import Base

if TYPE_CHECKING:
    from fashion_engine.models.channel import Channel


class ChannelNote(Base):
    """운영자가 채널별로 남기는 피드백/이슈 노트."""

    __tablename__ = "channel_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), index=True)
    # crawl-issue | selector-changed | price-bug | observation | resolved
    note_type: Mapped[str] = mapped_column(String(50), default="observation")
    body: Mapped[str] = mapped_column(Text)
    operator: Mapped[str] = mapped_column(String(100), default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    channel: Mapped["Channel"] = relationship()
