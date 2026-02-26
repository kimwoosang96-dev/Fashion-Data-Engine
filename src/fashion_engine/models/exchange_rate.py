from datetime import datetime

from sqlalchemy import String, Float, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from fashion_engine.database import Base


class ExchangeRate(Base):
    """통화 환율 (→ KRW 기준)"""

    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("from_currency", "to_currency", name="uq_currency_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    from_currency: Mapped[str] = mapped_column(String(3), nullable=False)  # "USD", "JPY", "EUR", "GBP"
    to_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KRW")
    rate: Mapped[float] = mapped_column(Float, nullable=False)  # 1 from_currency = rate KRW
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ExchangeRate {self.from_currency}→{self.to_currency} @{self.rate}>"
