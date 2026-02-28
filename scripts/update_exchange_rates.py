"""
환율 데이터 업데이트 스크립트 (→ KRW 기준).

사용법:
    uv run python scripts/update_exchange_rates.py

무료 API: https://open.er-api.com/v6/latest/KRW (API 키 불필요)
USD, JPY, EUR, GBP, HKD 및 추가 통화 → KRW 환율을 DB에 저장/갱신.
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import httpx
from rich.console import Console
from rich.table import Table
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from fashion_engine.database import AsyncSessionLocal, init_db
from fashion_engine.models.exchange_rate import ExchangeRate

console = Console()

CURRENCIES = [
    "USD",
    "JPY",
    "EUR",
    "GBP",
    "HKD",
    "DKK",
    "SEK",
    "SGD",
    "CAD",
    "AUD",
    "TWD",
    "CNY",
]
API_URL = "https://open.er-api.com/v6/latest/KRW"


async def fetch_rates() -> dict[str, float]:
    """KRW 기준 환율 조회 → {USD: 0.000735, JPY: 0.1075, ...} 형태로 반환.
    단, DB에는 "1 외화 = X KRW" 형태로 역변환해서 저장.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(API_URL)
        resp.raise_for_status()
        data = resp.json()

    if data.get("result") != "success":
        raise RuntimeError(f"환율 API 오류: {data}")

    rates_from_krw = data["rates"]  # 1 KRW = X 외화
    # 역변환: 1 외화 = (1 / rate) KRW
    return {
        currency: round(1 / rates_from_krw[currency], 4)
        for currency in CURRENCIES
        if currency in rates_from_krw
    }


async def run() -> None:
    console.print("[bold blue]Fashion Data Engine — 환율 업데이트[/bold blue]\n")
    await init_db()

    rates = await fetch_rates()
    fetched_at = datetime.utcnow()

    async with AsyncSessionLocal() as db:
        for currency, rate in rates.items():
            existing = (
                await db.execute(
                    select(ExchangeRate).where(
                        ExchangeRate.from_currency == currency,
                        ExchangeRate.to_currency == "KRW",
                    )
                )
            ).scalar_one_or_none()

            if existing:
                existing.rate = rate
                existing.fetched_at = fetched_at
            else:
                db.add(ExchangeRate(from_currency=currency, to_currency="KRW", rate=rate, fetched_at=fetched_at))

        await db.commit()

    table = Table(title="환율 (→ KRW)")
    table.add_column("통화", style="cyan")
    table.add_column("1 외화 = KRW", justify="right", style="green")
    for currency, rate in sorted(rates.items()):
        table.add_row(currency, f"{rate:,.1f}")
    console.print(table)


if __name__ == "__main__":
    asyncio.run(run())
