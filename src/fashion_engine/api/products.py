from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.database import get_db
from fashion_engine.services import product_service
from fashion_engine.api.schemas import (
    ProductOut,
    PriceComparisonOut,
    PriceComparisonItem,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/sales", response_model=list[ProductOut])
async def get_sale_products(
    brand: str | None = Query(None, description="브랜드 slug 필터"),
    tier: str | None = Query(None, description="티어 필터 (high-end/premium/street/sports)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """현재 세일 중인 제품 목록 (할인율 높은 순)."""
    products = await product_service.get_sale_products(
        db, brand_slug=brand, tier=tier, limit=limit, offset=offset
    )
    return products


@router.get("/search", response_model=list[ProductOut])
async def search_products(
    q: str = Query(..., min_length=1, description="검색어"),
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """제품명 검색."""
    return await product_service.search_products(db, q=q, limit=limit)


@router.get("/compare/{product_key:path}", response_model=PriceComparisonOut)
async def compare_prices(
    product_key: str,
    db: AsyncSession = Depends(get_db),
):
    """
    동일 제품(product_key)의 전 채널 가격 비교 — 핵심 기능.
    product_key 형식: "brand-slug:product-handle"
    예: new-balance:new-balance-2002r
    """
    listings_raw = await product_service.get_price_comparison(db, product_key=product_key)

    if not listings_raw:
        raise HTTPException(status_code=404, detail=f"Product not found: {product_key}")

    listings = [PriceComparisonItem(**item) for item in listings_raw]

    # 첫 번째 제품명 사용 (price 오름차순 정렬이므로 listings[0]이 최저가)
    # product_key에서 handle 부분을 제목으로 사용 (실제 제품명은 listings에서 추출 불가)
    # → DB Product.name을 별도로 조회하는 대신 product_key의 handle 부분을 표시
    handle_part = product_key.split(":", 1)[-1] if ":" in product_key else product_key

    cheapest = listings[0] if listings else None

    return PriceComparisonOut(
        product_key=product_key,
        product_name=handle_part.replace("-", " ").title(),
        listings=listings,
        cheapest_channel=cheapest.channel_name if cheapest else None,
        cheapest_price_krw=cheapest.price_krw if cheapest else None,
        total_listings=len(listings),
    )


@router.get("/", response_model=list[ProductOut])
async def list_products(
    brand: str | None = Query(None, description="브랜드 slug"),
    is_sale: bool | None = Query(None, description="세일 필터"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """제품 목록 (브랜드/세일 필터 지원)."""
    if is_sale:
        return await product_service.get_sale_products(
            db, brand_slug=brand, limit=limit, offset=offset
        )
    if brand:
        return await product_service.get_brand_products(
            db, brand_slug=brand, limit=limit, offset=offset
        )
    # 전체 목록은 brand 필터 없이는 너무 많으므로 기본 50개 반환
    return await product_service.get_sale_products(db, limit=limit, offset=offset)
