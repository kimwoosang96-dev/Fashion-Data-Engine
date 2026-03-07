from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.crawler.product_crawler import ProductInfo, ProductCrawler
from fashion_engine.database import get_db
from fashion_engine.models.activity_feed import ActivityFeed
from fashion_engine.models.channel import Channel
from fashion_engine.models.product import Product
from fashion_engine.services.product_service import (
    build_price_history_row,
    find_brands_by_vendors,
    get_rate_to_krw,
    upsert_product,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _channel_slug_candidates(channel: Channel) -> set[str]:
    host = urlparse(channel.url).netloc.lower().replace("www.", "")
    return {
        slugify(channel.name or ""),
        slugify(host),
        slugify(host.split(".")[0]),
    } - {""}


async def _find_channel_by_slug(db: AsyncSession, channel_slug: str) -> Channel | None:
    rows = (await db.execute(select(Channel))).scalars().all()
    for channel in rows:
        if channel_slug in _channel_slug_candidates(channel):
            return channel
    return None


def _verify_shopify_hmac(secret: str, body: bytes, header_value: str | None) -> bool:
    if not secret or not header_value:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, header_value.strip())


def _pick_variant(payload: dict) -> dict | None:
    variants = payload.get("variants") or []
    if not isinstance(variants, list) or not variants:
        return None
    for variant in variants:
        if variant.get("available") is True:
            return variant
        if (variant.get("inventory_quantity") or 0) > 0:
            return variant
    return variants[0]


def _to_float(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_shopify_product(payload: dict, channel: Channel) -> ProductInfo:
    handle = (payload.get("handle") or "").strip()
    title = (payload.get("title") or "").strip()
    vendor = (payload.get("vendor") or channel.name or "").strip()
    if not handle or not title or not vendor:
        raise HTTPException(status_code=400, detail="invalid shopify product payload")

    variant = _pick_variant(payload)
    if not variant:
        raise HTTPException(status_code=400, detail="shopify payload has no variants")

    price = _to_float(variant.get("price"))
    if price is None:
        raise HTTPException(status_code=400, detail="shopify variant price missing")
    compare_at_price = _to_float(variant.get("compare_at_price"))
    if compare_at_price is not None and compare_at_price <= price:
        compare_at_price = None

    image = payload.get("image") or {}
    images = payload.get("images") or []
    image_url = image.get("src") if isinstance(image, dict) else None
    if not image_url and isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, dict):
            image_url = first.get("src")

    currency = ProductCrawler._infer_currency(channel.url, channel.country)  # type: ignore[attr-defined]
    return ProductInfo(
        title=title,
        vendor=vendor,
        handle=handle,
        product_type=payload.get("product_type"),
        price=price,
        compare_at_price=compare_at_price,
        currency=currency,
        sku=(variant.get("sku") or None),
        image_url=image_url,
        tags=payload.get("tags"),
        product_url=f"{channel.url.rstrip('/')}/products/{handle}",
        product_key=f"{slugify(vendor)}:{handle}",
        is_available=bool(variant.get("available", True)),
    )


@router.post("/shopify/{channel_slug}")
async def receive_shopify_webhook(
    channel_slug: str,
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(None, alias="X-Shopify-Hmac-Sha256"),
    db: AsyncSession = Depends(get_db),
):
    channel = await _find_channel_by_slug(db, channel_slug)
    if not channel:
        raise HTTPException(status_code=404, detail="channel not found")
    if not channel.webhook_secret:
        raise HTTPException(status_code=401, detail="webhook secret not configured")

    body = await request.body()
    if not _verify_shopify_hmac(channel.webhook_secret, body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="invalid webhook signature")

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid json payload") from exc

    info = _parse_shopify_product(payload, channel)
    rate = await get_rate_to_krw(db, info.currency)
    if rate is None:
        raise HTTPException(status_code=503, detail=f"missing FX rate for {info.currency}")

    existing = (
        await db.execute(select(Product).where(Product.url == info.product_url))
    ).scalar_one_or_none()
    brand_map = await find_brands_by_vendors(db, [info.vendor])
    brand = brand_map.get(info.vendor)
    product, is_new, sale_just_started, _ = await upsert_product(
        db,
        channel.id,
        info,
        rate,
        brand_id=brand.id if brand else None,
        existing=existing,
    )
    if history_row := build_price_history_row(product.id, info, rate):
        from fashion_engine.models.price_history import PriceHistory

        db.add(PriceHistory(**history_row))

    event_type = "new_drop" if is_new else ("sale_start" if sale_just_started else None)
    if event_type:
        db.add(
            ActivityFeed(
                event_type=event_type,
                product_id=product.id,
                channel_id=channel.id,
                brand_id=product.brand_id,
                product_name=product.name,
                price_krw=product.price_krw,
                discount_rate=product.discount_rate,
                source_url=product.url,
                metadata_json={"image_url": product.image_url, "source": "shopify_webhook"},
                detected_at=datetime.utcnow(),
                notified=False,
            )
        )

    await db.commit()
    return {
        "ok": True,
        "channel_id": channel.id,
        "product_id": product.id,
        "product_key": product.product_key,
        "is_new": is_new,
        "sale_just_started": sale_just_started,
    }
