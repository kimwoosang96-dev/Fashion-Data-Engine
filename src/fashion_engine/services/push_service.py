from __future__ import annotations

import asyncio

from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.config import settings
from fashion_engine.models.activity_feed import ActivityFeed
from fashion_engine.models.product import Product
from fashion_engine.models.push_subscription import PushSubscription


async def _send_webpush(subscription_info: dict, payload: dict) -> None:
    await asyncio.to_thread(
        webpush,
        subscription_info=subscription_info,
        data=__import__("json").dumps(payload, ensure_ascii=False),
        vapid_private_key=settings.push_vapid_private_key,
        vapid_claims={"sub": settings.push_vapid_subject},
    )


async def send_push_for_feed_items(
    db: AsyncSession,
    events: list[ActivityFeed],
) -> int:
    if not settings.push_vapid_private_key or not settings.push_vapid_public_key:
        return 0

    subs = list((await db.execute(select(PushSubscription))).scalars().all())
    if not subs:
        return 0

    sent = 0
    for event in events:
        target_subs = [
            sub for sub in subs
            if not sub.brand_ids or (event.brand_id is not None and event.brand_id in sub.brand_ids)
        ]
        if not target_subs:
            continue

        product_key = None
        if event.product_id:
            product = await db.get(Product, event.product_id)
            product_key = product.product_key if product else None
        url = f"/compare/{product_key}" if product_key else (event.source_url or "/feed")
        title = f"{event.product_name or '상품'} 알림"
        if event.event_type == "sale_start":
            title = f"{event.product_name or '상품'} 세일 시작"
        elif event.event_type == "new_drop":
            title = f"{event.product_name or '상품'} 신제품 감지"
        elif event.event_type == "price_cut":
            title = f"{event.product_name or '상품'} 가격 인하"

        body_parts = []
        if event.discount_rate is not None:
            body_parts.append(f"{event.discount_rate}% OFF")
        if event.price_krw is not None:
            body_parts.append(f"₩{int(event.price_krw):,}")
        body = " · ".join(body_parts) if body_parts else "지금 확인해보세요"
        payload = {"title": title, "body": body, "url": url}

        for sub in target_subs:
            subscription_info = {
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            }
            try:
                await _send_webpush(subscription_info, payload)
                sent += 1
            except WebPushException as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status in (404, 410):
                    await db.delete(sub)
                    await db.commit()
    return sent
