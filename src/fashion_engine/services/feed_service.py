from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fashion_engine.models.activity_feed import ActivityFeed


async def get_activity_feed(
    db: AsyncSession,
    *,
    event_type: str | None = None,
    brand_id: int | None = None,
    limit: int = 30,
    offset: int = 0,
) -> list[dict]:
    stmt = (
        select(ActivityFeed)
        .options(
            selectinload(ActivityFeed.brand),
            selectinload(ActivityFeed.channel),
            selectinload(ActivityFeed.product),
        )
        .order_by(ActivityFeed.detected_at.desc(), ActivityFeed.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if brand_id is not None:
        stmt = stmt.where(ActivityFeed.brand_id == brand_id)
    if event_type is not None:
        stmt = stmt.where(ActivityFeed.event_type == event_type)

    rows = (await db.execute(stmt)).scalars().all()
    payload: list[dict] = []
    for row in rows:
        details = row.metadata_json or {}
        image_url = details.get("image_url") if isinstance(details, dict) else None
        product_name = row.product.name if row.product else None

        payload.append(
            {
                "id": row.id,
                "event_type": row.event_type,
                "product_name": product_name or row.product_name,
                "brand_name": row.brand.name if row.brand else None,
                "channel_name": row.channel.name if row.channel else None,
                "price_krw": row.price_krw,
                "discount_rate": row.discount_rate,
                "source_url": row.source_url or (row.product.url if row.product else None),
                "image_url": image_url or (row.product.image_url if row.product else None),
                "product_key": row.product.product_key if row.product else None,
                "detected_at": row.detected_at,
            }
        )
    return payload
