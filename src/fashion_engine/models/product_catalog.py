from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, DateTime, ForeignKey, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fashion_engine.database import Base

if TYPE_CHECKING:
    from fashion_engine.models.brand import Brand
    from fashion_engine.models.product import Product


class ProductCatalog(Base):
    """
    실세계 제품의 정체성 레이어 (캐노니컬 제품).

    여러 채널에서 판매되는 동일 제품을 하나로 묶는 상위 엔티티.
    기존 Product 테이블은 채널별 판매 목록(Listing)으로 역할을 유지하며,
    ProductCatalog.normalized_key ← Product.normalized_key 기준으로 집계된다.
    """

    __tablename__ = "product_catalog"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 교차채널 정체성 키 (Product.normalized_key 와 동일 포맷)
    normalized_key: Mapped[str] = mapped_column(String(300), unique=True, nullable=False, index=True)

    # 대표 제품 정보
    canonical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"), index=True)
    gender: Mapped[str | None] = mapped_column(String(20), index=True)   # men/women/unisex/kids
    subcategory: Mapped[str | None] = mapped_column(String(100), index=True)  # shoes/outer/top/...
    tags: Mapped[str | None] = mapped_column(Text)  # JSON 스타일/룩 태그

    # 트렌드 메타
    trend_score: Mapped[float | None] = mapped_column(Float, default=None)  # 0~100
    listing_count: Mapped[int] = mapped_column(Integer, default=1)           # 취급 채널 수

    # 가격 통계 (집계 캐시 — 정기적으로 갱신)
    min_price_krw: Mapped[int | None] = mapped_column(Integer)
    max_price_krw: Mapped[int | None] = mapped_column(Integer)
    is_sale_anywhere: Mapped[bool | None] = mapped_column()

    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    brand: Mapped["Brand | None"] = relationship()
    listings: Mapped[list["Product"]] = relationship(
        "Product",
        primaryjoin="foreign(Product.normalized_key) == ProductCatalog.normalized_key",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<ProductCatalog {self.normalized_key}>"
