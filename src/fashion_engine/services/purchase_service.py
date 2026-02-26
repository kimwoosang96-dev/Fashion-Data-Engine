"""
구매 이력 서비스 — 저장, 성공도 계산, 통계.

Score 알고리즘:
  PriceHistory에서 동일 product_key의 모든 KRW 가격 수집 후
  paid_price_krw의 백분위 순위 계산 → Grade S/A/B/C/D 부여.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.models.purchase import Purchase
from fashion_engine.models.product import Product
from fashion_engine.models.price_history import PriceHistory


# ── Grade 기준 ──────────────────────────────────────────────────────────────

def _calc_grade(percentile: float) -> str:
    if percentile <= 10:
        return "S"
    elif percentile <= 25:
        return "A"
    elif percentile <= 50:
        return "B"
    elif percentile <= 75:
        return "C"
    else:
        return "D"


def _grade_badge(grade: str, percentile: float) -> str:
    badges = {
        "S": "역대 최저가 달성! 🏆",
        "A": f"역대 상위 {round(percentile)}%",
        "B": f"평균 이하 구매",
        "C": f"평균 수준 구매",
        "D": f"비싸게 구매한 편",
    }
    return badges.get(grade, "")


# ── CRUD ────────────────────────────────────────────────────────────────────

async def create_purchase(db: AsyncSession, data: dict) -> Purchase:
    purchase = Purchase(
        product_key=data["product_key"],
        product_name=data["product_name"],
        brand_slug=data.get("brand_slug"),
        channel_name=data["channel_name"],
        channel_url=data.get("channel_url"),
        paid_price_krw=data["paid_price_krw"],
        original_price_krw=data.get("original_price_krw"),
        purchased_at=data.get("purchased_at") or datetime.utcnow(),
        notes=data.get("notes"),
    )
    db.add(purchase)
    await db.commit()
    await db.refresh(purchase)
    return purchase


async def get_purchase(db: AsyncSession, purchase_id: int) -> Purchase | None:
    result = await db.execute(select(Purchase).where(Purchase.id == purchase_id))
    return result.scalar_one_or_none()


async def list_purchases(db: AsyncSession, limit: int = 50, offset: int = 0) -> list[Purchase]:
    result = await db.execute(
        select(Purchase).order_by(Purchase.purchased_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def delete_purchase(db: AsyncSession, purchase_id: int) -> bool:
    purchase = await get_purchase(db, purchase_id)
    if not purchase:
        return False
    await db.delete(purchase)
    await db.commit()
    return True


# ── Score 계산 ───────────────────────────────────────────────────────────────

async def _get_krw_prices_for_key(db: AsyncSession, product_key: str) -> list[int]:
    """product_key에 해당하는 모든 PriceHistory KRW 가격 수집."""
    result = await db.execute(
        select(PriceHistory.price)
        .join(Product, Product.id == PriceHistory.product_id)
        .where(Product.product_key == product_key)
        .where(PriceHistory.currency == "KRW")
    )
    return [int(row[0]) for row in result.all() if row[0]]


async def calc_score(db: AsyncSession, purchase: Purchase) -> dict[str, Any]:
    """구매 성공도 계산."""
    prices = await _get_krw_prices_for_key(db, purchase.product_key)

    if not prices:
        return {
            "grade": "N/A",
            "percentile": None,
            "badge": "가격 이력 데이터 없음",
            "min_ever_krw": None,
            "max_ever_krw": None,
            "avg_krw": None,
            "data_points": 0,
            "savings_vs_full": None,
            "savings_vs_avg": None,
            "verdict": "아직 충분한 가격 이력이 없습니다. 크롤을 더 실행해 주세요.",
        }

    paid = purchase.paid_price_krw
    min_p = min(prices)
    max_p = max(prices)
    avg_p = int(sum(prices) / len(prices))

    # 백분위 = paid보다 저렴한 가격의 비율
    cheaper_count = sum(1 for p in prices if p < paid)
    percentile = round(cheaper_count / len(prices) * 100, 1)

    grade = _calc_grade(percentile)
    badge = _grade_badge(grade, percentile)

    savings_vs_full = (purchase.original_price_krw - paid) if purchase.original_price_krw else None
    savings_vs_avg = avg_p - paid  # 양수면 평균보다 저렴

    if savings_vs_avg > 0:
        verdict = f"평균보다 {savings_vs_avg:,}원 저렴하게 구매했습니다"
    elif savings_vs_avg < 0:
        verdict = f"평균보다 {abs(savings_vs_avg):,}원 비싸게 구매했습니다"
    else:
        verdict = "평균 가격에 구매했습니다"

    return {
        "grade": grade,
        "percentile": percentile,
        "badge": badge,
        "min_ever_krw": min_p,
        "max_ever_krw": max_p,
        "avg_krw": avg_p,
        "data_points": len(prices),
        "savings_vs_full": savings_vs_full,
        "savings_vs_avg": savings_vs_avg,
        "verdict": verdict,
    }


# ── 통계 ─────────────────────────────────────────────────────────────────────

async def get_stats(db: AsyncSession) -> dict[str, Any]:
    """전체 구매 통계."""
    result = await db.execute(select(Purchase))
    purchases = list(result.scalars().all())

    if not purchases:
        return {
            "total_purchases": 0,
            "total_paid_krw": 0,
            "total_savings_vs_full_krw": 0,
            "grade_distribution": {},
            "best_deal": None,
        }

    total_paid = sum(p.paid_price_krw for p in purchases)
    total_savings = sum(
        (p.original_price_krw - p.paid_price_krw)
        for p in purchases
        if p.original_price_krw and p.original_price_krw > p.paid_price_krw
    )

    # best_deal: 절약 금액이 가장 큰 구매
    best = max(
        purchases,
        key=lambda p: (p.original_price_krw - p.paid_price_krw) if p.original_price_krw else 0,
        default=None,
    )
    best_deal = None
    if best and best.original_price_krw:
        saved = best.original_price_krw - best.paid_price_krw
        discount_rate = round(saved / best.original_price_krw * 100) if best.original_price_krw else None
        best_deal = {
            "id": best.id,
            "product_name": best.product_name,
            "paid_price_krw": best.paid_price_krw,
            "original_price_krw": best.original_price_krw,
            "savings_krw": saved,
            "discount_rate": discount_rate,
        }

    return {
        "total_purchases": len(purchases),
        "total_paid_krw": total_paid,
        "total_savings_vs_full_krw": total_savings,
        "best_deal": best_deal,
    }
