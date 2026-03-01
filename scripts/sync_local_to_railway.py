#!/usr/bin/env python3
"""
로컬 SQLite products + price_history 를 Railway PostgreSQL로 동기화.

전략:
- products: url 기반 ON CONFLICT DO UPDATE (PK는 Railway 자동 할당)
- price_history: (product_id, crawled_at) 기반 ON CONFLICT DO NOTHING
  → products 이전 후 url→Railway_id 매핑을 통해 FK 재매핑

사용법:
    # dry-run (카운트만 확인)
    uv run python scripts/sync_local_to_railway.py --dry-run

    # 실제 동기화 (Railway URL은 .env의 RAILWAY_DATABASE_URL)
    uv run python scripts/sync_local_to_railway.py \\
        --target-url "postgresql+asyncpg://..."
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from fashion_engine.models.product import Product
from fashion_engine.models.price_history import PriceHistory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="로컬 SQLite → Railway PostgreSQL products 동기화")
    parser.add_argument(
        "--source-url",
        default="sqlite+aiosqlite:///./data/fashion.db",
        help="소스 DB URL (기본: 로컬 SQLite)",
    )
    parser.add_argument(
        "--target-url",
        default="",
        help="타깃 DB URL (postgresql+asyncpg://...)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 쓰기 없이 카운트만 출력",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="배치 업서트 크기 (기본 500)",
    )
    parser.add_argument(
        "--skip-price-history",
        action="store_true",
        help="price_history 동기화 건너뜀 (products만)",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    source_url = args.source_url
    target_url = args.target_url.strip()

    source_engine = create_async_engine(source_url, echo=False)
    source_sm = async_sessionmaker(source_engine, class_=AsyncSession, expire_on_commit=False)

    # ── dry-run ─────────────────────────────────────────────────────────────
    if args.dry_run:
        async with source_sm() as ss:
            product_count = (await ss.execute(text("SELECT COUNT(*) FROM products"))).scalar()
            ph_count = (await ss.execute(text("SELECT COUNT(*) FROM price_history"))).scalar()
        await source_engine.dispose()
        print(f"[DRY-RUN] 소스 로컬 SQLite:")
        print(f"  products     : {product_count:,}")
        print(f"  price_history: {ph_count:,}")
        print("실제 동기화하려면 --target-url 을 지정하세요.")
        return 0

    if not target_url:
        print("오류: --target-url 이 필요합니다.")
        print("예) --target-url \"postgresql+asyncpg://user:pass@host:port/db\"")
        return 1
    if not target_url.startswith("postgresql+asyncpg://"):
        print("오류: --target-url 은 postgresql+asyncpg:// 형식이어야 합니다.")
        return 1

    target_engine = create_async_engine(target_url, echo=False)
    target_sm = async_sessionmaker(target_engine, class_=AsyncSession, expire_on_commit=False)

    # products 컬럼 (id 제외 — Railway가 자동 할당)
    product_cols_no_id = [
        c.name for c in Product.__table__.columns if c.name != "id"
    ]

    try:
        # ── Step 1: SQLite products 읽기 ────────────────────────────────────
        print("▶ products 읽는 중 (로컬 SQLite)...")
        async with source_sm() as ss:
            src_products = (await ss.execute(select(Product))).scalars().all()
        print(f"  {len(src_products):,}개 로드 완료")

        # sqlite_id → url 매핑 (price_history FK 재매핑용)
        sqlite_id_to_url: dict[int, str] = {p.id: p.url for p in src_products}

        # ── Step 2: Railway에서 유효한 brand_id / channel_id 미리 조회 ──────
        print("▶ Railway 유효 FK 조회 중...")
        from fashion_engine.models.brand import Brand
        from fashion_engine.models.channel import Channel
        async with target_sm() as ts:
            valid_brand_ids: set[int] = set(
                (await ts.execute(text("SELECT id FROM brands"))).scalars().all()
            )
            valid_channel_ids: set[int] = set(
                (await ts.execute(text("SELECT id FROM channels"))).scalars().all()
            )
        print(f"  유효 brand_id: {len(valid_brand_ids):,}개, channel_id: {len(valid_channel_ids):,}개")

        # ── Step 3: Railway에 products 배치 upsert ──────────────────────────
        print("▶ products Railway로 업서트 중...")
        product_table = Product.__table__
        batch_size = args.batch_size
        total_products = 0
        nulled_brand = 0

        async with target_sm() as ts:
            for i in range(0, len(src_products), batch_size):
                batch = src_products[i : i + batch_size]
                payload = []
                for p in batch:
                    row = {col: getattr(p, col) for col in product_cols_no_id}
                    # FK 검증: 없는 brand_id → NULL
                    if row.get("brand_id") and row["brand_id"] not in valid_brand_ids:
                        row["brand_id"] = None
                        nulled_brand += 1
                    payload.append(row)
                stmt = pg_insert(product_table).values(payload)
                update_map = {col: getattr(stmt.excluded, col) for col in product_cols_no_id}
                stmt = stmt.on_conflict_do_update(
                    index_elements=["url"],
                    set_=update_map,
                )
                await ts.execute(stmt)
                total_products += len(batch)
                print(f"  {total_products:,}/{len(src_products):,}", end="\r")

            await ts.commit()
            print(f"\n  완료: {total_products:,}개 upsert (brand_id NULL 처리: {nulled_brand}개)")

            # sequence 재설정
            await ts.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence('products', 'id'), "
                    "COALESCE((SELECT MAX(id) FROM products), 1), "
                    "(SELECT COUNT(*) > 0 FROM products))"
                )
            )
            await ts.commit()
            print("  sequence 재설정 완료")

        # ── Step 3: url → Railway product_id 매핑 구축 ──────────────────────
        if not args.skip_price_history:
            print("▶ Railway url → id 매핑 구축 중...")
            async with target_sm() as ts:
                rwy_rows = (
                    await ts.execute(select(Product.id, Product.url))
                ).all()
            url_to_rwy_id: dict[str, int] = {row.url: row.id for row in rwy_rows}
            print(f"  {len(url_to_rwy_id):,}개 제품 매핑 완료")

            # sqlite_product_id → railway_product_id
            sqlite_to_rwy: dict[int, int] = {}
            unmapped = 0
            for sid, url in sqlite_id_to_url.items():
                rwy_id = url_to_rwy_id.get(url)
                if rwy_id:
                    sqlite_to_rwy[sid] = rwy_id
                else:
                    unmapped += 1
            if unmapped:
                print(f"  ⚠ 매핑 실패 product: {unmapped}개 (price_history에서 제외됨)")

            # ── Step 4: SQLite price_history 읽기 ───────────────────────────
            print("▶ price_history 읽는 중 (로컬 SQLite)...")
            async with source_sm() as ss:
                src_ph = (await ss.execute(select(PriceHistory))).scalars().all()
            print(f"  {len(src_ph):,}개 로드 완료")

            # ── Step 5: price_history Railway로 배치 upsert ─────────────────
            print("▶ price_history Railway로 업서트 중...")
            ph_table = PriceHistory.__table__
            ph_cols_no_id = [c.name for c in ph_table.columns if c.name != "id"]
            total_ph = 0
            skipped_ph = 0

            async with target_sm() as ts:
                buffer: list[dict] = []

                for ph in src_ph:
                    rwy_pid = sqlite_to_rwy.get(ph.product_id)
                    if not rwy_pid:
                        skipped_ph += 1
                        continue
                    row = {col: getattr(ph, col) for col in ph_cols_no_id}
                    row["product_id"] = rwy_pid
                    buffer.append(row)

                    if len(buffer) >= batch_size:
                        stmt = pg_insert(ph_table).values(buffer)
                        stmt = stmt.on_conflict_do_nothing()
                        await ts.execute(stmt)
                        total_ph += len(buffer)
                        print(f"  {total_ph:,}/{len(src_ph):,}", end="\r")
                        buffer = []

                if buffer:
                    stmt = pg_insert(ph_table).values(buffer)
                    stmt = stmt.on_conflict_do_nothing()
                    await ts.execute(stmt)
                    total_ph += len(buffer)

                await ts.commit()

                # sequence 재설정
                await ts.execute(
                    text(
                        "SELECT setval(pg_get_serial_sequence('price_history', 'id'), "
                        "COALESCE((SELECT MAX(id) FROM price_history), 1), "
                        "(SELECT COUNT(*) > 0 FROM price_history))"
                    )
                )
                await ts.commit()

            print(f"\n  완료: {total_ph:,}개 upsert, {skipped_ph}개 제품 미매핑으로 건너뜀")

    finally:
        await source_engine.dispose()
        await target_engine.dispose()

    print("\n✅ 동기화 완료!")
    print("검증: DATABASE_URL=\"$RAILWAY_DATABASE_URL\" uv run python scripts/data_audit.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
