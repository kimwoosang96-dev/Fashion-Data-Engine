from datetime import datetime, date

from sqlalchemy import String, DateTime, Date, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from fashion_engine.database import Base

if TYPE_CHECKING:
    from fashion_engine.models.brand import Brand


class Drop(Base):
    """발매(드롭) 정보 — 예정 발매 및 신제품 발매 이력"""

    __tablename__ = "drops"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"))
    product_name: Mapped[str] = mapped_column(String(500))
    product_key: Mapped[str | None] = mapped_column(String(300), index=True)  # products 테이블 연결용
    source_url: Mapped[str] = mapped_column(String(1000))
    image_url: Mapped[str | None] = mapped_column(String(1000))
    price_krw: Mapped[int | None] = mapped_column(Integer)
    release_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), default="released")  # "upcoming" | "released" | "sold_out"
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime)

    brand: Mapped["Brand | None"] = relationship()

    def __repr__(self) -> str:
        return f"<Drop {self.product_name} [{self.status}]>"
