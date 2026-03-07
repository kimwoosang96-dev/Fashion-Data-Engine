"""
price_history 월별 파티션 관리 스크립트.

기본 동작:
- PostgreSQL인 경우 다음 해 파티션 12개를 idempotent하게 생성
- 2028년 이전 환경에서는 2028년 파티션도 함께 생성해 만료를 선제 방지
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal  # noqa: E402


def resolve_target_years(explicit_years: list[int] | None = None) -> list[int]:
    if explicit_years:
        return sorted(set(explicit_years))

    current_year = datetime.now().year
    years = {current_year + 1}
    if current_year < 2028:
        years.add(2028)
    return sorted(years)


async def ensure_price_history_partitions(years: list[int]) -> int:
    created = 0
    async with AsyncSessionLocal() as session:
        bind = session.get_bind()
        if bind.dialect.name != "postgresql":
            print("skip: DATABASE_URL is not PostgreSQL")
            return 0

        for year in years:
            for month in range(1, 13):
                start = f"{year}-{month:02d}-01"
                if month == 12:
                    end = f"{year + 1}-01-01"
                else:
                    end = f"{year}-{month + 1:02d}-01"
                partition_name = f"price_history_{year}_{month:02d}"
                await session.execute(
                    text(
                        f"""
                        CREATE TABLE IF NOT EXISTS {partition_name}
                        PARTITION OF price_history
                        FOR VALUES FROM ('{start}') TO ('{end}')
                        """
                    )
                )
                created += 1

        await session.commit()

    print(f"ensured partitions: {created} ({', '.join(str(year) for year in years)})")
    return created


async def main(years: list[int]) -> int:
    return await ensure_price_history_partitions(resolve_target_years(years))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ensure future price_history monthly partitions")
    parser.add_argument(
        "--year",
        dest="years",
        action="append",
        type=int,
        help="생성 대상 연도. 여러 번 지정 가능. 생략 시 다음 해(+ 필요 시 2028)를 생성합니다.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.years or []))
