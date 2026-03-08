from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fashion_engine.database import get_db
from fashion_engine.models.product_catalog import ProductCatalog
from fashion_engine.models.product import Product
from fashion_engine.models.brand import Brand
from fashion_engine.models.price_history import PriceHistory
from fashion_engine.api.schemas import CatalogOut, CatalogDetailOut, CatalogListingOut

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _catalog_to_out(pc: ProductCatalog, brand: Brand | None) -> dict:
    return {
        "id": pc.id,
        "normalized_key": pc.normalized_key,
        "canonical_name": pc.canonical_name,
        "brand_id": pc.brand_id,
        "brand_name": brand.name if brand else None,
        "brand_slug": brand.slug if brand else None,
        "gender": pc.gender,
        "subcategory": pc.subcategory,
        "tags": pc.tags,
        "trend_score": pc.trend_score,
        "listing_count": pc.listing_count,
        "channel_count": pc.channel_count,
        "min_price_krw": pc.min_price_krw,
        "max_price_krw": pc.max_price_krw,
        "is_sale_anywhere": pc.is_sale_anywhere,
        "first_seen_at": pc.first_seen_at,
    }


@router.get("/", response_model=list[CatalogOut])
async def list_catalog(
    brand: str | None = Query(None, description="브랜드 slug 필터"),
    gender: str | None = Query(None, description="성별: men/women/unisex/kids"),
    subcategory: str | None = Query(None, description="카테고리: shoes/outer/top/..."),
    on_sale: bool | None = Query(None, description="세일 중인 제품만"),
    min_price: int | None = Query(None, ge=0, description="최소 가격(KRW)"),
    max_price: int | None = Query(None, ge=0, description="최대 가격(KRW)"),
    q: str | None = Query(None, description="제품명 검색어"),
    sort: str = Query("listing_count", description="정렬 기준: listing_count/min_price/first_seen_at"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[CatalogOut]:
    """ProductCatalog 목록 조회 (여러 채널에 걸쳐 집약된 정규 제품)."""
    stmt = (
        select(ProductCatalog, Brand)
        .outerjoin(Brand, Brand.id == ProductCatalog.brand_id)
    )

    if brand:
        stmt = stmt.where(Brand.slug == brand)
    if gender:
        stmt = stmt.where(ProductCatalog.gender == gender)
    if subcategory:
        stmt = stmt.where(ProductCatalog.subcategory == subcategory)
    if on_sale is True:
        stmt = stmt.where(ProductCatalog.is_sale_anywhere == True)  # noqa: E712
    if on_sale is False:
        stmt = stmt.where(
            (ProductCatalog.is_sale_anywhere == False)  # noqa: E712
            | (ProductCatalog.is_sale_anywhere.is_(None))
        )
    if min_price is not None:
        stmt = stmt.where(ProductCatalog.min_price_krw >= min_price)
    if max_price is not None:
        stmt = stmt.where(ProductCatalog.min_price_krw <= max_price)
    if q:
        stmt = stmt.where(ProductCatalog.canonical_name.ilike(f"%{q}%"))

    # 정렬
    sort_col = {
        "listing_count": desc(ProductCatalog.listing_count),
        "min_price": ProductCatalog.min_price_krw,
        "first_seen_at": desc(ProductCatalog.first_seen_at),
    }.get(sort, desc(ProductCatalog.listing_count))
    stmt = stmt.order_by(sort_col).offset(offset).limit(limit)

    rows = (await db.execute(stmt)).all()
    return [CatalogOut(**_catalog_to_out(pc, brand_obj)) for pc, brand_obj in rows]


@router.get("/{normalized_key:path}", response_model=CatalogDetailOut)
async def get_catalog_detail(
    normalized_key: str,
    db: AsyncSession = Depends(get_db),
) -> CatalogDetailOut:
    """특정 제품의 모든 채널 판매 정보 조회."""
    # ProductCatalog 조회
    pc = (await db.execute(
        select(ProductCatalog).where(ProductCatalog.normalized_key == normalized_key)
    )).scalar_one_or_none()

    if pc is None:
        raise HTTPException(status_code=404, detail=f"Catalog not found: {normalized_key}")

    brand = None
    if pc.brand_id:
        brand = (await db.execute(
            select(Brand).where(Brand.id == pc.brand_id)
        )).scalar_one_or_none()

    # 채널별 판매 목록 (최신 가격 포함)
    products = (await db.execute(
        select(Product)
        .where(Product.normalized_key == normalized_key)
        .where(Product.is_active == True)  # noqa: E712
        .options(selectinload(Product.channel))
    )).scalars().all()

    # 제품별 최신 PriceHistory 조회
    product_ids = [p.id for p in products]
    latest_prices: dict[int, PriceHistory] = {}
    if product_ids:
        # DISTINCT ON (product_id) 최신 가격
        from sqlalchemy import text
        ph_rows = (await db.execute(text("""
            SELECT DISTINCT ON (product_id)
                product_id, price, currency, is_sale, discount_rate
            FROM price_history
            WHERE product_id = ANY(:pids)
            ORDER BY product_id, crawled_at DESC
        """), {"pids": product_ids})).all()
        for row in ph_rows:
            latest_prices[row[0]] = row

    # exchange_rates로 KRW 환산
    from sqlalchemy import text as txt
    fx_rows = (await db.execute(txt(
        "SELECT from_currency, rate FROM exchange_rates WHERE to_currency = 'KRW'"
    ))).all()
    fx: dict[str, float] = {"KRW": 1.0}
    for currency, rate in fx_rows:
        fx[currency] = float(rate)

    listings: list[CatalogListingOut] = []
    for p in products:
        ph = latest_prices.get(p.id)
        price_krw = None
        is_sale = p.is_sale
        discount_rate = None
        if ph:
            rate = fx.get(ph[2], 1.0)
            raw_price_krw = int(float(ph[1]) * rate)
            if 0 < raw_price_krw <= 50_000_000:
                price_krw = raw_price_krw
            is_sale = bool(ph[3])
            discount_rate = ph[4]

        listings.append(CatalogListingOut(
            channel_id=p.channel_id,
            channel_name=p.channel.name if p.channel else "",
            channel_url=p.channel.url if p.channel else "",
            product_id=p.id,
            product_url=p.url,
            latest_price_krw=price_krw,
            is_sale=is_sale,
            discount_rate=discount_rate,
        ))

    # 가격 오름차순 정렬
    listings.sort(key=lambda x: x.latest_price_krw or 999_999_999)

    return CatalogDetailOut(
        **_catalog_to_out(pc, brand),
        listings=listings,
    )
