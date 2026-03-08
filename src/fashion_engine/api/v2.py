from __future__ import annotations

import asyncio
import csv
import io
import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.api.auth import require_api_key
from fashion_engine.services.api_key_service import authenticate_api_key
from fashion_engine.api.schemas import (
    BrandSaleIntelOut,
    BrandSeasonalityOut,
    CrossChannelPriceHistoryOut,
    ProductAvailabilityOut,
    SearchV2ItemOut,
)
from fashion_engine.cache import cached_json
from fashion_engine.database import get_db
from fashion_engine.services import brand_service, product_service
from fashion_engine.services.analytics_service import get_brand_seasonality
from fashion_engine.services.search_service_v2 import keyword_search, semantic_search

router = APIRouter(prefix="/api/v2", tags=["v2"])


async def _maybe_authenticate_api_key(
    request: Request,
    db: AsyncSession,
    *,
    scope: str,
) -> None:
    raw_key = request.headers.get("X-API-Key")
    if not raw_key:
        auth = request.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            raw_key = auth.split(" ", 1)[1].strip()
    if raw_key:
        await authenticate_api_key(db, raw_key=raw_key, scope=scope)


@router.get("/search", response_model=list[SearchV2ItemOut])
async def search_v2(
    q: str = Query(..., min_length=1),
    mode: str = Query("keyword", pattern="^(keyword|semantic)$"),
    limit: int = Query(20, ge=1, le=50),
    response: Response = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    if request is not None:
        await _maybe_authenticate_api_key(request, db, scope="search")
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=30"

    async def fetch():
        if mode == "semantic":
            return await semantic_search(db, q=q, limit=limit)
        return await keyword_search(db, q=q, limit=limit)

    key = f"v2:search:{mode}:{limit}:{q.strip().lower()}"
    rows = await cached_json(key=key, ttl=60, fetch_fn=fetch)
    return [SearchV2ItemOut(**row) for row in rows]


@router.get("/brands/{slug}/sale-intel", response_model=BrandSaleIntelOut)
async def brand_sale_intel(
    slug: str,
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=600, stale-while-revalidate=60"

    key = f"v2:brand-sale-intel:{slug}"
    payload = await cached_json(
        key=key,
        ttl=600,
        fetch_fn=lambda: brand_service.get_brand_sale_intel(db, slug),
    )
    if not payload:
        raise HTTPException(status_code=404, detail="brand not found")
    return BrandSaleIntelOut(**payload)


@router.get("/brands/{slug}/seasonality", response_model=BrandSeasonalityOut)
async def brand_seasonality(
    slug: str,
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=1800, stale-while-revalidate=300"

    key = f"v2:brand-seasonality:{slug}"
    payload = await cached_json(
        key=key,
        ttl=1800,
        fetch_fn=lambda: get_brand_seasonality(db, slug),
    )
    if not payload:
        raise HTTPException(status_code=404, detail="brand not found")
    return BrandSeasonalityOut(**payload)


@router.get("/availability/{product_key:path}", response_model=ProductAvailabilityOut)
async def product_availability(
    product_key: str,
    response: Response = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    if request is not None:
        await _maybe_authenticate_api_key(request, db, scope="availability")
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"

    key = f"v2:availability:{product_key}"
    payload = await cached_json(
        key=key,
        ttl=300,
        fetch_fn=lambda: product_service.get_product_availability(db, product_key),
    )
    if not payload:
        raise HTTPException(status_code=404, detail="product not found")
    return ProductAvailabilityOut(**payload)


@router.get("/price-history/{product_key:path}", response_model=CrossChannelPriceHistoryOut)
async def cross_channel_price_history(
    product_key: str,
    days: int = Query(90, ge=7, le=365),
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"

    key = f"v2:price-history:{product_key}:{days}"
    payload = await cached_json(
        key=key,
        ttl=300,
        fetch_fn=lambda: product_service.get_cross_channel_price_history(db, product_key, days),
    )
    if not payload:
        raise HTTPException(status_code=404, detail="product not found")
    return CrossChannelPriceHistoryOut(**payload)


@router.get("/export/products")
async def export_products(
    format: Literal["csv", "json"] = Query("json"),
    brand_slug: str | None = Query(None),
    is_sale: bool | None = Query(None),
    _api_key=Depends(require_api_key(scope="export", export_limited=True)),
    db: AsyncSession = Depends(get_db),
):
    fields = [
        "id",
        "product_key",
        "normalized_key",
        "name",
        "brand_slug",
        "brand_name",
        "channel_name",
        "channel_country",
        "price_krw",
        "original_price_krw",
        "discount_rate",
        "currency",
        "is_sale",
        "is_active",
        "stock_status",
        "size_scarcity",
        "is_all_time_low",
        "url",
        "image_url",
        "updated_at",
    ]

    async def generate_csv():
        header_buf = io.StringIO()
        writer = csv.DictWriter(header_buf, fieldnames=fields)
        writer.writeheader()
        yield header_buf.getvalue()
        async for row in product_service.iter_export_products(db, brand_slug=brand_slug, is_sale=is_sale):
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=fields)
            writer.writerow(row)
            yield buf.getvalue()
            await asyncio.sleep(0)

    async def generate_ndjson():
        async for row in product_service.iter_export_products(db, brand_slug=brand_slug, is_sale=is_sale):
            yield json.dumps(row, ensure_ascii=False) + "\n"
            await asyncio.sleep(0)

    if format == "csv":
        return StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=products.csv"},
        )
    return StreamingResponse(
        generate_ndjson(),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": "attachment; filename=products.ndjson"},
    )
