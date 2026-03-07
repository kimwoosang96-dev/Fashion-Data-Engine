from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.database import get_db
from fashion_engine.services import product_service
from fashion_engine.api.schemas import (
    ProductOut,
    PriceComparisonOut,
    PriceComparisonItem,
    SaleHighlightOut,
    MultiChannelProductOut,
    ProductKeyOut,
    ProductRankingOut,
    SearchSuggestionOut,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/sales", response_model=list[ProductOut])
async def get_sale_products(
    brand: str | None = Query(None, description="브랜드 slug 필터"),
    tier: str | None = Query(None, description="티어 필터 (high-end/premium/street/sports)"),
    gender: str | None = Query(None, description="성별 필터: men/women/unisex/kids"),
    category: str | None = Query(None, description="카테고리 필터: shoes/top/outer/bottom/..."),
    min_price: int | None = Query(None, ge=0),
    max_price: int | None = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """현재 세일 중인 제품 목록 (할인율 높은 순)."""
    products = await product_service.get_sale_products(
        db,
        brand_slug=brand,
        tier=tier,
        gender=gender,
        category=category,
        min_price=min_price,
        max_price=max_price,
        limit=limit,
        offset=offset,
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


@router.get("/search/suggestions", response_model=list[SearchSuggestionOut])
async def search_suggestions(
    q: str = Query(..., min_length=1, max_length=50),
    limit: int = Query(8, ge=1, le=20),
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=60"
    return await product_service.search_suggestions(db, q=q, limit=limit)


@router.get("/sales-highlights", response_model=list[SaleHighlightOut])
async def get_sale_highlights(
    gender: str | None = Query(None, description="성별 필터: men/women/unisex/kids"),
    category: str | None = Query(None, description="카테고리 필터: shoes/top/outer/bottom/..."),
    min_price: int | None = Query(None, ge=0),
    max_price: int | None = Query(None, ge=0),
    limit: int = Query(120, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """세일 제품 하이라이트 (세일율 강조용)."""
    return await product_service.get_sale_highlights(
        db,
        gender=gender,
        category=category,
        min_price=min_price,
        max_price=max_price,
        limit=limit,
        offset=offset,
    )


@router.get("/sales-count")
async def get_sales_count(
    gender: str | None = Query(None, description="성별 필터"),
    category: str | None = Query(None, description="카테고리 필터"),
    min_price: int | None = Query(None, ge=0),
    max_price: int | None = Query(None, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """세일 제품 총 개수."""
    total = await product_service.get_sale_products_count_filtered(
        db,
        gender=gender,
        category=category,
        min_price=min_price,
        max_price=max_price,
    )
    return {"total": total}


@router.get("/related-searches", response_model=list[str])
async def related_searches(
    q: str = Query(..., min_length=1, description="검색어"),
    limit: int = Query(8, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """검색어 연관검색어 제안."""
    return await product_service.get_related_searches(db, q=q, limit=limit)


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
    comparison = await product_service.get_price_comparison(db, product_key=product_key)
    if not comparison:
        raise HTTPException(status_code=404, detail=f"Product not found: {product_key}")
    comparison["listings"] = [PriceComparisonItem(**item) for item in comparison["listings"]]
    return PriceComparisonOut(**comparison)


@router.get("/keys", response_model=list[ProductKeyOut])
async def list_product_keys(
    limit: int = Query(0, ge=0, le=200000),
    db: AsyncSession = Depends(get_db),
):
    keys = await product_service.get_product_keys(db, limit=limit or None)
    return [ProductKeyOut(product_key=key) for key in keys]


@router.get("/ranking", response_model=list[ProductRankingOut])
async def get_product_ranking(
    type: str = Query("sale_hot", pattern="^(sale_hot|price_drop)$"),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await product_service.get_product_ranking(db, ranking_type=type, limit=limit)


@router.get("/archive", response_model=list[ProductOut])
async def get_archived_products(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """아카이브(품절 전환) 제품 목록."""
    return await product_service.get_archived_products(db, limit=limit, offset=offset)


@router.get("/multi-channel", response_model=list[MultiChannelProductOut])
async def get_multi_channel_products(
    min_channels: int = Query(2, ge=2, le=20),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = Query("spread", description="정렬 기준: spread(가격 차이↓) / channels(채널 수↓) / min_price(최저가↑)"),
    db: AsyncSession = Depends(get_db),
):
    """동일 product_key가 여러 채널에 존재하는 경쟁 제품 목록."""
    return await product_service.get_multi_channel_products(
        db,
        min_channels=min_channels,
        limit=limit,
        offset=offset,
        sort=sort,
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
