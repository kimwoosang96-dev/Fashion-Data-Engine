"""
product_catalog 의 가격 통계 컬럼을 최신 PriceHistory 기반으로 갱신.

업데이트 대상:
- min_price_krw: 해당 normalized_key 그룹에서 가장 낮은 현재가 (KRW)
- max_price_krw: 해당 normalized_key 그룹에서 가장 높은 현재가 (KRW)
- is_sale_anywhere: 하나라도 세일 중이면 True

전략:
1. exchange_rates 에서 환율 로드 (KRW 기준)
2. price_history DISTINCT ON product_id (최신 레코드) → KRW 환산
3. product_catalog 일괄 UPDATE

사용법:
    uv run python scripts/update_catalog_prices.py --dry-run
    DATABASE_URL=postgresql+asyncpg://... uv run python scripts/update_catalog_prices.py --apply
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
    p = argparse.ArgumentParser(description="product_catalog 가격 통계 갱신")
    p.add_argument("--apply", action="store_true", help="실제 UPDATE 실행")
    p.add_argument("--dry-run", action="store_true", help="미리보기 (기본)")
    p.add_argument("--batch-size", type=int, default=500, help="배치 크기 (기본 500)")
    return p.parse_args()


async def run(*, apply: bool, batch_size: int) -> int:
    await init_db()

    async with AsyncSessionLocal() as db:
        # ── 0. 현재 상태 ──────────────────────────────────────────────────
        null_cnt = (await db.execute(text(
            "SELECT COUNT(*) FROM product_catalog WHERE min_price_krw IS NULL"
        ))).scalar()
        total_cnt = (await db.execute(text(
            "SELECT COUNT(*) FROM product_catalog"
        ))).scalar()
        print(f"product_catalog 총: {total_cnt:,}개 / 가격 미설정: {null_cnt:,}개")

        # ── 1. 환율 로드 ──────────────────────────────────────────────────
        rate_rows = (await db.execute(text(
            "SELECT from_currency, rate FROM exchange_rates WHERE to_currency = 'KRW'"
        ))).all()
        fx: dict[str, float] = {"KRW": 1.0}
        for currency, rate in rate_rows:
            fx[currency] = float(rate)
        print(f"환율 로드: {fx}")

        # ── 2. 최신 PriceHistory per product (ROW_NUMBER — SQLite/PG 공용) ──
        print("▶ 최신 가격 집계 중 (ROW_NUMBER per product)...")
        price_rows = (await db.execute(text("""
            WITH ranked AS (
                SELECT
                    ph.product_id,
                    ph.price,
                    ph.currency,
                    ph.is_sale,
                    ROW_NUMBER() OVER (
                        PARTITION BY ph.product_id
                        ORDER BY ph.crawled_at DESC
                    ) AS rn
                FROM price_history ph
            )
            SELECT
                p.id AS product_id,
                COALESCE(p.normalized_key, p.product_key) AS nkey,
                r.price,
                r.currency,
                r.is_sale
            FROM products p
            JOIN ranked r ON r.product_id = p.id AND r.rn = 1
            WHERE COALESCE(p.normalized_key, p.product_key) IS NOT NULL
        """))).all()

        print(f"  가격 데이터: {len(price_rows):,}개 제품")

        # ── 3. normalized_key별 KRW 가격 집계 ───────────────────────────
        from collections import defaultdict
        key_prices: dict[str, list[int]] = defaultdict(list)
        key_sale: dict[str, bool] = defaultdict(bool)

        skipped = 0
        for _, nkey, price, currency, is_sale in price_rows:
            if nkey is None:
                continue
            rate = fx.get(currency)
            if rate is None:
                skipped += 1
                continue
            price_krw = int(float(price) * rate)
            if price_krw <= 0 or price_krw > 50_000_000:  # 이상값 필터 (5천만원 초과)
                skipped += 1
                continue
            key_prices[nkey].append(price_krw)
            if is_sale:
                key_sale[nkey] = True

        print(f"  집계 완료: {len(key_prices):,}개 키 / 스킵: {skipped:,}개")

        # 집계 결과
        catalog_updates: list[dict] = []
        for nkey, prices in key_prices.items():
            catalog_updates.append({
                "nkey": nkey,
                "min_price": min(prices),
                "max_price": max(prices),
                "is_sale": key_sale.get(nkey, False),
            })

        print(f"  UPDATE 대상: {len(catalog_updates):,}개 catalog 행")

        if not apply:
            # 샘플 출력
            print("\n[샘플 20개]")
            for row in catalog_updates[:20]:
                print(
                    f"  key={row['nkey'][:50]}"
                    f"  min={row['min_price']:,}  max={row['max_price']:,}"
                    f"  sale={row['is_sale']}"
                )
            print(f"\n[DRY-RUN] --apply 플래그 없이는 실제 변경 없음")
            return 0

        # ── 4. unnest() 배열 UPDATE — 단일 SQL 호출 (네트워크 효율) ──────
        # PostgreSQL의 unnest()로 배열을 행으로 변환하여 JOIN UPDATE
        print("▶ product_catalog UPDATE 중 (unnest 배열 방식)...")
        updated = 0
        for i in range(0, len(catalog_updates), batch_size):
            batch = catalog_updates[i : i + batch_size]
            nkeys     = [r["nkey"] for r in batch]
            min_prices = [r["min_price"] for r in batch]
            max_prices = [r["max_price"] for r in batch]
            is_sales   = [r["is_sale"] for r in batch]

            result = await db.execute(
                text("""
                    UPDATE product_catalog pc
                    SET min_price_krw    = data.min_p,
                        max_price_krw    = data.max_p,
                        is_sale_anywhere = data.is_sale,
                        updated_at       = NOW()
                    FROM (
                        SELECT
                            unnest(CAST(:nkeys AS text[]))  AS nkey,
                            unnest(CAST(:min_p AS int[]))   AS min_p,
                            unnest(CAST(:max_p AS int[]))   AS max_p,
                            unnest(CAST(:is_sale AS bool[])) AS is_sale
                    ) AS data
                    WHERE pc.normalized_key = data.nkey
                """),
                {
                    "nkeys":  nkeys,
                    "min_p":  min_prices,
                    "max_p":  max_prices,
                    "is_sale": is_sales,
                },
            )
            await db.commit()
            updated += result.rowcount
            pct = updated / len(catalog_updates) * 100
            print(f"  {updated:,}/{len(catalog_updates):,} ({pct:.0f}%)", end="\r")

        print(f"\n  UPDATE 완료: {updated:,}개")

        # ── 5. 결과 요약 ──────────────────────────────────────────────────
        after_null = (await db.execute(text(
            "SELECT COUNT(*) FROM product_catalog WHERE min_price_krw IS NULL"
        ))).scalar()
        sale_cnt = (await db.execute(text(
            "SELECT COUNT(*) FROM product_catalog WHERE is_sale_anywhere = TRUE"
        ))).scalar()
        avg_price = (await db.execute(text(
            "SELECT AVG(min_price_krw) FROM product_catalog WHERE min_price_krw > 0"
        ))).scalar()

        print(f"\n✅ 가격 통계 갱신 완료!")
        print(f"   가격 미설정: {after_null:,}개 (이전: {null_cnt:,}개)")
        print(f"   세일 중인 catalog: {sale_cnt:,}개")
        print(f"   평균 최저가(KRW): {int(avg_price or 0):,}원")

    return 0


if __name__ == "__main__":
    args = parse_args()
    apply = bool(args.apply and not args.dry_run)
    raise SystemExit(asyncio.run(run(apply=apply, batch_size=args.batch_size)))
