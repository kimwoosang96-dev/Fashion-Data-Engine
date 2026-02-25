from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fashion_engine.database import Base

if TYPE_CHECKING:
    from fashion_engine.models.brand import Brand


class BrandCollaboration(Base):
    """브랜드 간 협업 기록 및 하입 추적"""

    __tablename__ = "brand_collaborations"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_a_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    brand_b_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    collab_name: Mapped[str] = mapped_column(String(255), nullable=False)             # "Adidas x Wales Bonner SS24"
    collab_category: Mapped[str | None] = mapped_column(String(50))                  # footwear | apparel | accessories | lifestyle
    release_year: Mapped[int | None] = mapped_column(Integer)
    hype_score: Mapped[int] = mapped_column(Integer, default=0)                      # 0-100 (채널 픽업 수 × 10, 상한 100)
    source_url: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    brand_a: Mapped["Brand"] = relationship("Brand", foreign_keys=[brand_a_id])
    brand_b: Mapped["Brand"] = relationship("Brand", foreign_keys=[brand_b_id])

    def __repr__(self) -> str:
        return f"<BrandCollaboration {self.collab_name} (hype={self.hype_score})>"
