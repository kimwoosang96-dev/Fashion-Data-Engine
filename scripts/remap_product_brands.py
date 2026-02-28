"""
edit-shop 제품의 product_key prefix(slug)로 brand_id 재매핑.

정책:
- channel_type='edit-shop' 기본 대상
- products.brand_id IS NULL 인 행만 처리
- product_key 형식이 "slug:handle" 인 경우에만 처리
- slug == brands.slug 일치 시 brand_id 설정

사용법:
  uv run python scripts/remap_product_brands.py --dry-run
  uv run python scripts/remap_product_brands.py --apply

  # Railway (DATABASE_URL 환경변수로 전환)
  DATABASE_URL=postgresql+asyncpg://... uv run python scripts/remap_product_brands.py --apply
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sqlalchemy import bindparam, func, text  # noqa: E402

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="product_key slug 기반 brand_id 재매핑")
    p.add_argument("--apply", action="store_true", help="실제 UPDATE 수행")
    p.add_argument("--dry-run", action="store_true", help="미리보기만 수행(기본)")
    p.add_argument(
        "--channel-type",
        default="edit-shop",
        help="대상 channel_type (기본: edit-shop)",
    )
    return p.parse_args()


async def run(*, apply: bool, channel_type: str) -> int:
    await init_db()

    async with AsyncSessionLocal() as db:
        # NULL brand_id 전체 수
        base_count = (await db.execute(text("""
            SELECT COUNT(*)
            FROM products p
            JOIN channels c ON c.id = p.channel_id
            WHERE p.brand_id IS NULL
              AND c.channel_type = :ct
        """), {"ct": channel_type})).scalar_one()

        # slug 매칭 후보 조회
        # split_part(product_key, ':', 1) = ':' 앞 부분 (PostgreSQL)
        # LIKE '%:%' 조건으로 ':' 항상 존재 보장
        candidates = (await db.execute(text("""
            SELECT
                p.id AS product_id,
                b.id AS brand_id,
                lower(split_part(p.product_key, ':', 1)) AS slug,
                p.channel_id
            FROM products p
            JOIN channels c ON c.id = p.channel_id
            JOIN brands b
              ON b.slug = lower(split_part(p.product_key, ':', 1))
            WHERE p.brand_id IS NULL
              AND c.channel_type = :ct
              AND p.product_key LIKE '%:%'
        """), {"ct": channel_type})).fetchall()

        expected_remaining = max(base_count - len(candidates), 0)
        print(
            f"mode={'apply' if apply else 'dry-run'} channel_type={channel_type} "
            f"null_brand_products={base_count} remap_candidates={len(candidates)} "
            f"expected_remaining={expected_remaining}"
        )

        if candidates:
            # 슬러그별 집계 (상위 20)
            from collections import Counter
            by_slug = Counter(row[2] for row in candidates)
            print("\n[top slugs]")
            for slug, cnt in by_slug.most_common(20):
                print(f"  {slug}: {cnt}")

            print("\n[sample 10]")
            for product_id, brand_id, slug, channel_id in candidates[:10]:
                print(f"  product_id={product_id} channel_id={channel_id} slug={slug} -> brand_id={brand_id}")

        if not apply:
            return 0

        if not candidates:
            print("Nothing to update.")
            return 0

        # 배치 UPDATE — SQLAlchemy expandable IN 미사용, executemany 방식으로 처리
        # (대량이므로 500개 단위 커밋)
        batch_size = 500
        total_updated = 0
        pairs = [(row[1], row[0]) for row in candidates]  # (brand_id, product_id)

        for i in range(0, len(pairs), batch_size):
            batch = pairs[i : i + batch_size]
            for brand_id, product_id in batch:
                await db.execute(
                    text("UPDATE products SET brand_id = :bid WHERE id = :pid"),
                    {"bid": brand_id, "pid": product_id},
                )
            await db.commit()
            total_updated += len(batch)
            print(f"  커밋 {total_updated}/{len(pairs)}")

        print(f"\nupdated={total_updated}")

    return 0


if __name__ == "__main__":
    args = parse_args()
    apply = bool(args.apply and not args.dry_run)
    raise SystemExit(asyncio.run(run(apply=apply, channel_type=args.channel_type)))
