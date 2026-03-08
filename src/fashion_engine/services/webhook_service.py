from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.models.activity_feed import ActivityFeed
from fashion_engine.models.brand import Brand
from fashion_engine.models.channel import Channel
from fashion_engine.models.product import Product
from fashion_engine.models.webhook_subscription import WebhookSubscription

logger = logging.getLogger(__name__)


async def list_webhook_subscriptions(db: AsyncSession) -> list[WebhookSubscription]:
    rows = (
        await db.execute(
            select(WebhookSubscription).order_by(
                WebhookSubscription.created_at.desc(),
                WebhookSubscription.id.desc(),
            )
        )
    ).scalars().all()
    return list(rows)


async def create_webhook_subscription(
    db: AsyncSession,
    *,
    url: str,
    secret: str,
    brand_ids: list[int] | None,
    event_types: list[str],
) -> WebhookSubscription:
    row = WebhookSubscription(
        url=url.strip()[:2000],
        secret=secret.strip()[:100],
        brand_ids=brand_ids or None,
        event_types=event_types,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def delete_webhook_subscription(db: AsyncSession, subscription_id: int) -> bool:
    row = await db.get(WebhookSubscription, subscription_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    return True


def _subscription_matches(sub: WebhookSubscription, event: ActivityFeed) -> bool:
    if not sub.is_active:
        return False
    if event.event_type not in (sub.event_types or []):
        return False
    if sub.brand_ids and event.brand_id not in sub.brand_ids:
        return False
    return True


async def dispatch_webhooks_for_feed_items(
    db: AsyncSession,
    events: list[ActivityFeed],
) -> int:
    if not events:
        return 0
    subscriptions = await list_webhook_subscriptions(db)
    if not subscriptions:
        return 0

    product_ids = [event.product_id for event in events if event.product_id]
    channel_ids = [event.channel_id for event in events if event.channel_id]
    brand_ids = [event.brand_id for event in events if event.brand_id]

    products = (
        await db.execute(select(Product).where(Product.id.in_(product_ids)))
    ).scalars().all() if product_ids else []
    channels = (
        await db.execute(select(Channel).where(Channel.id.in_(channel_ids)))
    ).scalars().all() if channel_ids else []
    brands = (
        await db.execute(select(Brand).where(Brand.id.in_(brand_ids)))
    ).scalars().all() if brand_ids else []
    product_by_id = {row.id: row for row in products}
    channel_by_id = {row.id: row for row in channels}
    brand_by_id = {row.id: row for row in brands}

    sent = 0
    async with httpx.AsyncClient(timeout=5.0) as client:
        for event in events:
            for sub in subscriptions:
                if not _subscription_matches(sub, event):
                    continue
                product = product_by_id.get(event.product_id) if event.product_id else None
                channel = channel_by_id.get(event.channel_id) if event.channel_id else None
                brand = brand_by_id.get(event.brand_id) if event.brand_id else None
                meta = event.metadata_json if isinstance(event.metadata_json, dict) else {}
                payload = {
                    "id": event.id,
                    "event_type": event.event_type,
                    "product_name": event.product_name or (product.name if product else None),
                    "product_key": product.product_key if product else None,
                    "brand_id": event.brand_id,
                    "brand_name": brand.name if brand else None,
                    "channel_id": event.channel_id,
                    "channel_name": channel.name if channel else None,
                    "price_krw": event.price_krw,
                    "discount_rate": event.discount_rate,
                    "source_url": event.source_url or (product.url if product else None),
                    "image_url": meta.get("image_url") or (product.image_url if product else None),
                    "detected_at": event.detected_at.isoformat() if event.detected_at else None,
                }
                body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                signature = hmac.new(
                    sub.secret.encode("utf-8"),
                    body.encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
                try:
                    resp = await client.post(
                        sub.url,
                        content=body.encode("utf-8"),
                        headers={
                            "Content-Type": "application/json",
                            "X-Fashion-Signature": f"sha256={signature}",
                        },
                    )
                    if 200 <= resp.status_code < 300:
                        sent += 1
                    else:
                        logger.warning("webhook dispatch failed subscription=%s status=%s", sub.id, resp.status_code)
                except Exception as exc:
                    logger.warning("webhook dispatch error subscription=%s err=%s", sub.id, exc)
    return sent
