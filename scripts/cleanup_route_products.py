"""오인덱싱 비패션 제품 소프트 삭제 스크립트.

대상:
  - route:routeins (3개) — Shipping Protection by Route
  - re-do:... (2개)  — CHERRY LA "Package Protection" 제품

실행:
  uv run python scripts/cleanup_route_products.py --dry-run   # 확인만
  uv run python scripts/cleanup_route_products.py             # 실제 삭제
"""

import argparse
import asyncio
import sys

sys.path.insert(0, "src")

from sqlalchemy import select, update

from fashion_engine.database import AsyncSessionLocal
from fashion_engine.models.product import Product

# 확실히 오인덱싱된 제품 ID (탐색 단계에서 직접 확인)
_TARGET_IDS: list[int] = [24936, 24938, 38679, 54305, 56304]

# 추가 안전망: vendor / name 키워드 기반으로 다른 오인덱싱 제품도 탐지
_VENDOR_DENYLIST = {"route", "routeins"}
_NAME_KEYWORDS = {"shipping protection", "package protection", "route protection"}


async def find_non_fashion_products(db) -> list[Product]:
    """vendor 또는 name 기준으로 비패션 제품 탐지."""
    stmt = select(Product).where(Product.is_active == True)
    result = await db.execute(stmt)
    all_active = result.scalars().all()

    flagged = []
    for p in all_active:
        vendor_lower = (p.vendor or "").lower().strip()
        name_lower = (p.name or "").lower()
        if vendor_lower in _VENDOR_DENYLIST:
            flagged.append(p)
        elif any(kw in name_lower for kw in _NAME_KEYWORDS):
            flagged.append(p)
    return flagged


async def main(dry_run: bool) -> None:
    async with AsyncSessionLocal() as db:
        # 이미 알려진 ID + 동적 탐지 통합
        known_stmt = select(Product).where(
            Product.id.in_(_TARGET_IDS), Product.is_active == True
        )
        known_result = await db.execute(known_stmt)
        known_products = known_result.scalars().all()

        dynamic_products = await find_non_fashion_products(db)

        # 중복 제거 (ID 기준 합산)
        all_by_id: dict[int, Product] = {}
        for p in known_products + dynamic_products:
            all_by_id[p.id] = p
        targets = list(all_by_id.values())

        if not targets:
            print("삭제 대상 없음 — 이미 모두 정리됨")
            return

        print(f"{'[DRY-RUN] ' if dry_run else ''}삭제 대상 {len(targets)}개:")
        for p in targets:
            print(
                f"  ID={p.id:6d} | product_key={p.product_key or '':40s} | "
                f"vendor={p.vendor or '':12s} | name={p.name[:50] if p.name else ''}"
            )

        if dry_run:
            print("\n--dry-run 모드: 실제 변경 없음.")
            return

        ids = [p.id for p in targets]
        await db.execute(
            update(Product).where(Product.id.in_(ids)).values(is_active=False)
        )
        await db.commit()
        print(f"\n완료: {len(ids)}개 제품 is_active → False")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="오인덱싱 비패션 제품 소프트 삭제")
    parser.add_argument(
        "--dry-run", action="store_true", help="실제 변경 없이 대상만 출력"
    )
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
