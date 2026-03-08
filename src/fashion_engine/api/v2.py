from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

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


@router.get("/search", response_model=list[SearchV2ItemOut])
async def search_v2(
    q: str = Query(..., min_length=1),
    mode: str = Query("keyword", pattern="^(keyword|semantic)$"),
    limit: int = Query(20, ge=1, le=50),
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
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
    db: AsyncSession = Depends(get_db),
):
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
