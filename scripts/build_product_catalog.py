"""
기존 products 테이블을 product_catalog로 집계.

전략:
- normalized_key 기준으로 GROUP BY → ProductCatalog 행 생성
- normalized_key가 NULL인 제품은 product_key → normalized_key 대체 사용
- canonical_name: 해당 normalized_key의 가장 긴 제품명 (대표값)
- brand_id: 해당 그룹에서 가장 빈번한 brand_id
- listing_count: 채널 수 (distinct channel_id)
- min/max_price, is_sale_anywhere: 최신 PriceHistory 기준 집계

사용법:
    uv run python scripts/build_product_catalog.py --dry-run
    DATABASE_URL=postgresql+asyncpg://... uv run python scripts/build_product_catalog.py --apply
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sqlalchemy import text  # noqa: E402

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="product_catalog 백필")
    p.add_argument("--apply", action="store_true", help="실제 INSERT 실행")
    p.add_argument("--dry-run", action="store_true", help="미리보기 (기본)")
    p.add_argument("--batch-size", type=int, default=1000, help="배치 크기 (기본 1000)")
    return p.parse_args()


async def run(*, apply: bool, batch_size: int) -> int:
    await init_db()

    async with AsyncSessionLocal() as db:
        # ── 0. 현재 catalog 상태 ──────────────────────────────────────────
        existing_cnt = (await db.execute(text(
            "SELECT COUNT(*) FROM product_catalog"
        ))).scalar()
        print(f"현재 product_catalog: {existing_cnt:,}개")

        # ── 1. normalized_key별 집계 ──────────────────────────────────────
        # normalized_key가 NULL인 경우 product_key를 대체 사용
        print("▶ normalized_key별 집계 중...")
        # 1단계: products만 집계 (가격 제외) — 빠름
        rows = (await db.execute(text("""
            SELECT
                COALESCE(p.normalized_key, p.product_key) AS nkey,
                MAX(p.name) AS canonical_name,
                MODE() WITHIN GROUP (ORDER BY p.brand_id) AS brand_id,
                MAX(p.gender) AS gender,
                MAX(p.subcategory) AS subcategory,
                COUNT(DISTINCT p.channel_id) AS listing_count,
                MIN(p.created_at) AS first_seen_at
            FROM products p
            WHERE COALESCE(p.normalized_key, p.product_key) IS NOT NULL
            GROUP BY COALESCE(p.normalized_key, p.product_key)
        """))).all()

        total_keys = len(rows)
        print(f"  고유 normalized_key: {total_keys:,}개")

        if not apply:
            # 샘플 출력
            print("\n[샘플 20개]")
            for row in rows[:20]:
                print(f"  key={row[0][:50]} name={row[1][:40]} brand={row[2]} ch={row[5]}")
            print(f"\n[DRY-RUN] --apply 플래그 없이는 실제 변경 없음")
            return 0

        # ── 2. 기존 catalog key 셋 (이미 있는 건 SKIP) ──────────────────
        existing_keys: set[str] = {
            row[0]
            for row in (await db.execute(text(
                "SELECT normalized_key FROM product_catalog"
            ))).all()
        }
        print(f"  이미 catalog에 있는 key: {len(existing_keys):,}개 (SKIP)")

        new_rows = [r for r in rows if r[0] not in existing_keys]
        print(f"  신규 INSERT 대상: {len(new_rows):,}개")

        # ── 3. 배치 INSERT ────────────────────────────────────────────────
        print("▶ product_catalog INSERT 중...")
        inserted = 0
        for i in range(0, len(new_rows), batch_size):
            batch = new_rows[i : i + batch_size]
            values = [
                {
                    "nkey": row[0],
                    "name": row[1] or row[0],
                    "brand_id": row[2],
                    "gender": row[3],
                    "subcategory": row[4],
                    "listing_count": int(row[5]) if row[5] else 1,
                    "first_seen": row[6],
                }
                for row in batch
            ]
            await db.execute(
                text("""
                    INSERT INTO product_catalog
                        (normalized_key, canonical_name, brand_id, gender, subcategory,
                         listing_count, first_seen_at, updated_at)
                    VALUES
                        (:nkey, :name, :brand_id, :gender, :subcategory,
                         :listing_count, :first_seen, NOW())
                    ON CONFLICT (normalized_key) DO UPDATE SET
                        canonical_name = EXCLUDED.canonical_name,
                        listing_count  = EXCLUDED.listing_count,
                        updated_at     = NOW()
                """),
                values,
            )
            await db.commit()
            inserted += len(batch)
            print(f"  {inserted:,}/{len(new_rows):,}", end="\r")

        print(f"\n  INSERT 완료: {inserted:,}개")

        # ── 4. 결과 요약 ──────────────────────────────────────────────────
        final_cnt = (await db.execute(text("SELECT COUNT(*) FROM product_catalog"))).scalar()
        print(f"\n✅ product_catalog 완료!")
        print(f"   총 레코드: {final_cnt:,}개")
        print(f"   products 대비 집약률: {len(rows)/80348*100:.1f}%")

    return 0


if __name__ == "__main__":
    args = parse_args()
    apply = bool(args.apply and not args.dry_run)
    raise SystemExit(asyncio.run(run(apply=apply, batch_size=args.batch_size)))
