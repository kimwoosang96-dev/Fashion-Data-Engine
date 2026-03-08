from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.models.brand import Brand
from fashion_engine.models.channel import Channel
from fashion_engine.models.price_history import PriceHistory
from fashion_engine.models.product import Product


async def get_brand_seasonality(db: AsyncSession, brand_slug: str) -> dict | None:
    brand = (
        await db.execute(select(Brand).where(Brand.slug == brand_slug))
    ).scalar_one_or_none()
    if not brand:
        return None

    cutoff = datetime.utcnow() - timedelta(days=730)
    rows = (
        await db.execute(
            select(
                func.extract("month", PriceHistory.crawled_at).label("month"),
                func.count(func.distinct(PriceHistory.product_id)).label("sale_count"),
                func.avg(PriceHistory.discount_rate).label("avg_discount"),
                func.count(PriceHistory.id).label("data_points"),
            )
            .join(Product, Product.id == PriceHistory.product_id)
            .where(
                Product.brand_id == brand.id,
                PriceHistory.is_sale == True,  # noqa: E712
                PriceHistory.crawled_at >= cutoff,
            )
            .group_by(func.extract("month", PriceHistory.crawled_at))
            .order_by(func.extract("month", PriceHistory.crawled_at).asc())
        )
    ).all()

    monthly = {
        month: {
            "sale_count": 0,
            "avg_discount": None,
            "data_points": 0,
        }
        for month in range(1, 13)
    }
    for row in rows:
        month = int(row.month)
        monthly[month] = {
            "sale_count": int(row.sale_count or 0),
            "avg_discount": round(float(row.avg_discount), 2) if row.avg_discount is not None else None,
            "data_points": int(row.data_points or 0),
        }

    peak_sale_months = [
        month
        for month, _ in sorted(
            monthly.items(),
            key=lambda item: (-item[1]["sale_count"], item[0]),
        )[:3]
        if monthly[month]["sale_count"] > 0
    ]
    return {
        "brand_slug": brand.slug,
        "brand_name": brand.name,
        "monthly": monthly,
        "peak_sale_months": peak_sale_months,
        "data_window_days": 730,
    }


async def get_channel_competitiveness(
    db: AsyncSession,
    *,
    min_matches: int = 5,
    limit: int = 100,
) -> list[dict]:
    rows = (
        await db.execute(
            text(
                """
                WITH ranked AS (
                    SELECT
                        p.channel_id,
                        p.normalized_key,
                        p.price_krw,
                        RANK() OVER (
                            PARTITION BY p.normalized_key
                            ORDER BY p.price_krw ASC, p.id ASC
                        ) AS price_rank
                    FROM products p
                    WHERE p.price_krw IS NOT NULL
                      AND p.normalized_key IS NOT NULL
                      AND p.is_active = true
                )
                SELECT
                    c.id AS channel_id,
                    c.name AS channel_name,
                    c.country AS country,
                    c.platform AS platform,
                    COUNT(*) AS matched_products,
                    AVG(r.price_rank) AS avg_price_rank,
                    SUM(CASE WHEN r.price_rank = 1 THEN 1 ELSE 0 END) AS cheapest_count
                FROM ranked r
                JOIN channels c ON c.id = r.channel_id
                GROUP BY c.id, c.name, c.country, c.platform
                HAVING COUNT(*) >= :min_matches
                ORDER BY cheapest_count DESC, avg_price_rank ASC, channel_name ASC
                LIMIT :limit
                """
            ),
            {"min_matches": min_matches, "limit": limit},
        )
    ).all()
    payload: list[dict] = []
    for row in rows:
        matched_products = int(row.matched_products or 0)
        cheapest_count = int(row.cheapest_count or 0)
        payload.append(
            {
                "channel_id": int(row.channel_id),
                "channel_name": row.channel_name,
                "country": row.country,
                "platform": row.platform,
                "matched_products": matched_products,
                "avg_price_rank": round(float(row.avg_price_rank or 0), 3),
                "cheapest_count": cheapest_count,
                "cheapest_ratio": round((cheapest_count / matched_products) * 100, 1) if matched_products else 0.0,
            }
        )
    return payload
