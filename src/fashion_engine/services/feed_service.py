from __future__ import annotations

from datetime import datetime
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fashion_engine.models.brand import Brand
from fashion_engine.models.activity_feed import ActivityFeed
from fashion_engine.services.realtime_client import broadcast_feed_item
from fashion_engine.services.webhook_service import dispatch_webhooks_for_feed_items

logger = logging.getLogger(__name__)


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


async def ingest_activity_feed(
    db: AsyncSession,
    *,
    event_type: str,
    product_name: str,
    source_url: str,
    brand_slug: str | None = None,
    price_krw: int | None = None,
    discount_rate: int | None = None,
    image_url: str | None = None,
    notes: str | None = None,
    detected_at: datetime | None = None,
) -> dict:
    brand = None
    if brand_slug:
        brand = (
            await db.execute(
                select(Brand).where(Brand.slug == brand_slug)
            )
        ).scalar_one_or_none()
        if not brand:
            raise ValueError("brand_slug not found")

    metadata: dict[str, str] = {"source": "gpt_actions"}
    if image_url:
        metadata["image_url"] = image_url
    if notes:
        metadata["notes"] = notes

    row = ActivityFeed(
        event_type=event_type,
        brand_id=brand.id if brand else None,
        product_name=product_name.strip()[:500],
        price_krw=price_krw,
        discount_rate=discount_rate,
        source_url=source_url.strip()[:2000],
        metadata_json=metadata,
        detected_at=detected_at or datetime.utcnow(),
        notified=False,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    payload = {
        "id": row.id,
        "event_type": row.event_type,
        "product_name": row.product_name,
        "brand_name": brand.name if brand else None,
        "channel_name": None,
        "price_krw": row.price_krw,
        "discount_rate": row.discount_rate,
        "source_url": row.source_url,
        "image_url": image_url,
        "product_key": None,
        "detected_at": row.detected_at,
    }
    await broadcast_feed_item(
        {
            **payload,
            "detected_at": row.detected_at.isoformat(),
        }
    )
    try:
        await dispatch_webhooks_for_feed_items(db, [row])
    except Exception as exc:
        logger.warning("feed ingest webhook dispatch failed: %s", exc)
    return payload
