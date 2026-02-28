#!/usr/bin/env python3
"""
SQLite 시드 데이터를 PostgreSQL로 이전하는 스크립트.

기본 전략:
- brands/channels/channel_brands/brand_collaborations 등 시드 테이블만 이전
- products/price_history/drops/purchases/watchlist 는 이전하지 않음 (재크롤/재수집 대상)
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from fashion_engine.config import settings
from fashion_engine.models.brand import Brand
from fashion_engine.models.brand_collaboration import BrandCollaboration
from fashion_engine.models.brand_director import BrandDirector
from fashion_engine.models.category import Category
from fashion_engine.models.channel import Channel
from fashion_engine.models.channel_brand import ChannelBrand
from fashion_engine.models.exchange_rate import ExchangeRate


SEED_MODELS = [
    Category,
    Brand,
    Channel,
    ChannelBrand,
    BrandCollaboration,
    BrandDirector,
    ExchangeRate,
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SQLite -> PostgreSQL 시드 데이터 이전")
    parser.add_argument(
        "--source-url",
        default="sqlite+aiosqlite:///./data/fashion.db",
        help="소스 DB URL (기본: sqlite+aiosqlite:///./data/fashion.db)",
    )
    parser.add_argument(
        "--target-url",
        default="",
        help="타깃 DB URL (postgresql+asyncpg://...)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 쓰기 없이 대상 테이블별 카운트만 출력",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="배치 업서트 크기 (기본 1000)",
    )
    return parser.parse_args()


def model_columns(model: type[Any]) -> list[str]:
    return [col.name for col in model.__table__.columns]


def rows_to_dicts(items: list[Any], cols: list[str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in items:
        row: dict[str, Any] = {}
        for col in cols:
            row[col] = getattr(item, col)
        result.append(row)
    return result


async def read_source_counts(source_session: AsyncSession) -> dict[str, int]:
    counts: dict[str, int] = {}
    for model in SEED_MODELS:
        rows = (await source_session.execute(select(model))).scalars().all()
        counts[model.__tablename__] = len(rows)
    return counts


async def copy_model_rows(
    source_session: AsyncSession,
    target_session: AsyncSession,
    model: type[Any],
    batch_size: int,
) -> int:
    cols = model_columns(model)
    rows = (await source_session.execute(select(model))).scalars().all()
    payload = rows_to_dicts(rows, cols)
    if not payload:
        return 0

    table = model.__table__
    pk_cols = [col.name for col in table.primary_key.columns]
    non_pk_cols = [name for name in cols if name not in pk_cols]

    for i in range(0, len(payload), batch_size):
        batch = payload[i : i + batch_size]
        stmt = pg_insert(table).values(batch)
        if non_pk_cols:
            update_map = {name: getattr(stmt.excluded, name) for name in non_pk_cols}
            stmt = stmt.on_conflict_do_update(index_elements=pk_cols, set_=update_map)
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=pk_cols)
        await target_session.execute(stmt)

    return len(payload)


async def fix_postgres_sequences(target_session: AsyncSession) -> None:
    # id PK를 명시값으로 적재했으므로 sequence를 MAX(id)에 맞춤
    table_names = [
        "categories",
        "brands",
        "channels",
        "brand_collaborations",
        "brand_directors",
        "exchange_rates",
    ]
    for table_name in table_names:
        await target_session.execute(
            text(
                """
                SELECT setval(
                  pg_get_serial_sequence(:table_name, 'id'),
                  COALESCE((SELECT MAX(id) FROM """ + table_name + """), 1),
                  (SELECT COUNT(*) > 0 FROM """ + table_name + """)
                )
                """
            ),
            {"table_name": table_name},
        )


async def main() -> int:
    args = parse_args()
    source_url = args.source_url or settings.database_url
    target_url = args.target_url.strip()

    if args.dry_run:
        source_engine = create_async_engine(source_url, echo=False)
        source_sessionmaker = async_sessionmaker(source_engine, class_=AsyncSession, expire_on_commit=False)
        async with source_sessionmaker() as source_session:
            counts = await read_source_counts(source_session)
            print("[DRY-RUN] SQLite -> PostgreSQL 시드 이전 대상")
            for table_name, count in counts.items():
                print(f"- {table_name}: {count}")
            print("- skipped: products, price_history, purchases, watchlist, drops, fashion_news")
        await source_engine.dispose()
        return 0

    if not target_url:
        print("오류: --target-url 이 필요합니다. (예: postgresql+asyncpg://...)")
        return 1
    if not target_url.startswith("postgresql+asyncpg://"):
        print("오류: --target-url 은 postgresql+asyncpg:// 형식이어야 합니다.")
        return 1

    source_engine = create_async_engine(source_url, echo=False)
    target_engine = create_async_engine(target_url, echo=False)
    source_sessionmaker = async_sessionmaker(source_engine, class_=AsyncSession, expire_on_commit=False)
    target_sessionmaker = async_sessionmaker(target_engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with source_sessionmaker() as source_session, target_sessionmaker() as target_session:
            copied: dict[str, int] = {}
            for model in SEED_MODELS:
                table_name = model.__tablename__
                copied[table_name] = await copy_model_rows(
                    source_session=source_session,
                    target_session=target_session,
                    model=model,
                    batch_size=args.batch_size,
                )
                print(f"[OK] {table_name}: {copied[table_name]} rows")

            await fix_postgres_sequences(target_session)
            await target_session.commit()

            print("[DONE] 시드 데이터 이전 완료")
            print("참고: products/price_history/drops/purchases/watchlist/fashion_news 는 재크롤/재수집 대상")
    finally:
        await source_engine.dispose()
        await target_engine.dispose()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
