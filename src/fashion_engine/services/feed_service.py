from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fashion_engine.models.intel import IntelEvent

_EVENT_TYPE_MAP = {
    "sale_start": "sale_start",
    "sales_spike": "price_cut",
    "drop": "new_drop",
    "upcoming_drop": "new_drop",
    "sold_out": "sold_out",
    "restock": "restock",
}


def _coerce_feed_type(event_type: str) -> str | None:
    return _EVENT_TYPE_MAP.get((event_type or "").lower())


def _extract_details(event: IntelEvent) -> dict:
    if not event.details_json:
        return {}
    try:
        data = json.loads(event.details_json)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


async def get_activity_feed(
    db: AsyncSession,
    *,
    event_type: str | None = None,
    brand_id: int | None = None,
    limit: int = 30,
    offset: int = 0,
) -> list[dict]:
    stmt = (
        select(IntelEvent)
        .options(
            selectinload(IntelEvent.brand),
            selectinload(IntelEvent.channel),
            selectinload(IntelEvent.product),
        )
        .where(IntelEvent.is_active == True)  # noqa: E712
        .order_by(IntelEvent.detected_at.desc(), IntelEvent.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if brand_id is not None:
        stmt = stmt.where(IntelEvent.brand_id == brand_id)

    rows = (await db.execute(stmt)).scalars().all()
    payload: list[dict] = []
    for row in rows:
        feed_type = _coerce_feed_type(row.event_type)
        if not feed_type:
            continue
        if event_type and feed_type != event_type:
            continue

        details = _extract_details(row)
        product_name = row.product.name if row.product else None
        image_url = row.product.image_url if row.product else None
        price_value = details.get("price_krw")
        if price_value is None:
            price_value = details.get("current_price_krw")
        discount_value = details.get("discount_rate")

        payload.append(
            {
                "id": row.id,
                "event_type": feed_type,
                "product_name": product_name or row.title,
                "brand_name": row.brand.name if row.brand else None,
                "channel_name": row.channel.name if row.channel else None,
                "price_krw": int(price_value) if isinstance(price_value, (int, float)) else None,
                "discount_rate": int(discount_value) if isinstance(discount_value, (int, float)) else None,
                "source_url": row.source_url or (row.product.url if row.product else None),
                "image_url": image_url,
                "product_key": row.product_key,
                "detected_at": row.detected_at.isoformat(),
            }
        )
    return payload
