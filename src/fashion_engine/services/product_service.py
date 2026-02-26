from datetime import datetime
from decimal import Decimal

from slugify import slugify
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fashion_engine.crawler.product_crawler import ProductInfo
from fashion_engine.models.brand import Brand
from fashion_engine.models.channel import Channel
from fashion_engine.models.exchange_rate import ExchangeRate
from fashion_engine.models.price_history import PriceHistory
from fashion_engine.models.product import Product


# ── 환율 조회 ────────────────────────────────────────────────────────────

async def get_rate_to_krw(db: AsyncSession, currency: str) -> float:
    """currency → KRW 환율. KRW면 1.0, 없으면 1.0 fallback."""
    if currency == "KRW":
        return 1.0
    row = (
        await db.execute(
            select(ExchangeRate).where(
                ExchangeRate.from_currency == currency,
                ExchangeRate.to_currency == "KRW",
            )
        )
    ).scalar_one_or_none()
    return row.rate if row else 1.0


# ── 브랜드 조회 (vendor명으로) ────────────────────────────────────────────

async def find_brand_by_vendor(db: AsyncSession, vendor: str) -> Brand | None:
    """Shopify vendor 이름으로 Brand 찾기 (slug 기반)."""
    slug = slugify(vendor)
    return (
        await db.execute(select(Brand).where(Brand.slug == slug))
    ).scalar_one_or_none()


# ── 제품 upsert ───────────────────────────────────────────────────────────

async def upsert_product(
    db: AsyncSession,
    channel_id: int,
    info: ProductInfo,
    brand_id: int | None = None,
) -> Product:
    """
    url 기준으로 제품 upsert.
    - 신규: 생성 후 반환
    - 기존: is_sale, image_url 등 최신 상태로 업데이트
    """
    is_sale = info.compare_at_price is not None and info.compare_at_price > info.price
    discount_rate: int | None = None
    if is_sale and info.compare_at_price:
        discount_rate = round((1 - info.price / info.compare_at_price) * 100)

    existing = (
        await db.execute(select(Product).where(Product.url == info.product_url))
    ).scalar_one_or_none()

    if existing:
        existing.name = info.title
        existing.product_key = info.product_key
        existing.is_sale = is_sale
        existing.image_url = info.image_url
        existing.updated_at = datetime.utcnow()
        product = existing
    else:
        product = Product(
            channel_id=channel_id,
            brand_id=brand_id,
            name=info.title,
            product_key=info.product_key,
            sku=info.sku,
            url=info.product_url,
            image_url=info.image_url,
            is_sale=is_sale,
        )
        db.add(product)
        await db.flush()  # id 확보

    return product


async def record_price(
    db: AsyncSession,
    product_id: int,
    info: ProductInfo,
    rate_to_krw: float,
) -> PriceHistory:
    """
    가격 이력 INSERT (항상 새 레코드 — 시계열 추적).
    price, original_price는 KRW 환산값으로 저장.
    """
    is_sale = info.compare_at_price is not None and info.compare_at_price > info.price
    discount_rate: int | None = None
    if is_sale and info.compare_at_price:
        discount_rate = round((1 - info.price / info.compare_at_price) * 100)

    price_krw = Decimal(str(round(info.price * rate_to_krw)))
    original_krw = (
        Decimal(str(round(info.compare_at_price * rate_to_krw)))
        if info.compare_at_price
        else None
    )

    ph = PriceHistory(
        product_id=product_id,
        price=price_krw,
        original_price=original_krw,
        currency="KRW",
        is_sale=is_sale,
        discount_rate=discount_rate,
        crawled_at=datetime.utcnow(),
    )
    db.add(ph)
    return ph


# ── 조회 함수 ─────────────────────────────────────────────────────────────

async def get_sale_products(
    db: AsyncSession,
    brand_slug: str | None = None,
    tier: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Product]:
    """세일 중인 제품 목록 (최신 가격 기준 할인율 내림차순)."""
    # 최신 PriceHistory subquery
    latest_ph = (
        select(
            PriceHistory.product_id,
            func.max(PriceHistory.crawled_at).label("latest"),
        )
        .group_by(PriceHistory.product_id)
        .subquery()
    )
    latest_price = (
        select(PriceHistory)
        .join(
            latest_ph,
            (PriceHistory.product_id == latest_ph.c.product_id)
            & (PriceHistory.crawled_at == latest_ph.c.latest),
        )
        .subquery()
    )

    query = (
        select(Product)
        .join(latest_price, Product.id == latest_price.c.product_id)
        .options(selectinload(Product.channel), selectinload(Product.brand))
        .where(Product.is_sale == True)
        .order_by(desc(latest_price.c.discount_rate))
        .limit(limit)
        .offset(offset)
    )

    if brand_slug:
        query = query.join(Brand, Product.brand_id == Brand.id).where(
            Brand.slug == brand_slug
        )
    if tier:
        if not brand_slug:
            query = query.join(Brand, Product.brand_id == Brand.id)
        query = query.where(Brand.tier == tier)

    return list((await db.execute(query)).scalars().all())


async def search_products(
    db: AsyncSession, q: str, limit: int = 30
) -> list[Product]:
    """제품명 검색."""
    pct = f"%{q}%"
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.channel), selectinload(Product.brand))
        .where(Product.name.ilike(pct))
        .order_by(Product.name)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_price_comparison(
    db: AsyncSession, product_key: str
) -> list[dict]:
    """
    동일 product_key를 가진 모든 채널 제품의 최신 가격 비교.
    KRW 기준 오름차순 정렬.
    """
    # 각 product별 최신 PriceHistory
    latest_sub = (
        select(
            PriceHistory.product_id,
            func.max(PriceHistory.crawled_at).label("latest"),
        )
        .group_by(PriceHistory.product_id)
        .subquery()
    )

    rows = (
        await db.execute(
            select(Product, PriceHistory, Channel)
            .join(
                latest_sub,
                (Product.id == latest_sub.c.product_id),
            )
            .join(
                PriceHistory,
                (PriceHistory.product_id == Product.id)
                & (PriceHistory.crawled_at == latest_sub.c.latest),
            )
            .join(Channel, Product.channel_id == Channel.id)
            .where(Product.product_key == product_key)
            .order_by(PriceHistory.price)
        )
    ).all()

    listings = []
    for product, ph, channel in rows:
        listings.append(
            {
                "channel_name": channel.name,
                "channel_country": channel.country,
                "channel_url": channel.url,
                "price_krw": int(ph.price),
                "original_price_krw": int(ph.original_price) if ph.original_price else None,
                "is_sale": ph.is_sale,
                "discount_rate": ph.discount_rate,
                "product_url": product.url,
                "image_url": product.image_url,
            }
        )
    return listings


async def get_brand_products(
    db: AsyncSession,
    brand_slug: str,
    limit: int = 100,
    offset: int = 0,
) -> list[Product]:
    """브랜드별 제품 목록."""
    result = await db.execute(
        select(Product)
        .join(Brand, Product.brand_id == Brand.id)
        .options(selectinload(Product.channel), selectinload(Product.brand))
        .where(Brand.slug == brand_slug)
        .order_by(Product.name)
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())
