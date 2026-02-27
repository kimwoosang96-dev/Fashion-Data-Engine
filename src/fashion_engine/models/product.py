from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fashion_engine.database import Base

if TYPE_CHECKING:
    from fashion_engine.models.channel import Channel
    from fashion_engine.models.brand import Brand
    from fashion_engine.models.category import Category
    from fashion_engine.models.price_history import PriceHistory


class Product(Base):
    """상품"""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), nullable=False)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    product_key: Mapped[str | None] = mapped_column(String(300), index=True)  # "brand-slug:handle" 교차 채널 매칭용
    gender: Mapped[str | None] = mapped_column(String(20), index=True)         # men / women / unisex / kids
    subcategory: Mapped[str | None] = mapped_column(String(100), index=True)   # shoes / outer / top / ...
    sku: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1000))
    description: Mapped[str | None] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_new: Mapped[bool] = mapped_column(Boolean, default=False)                     # 신상품 여부
    is_sale: Mapped[bool] = mapped_column(Boolean, default=False)                    # 세일 여부

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    channel: Mapped["Channel"] = relationship()
    brand: Mapped["Brand | None"] = relationship()
    category: Mapped["Category | None"] = relationship(back_populates="products")
    price_history: Mapped[list["PriceHistory"]] = relationship(back_populates="product", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Product {self.name}>"
