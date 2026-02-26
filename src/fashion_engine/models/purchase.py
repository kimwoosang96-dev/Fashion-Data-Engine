from datetime import datetime

from sqlalchemy import String, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from fashion_engine.database import Base


class Purchase(Base):
    """구매 이력 — 사용자가 실제 구매한 제품 기록"""

    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_key: Mapped[str] = mapped_column(String(300), index=True)   # "brand-slug:handle"
    product_name: Mapped[str] = mapped_column(String(500))              # 구매 당시 제품명 (스냅샷)
    brand_slug: Mapped[str | None] = mapped_column(String(200))
    channel_name: Mapped[str] = mapped_column(String(200))              # 채널 이름 (텍스트 스냅샷)
    channel_url: Mapped[str | None] = mapped_column(String(1000))
    paid_price_krw: Mapped[int] = mapped_column(Integer, nullable=False) # 실제 지불 금액 (KRW)
    original_price_krw: Mapped[int | None] = mapped_column(Integer)      # 정가 (있을 경우)
    purchased_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str | None] = mapped_column(Text)                      # 메모 (컬러, 사이즈 등)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Purchase {self.product_name} {self.paid_price_krw}KRW>"
