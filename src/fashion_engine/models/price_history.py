from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, DateTime, Numeric, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fashion_engine.database import Base

if TYPE_CHECKING:
    from fashion_engine.models.product import Product


class PriceHistory(Base):
    """상품 가격 이력 (크롤링 시마다 기록)"""

    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)

    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    original_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))           # 정가 (세일 중일 때)
    currency: Mapped[str] = mapped_column(String(10), default="KRW")
    is_sale: Mapped[bool] = mapped_column(Boolean, default=False)
    discount_rate: Mapped[int | None] = mapped_column()                              # 할인율 (%)

    crawled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped["Product"] = relationship(back_populates="price_history")

    def __repr__(self) -> str:
        return f"<PriceHistory product={self.product_id} price={self.price} {self.currency}>"
