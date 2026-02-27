from datetime import datetime, timedelta
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
) -> tuple["Product", bool, bool]:
    """
    url 기준으로 제품 upsert.
    반환: (product, is_new, sale_just_started)
      - is_new: product_key가 이 크롤에서 처음 등장한 경우
      - sale_just_started: 이전 is_sale=False → 이번 True 전환
    """
    is_sale = info.compare_at_price is not None and info.compare_at_price > info.price

    existing = (
        await db.execute(select(Product).where(Product.url == info.product_url))
    ).scalar_one_or_none()

    if existing:
        prev_sale = existing.is_sale
        sale_just_started = (not prev_sale) and is_sale
        existing.name = info.title
        existing.product_key = info.product_key
        existing.gender = info.gender
        existing.subcategory = info.subcategory
        existing.is_sale = is_sale
        existing.is_active = info.is_available
        existing.image_url = info.image_url
        existing.updated_at = datetime.utcnow()
        return existing, False, sale_just_started
    else:
        product = Product(
            channel_id=channel_id,
            brand_id=brand_id,
            name=info.title,
            product_key=info.product_key,
            gender=info.gender,
            subcategory=info.subcategory,
            sku=info.sku,
            url=info.product_url,
            image_url=info.image_url,
            is_active=info.is_available,
            is_sale=is_sale,
        )
        db.add(product)
        await db.flush()  # id 확보
        return product, True, False


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
    gender: str | None = None,
    category: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
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
    if gender:
        query = query.where(Product.gender == gender)
    if category:
        query = query.where(Product.subcategory == category)
    if min_price is not None:
        query = query.where(latest_price.c.price >= min_price)
    if max_price is not None:
        query = query.where(latest_price.c.price <= max_price)

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


async def get_sale_highlights(
    db: AsyncSession,
    gender: str | None = None,
    category: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    limit: int = 120,
    offset: int = 0,
) -> list[dict]:
    """세일 제품 하이라이트 (세일율/가격/채널 포함)."""
    latest_sub = (
        select(
            PriceHistory.product_id,
            func.max(PriceHistory.crawled_at).label("latest"),
        )
        .group_by(PriceHistory.product_id)
        .subquery()
    )

    query = (
        select(Product, PriceHistory, Channel)
        .join(latest_sub, Product.id == latest_sub.c.product_id)
        .join(
            PriceHistory,
            (PriceHistory.product_id == Product.id)
            & (PriceHistory.crawled_at == latest_sub.c.latest),
        )
        .join(Channel, Product.channel_id == Channel.id)
        .where(Product.is_sale == True)
        .order_by(desc(PriceHistory.discount_rate), Product.name)
        .limit(limit)
        .offset(offset)
    )
    if gender:
        query = query.where(Product.gender == gender)
    if category:
        query = query.where(Product.subcategory == category)
    if min_price is not None:
        query = query.where(PriceHistory.price >= min_price)
    if max_price is not None:
        query = query.where(PriceHistory.price <= max_price)

    rows = (await db.execute(query)).all()

    result: list[dict] = []
    for product, ph, channel in rows:
        result.append(
            {
                "product_id": product.id,
                "product_name": product.name,
                "product_key": product.product_key,
                "product_url": product.url,
                "image_url": product.image_url,
                "channel_name": channel.name,
                "channel_country": channel.country,
                "is_new": bool(product.is_new),
                "is_active": bool(product.is_active),
                "price_krw": int(ph.price),
                "original_price_krw": int(ph.original_price) if ph.original_price else None,
                "discount_rate": ph.discount_rate,
            }
        )
    return result


async def get_sale_products_count(db: AsyncSession) -> int:
    """현재 세일 제품 총 개수."""
    result = await db.execute(select(func.count(Product.id)).where(Product.is_sale == True))
    return int(result.scalar_one() or 0)


async def get_sale_products_count_filtered(
    db: AsyncSession,
    gender: str | None = None,
    category: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
) -> int:
    latest_sub = (
        select(
            PriceHistory.product_id,
            func.max(PriceHistory.crawled_at).label("latest"),
        )
        .group_by(PriceHistory.product_id)
        .subquery()
    )
    query = (
        select(func.count(Product.id))
        .join(latest_sub, Product.id == latest_sub.c.product_id)
        .join(
            PriceHistory,
            (PriceHistory.product_id == Product.id)
            & (PriceHistory.crawled_at == latest_sub.c.latest),
        )
        .where(Product.is_sale == True)
    )
    if gender:
        query = query.where(Product.gender == gender)
    if category:
        query = query.where(Product.subcategory == category)
    if min_price is not None:
        query = query.where(PriceHistory.price >= min_price)
    if max_price is not None:
        query = query.where(PriceHistory.price <= max_price)

    result = await db.execute(query)
    return int(result.scalar_one() or 0)


async def get_related_searches(
    db: AsyncSession, q: str, limit: int = 8
) -> list[str]:
    """
    검색어 기준 연관검색어 생성.
    - 매칭 제품의 브랜드명 상위
    - 매칭 제품명에서 자주 등장한 키워드
    """
    query = q.strip().lower()
    if not query:
        return []

    rows = (
        await db.execute(
            select(Product.name, Brand.name)
            .join(Brand, Product.brand_id == Brand.id, isouter=True)
            .where(Product.name.ilike(f"%{query}%"))
            .limit(300)
        )
    ).all()

    if not rows:
        brand_rows = (
            await db.execute(
                select(Brand.name)
                .where((Brand.name.ilike(f"%{query}%")) | (Brand.slug.ilike(f"%{query}%")))
                .limit(limit)
            )
        ).all()
        return [name for (name,) in brand_rows if name][:limit]

    suggestions: list[str] = []
    seen: set[str] = set()

    # 1) 브랜드명 기반
    brand_freq: dict[str, int] = {}
    for _, brand_name in rows:
        if not brand_name:
            continue
        key = brand_name.strip()
        if not key:
            continue
        brand_freq[key] = brand_freq.get(key, 0) + 1

    for brand_name, _ in sorted(brand_freq.items(), key=lambda x: x[1], reverse=True):
        if brand_name.lower() == query:
            continue
        if brand_name.lower() in seen:
            continue
        suggestions.append(brand_name)
        seen.add(brand_name.lower())
        if len(suggestions) >= limit:
            return suggestions

    # 2) 제품명 키워드 기반
    token_freq: dict[str, int] = {}
    for product_name, _ in rows:
        for token in product_name.replace("/", " ").replace("-", " ").split():
            cleaned = token.strip("()[]{}.,:;!?'\"").lower()
            if len(cleaned) < 2:
                continue
            if cleaned == query:
                continue
            if query in cleaned:
                continue
            token_freq[cleaned] = token_freq.get(cleaned, 0) + 1

    for token, _ in sorted(token_freq.items(), key=lambda x: x[1], reverse=True):
        keyword = f"{q} {token}"
        key = keyword.lower()
        if key in seen:
            continue
        suggestions.append(keyword)
        seen.add(key)
        if len(suggestions) >= limit:
            break

    return suggestions[:limit]


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


async def get_price_history(
    db: AsyncSession, product_key: str, days: int = 30
) -> list[dict]:
    """동일 product_key의 채널별 가격 히스토리."""
    query = (
        select(Channel.name, PriceHistory.crawled_at, PriceHistory.price, PriceHistory.is_sale)
        .join(Product, Product.id == PriceHistory.product_id)
        .join(Channel, Channel.id == Product.channel_id)
        .where(Product.product_key == product_key)
        .order_by(Channel.name.asc(), PriceHistory.crawled_at.asc())
    )

    if days > 0:
        threshold = datetime.utcnow() - timedelta(days=days)
        query = query.where(PriceHistory.crawled_at >= threshold)

    rows = (await db.execute(query)).all()
    grouped: dict[str, list[dict]] = {}

    for channel_name, crawled_at, price, is_sale in rows:
        grouped.setdefault(channel_name, []).append(
            {
                "date": crawled_at.strftime("%Y-%m-%d"),
                "price_krw": int(price),
                "is_sale": bool(is_sale),
            }
        )

    return [
        {"channel_name": channel_name, "history": history}
        for channel_name, history in grouped.items()
        if history
    ]


async def get_brand_products(
    db: AsyncSession,
    brand_slug: str,
    is_sale: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Product]:
    """브랜드별 제품 목록."""
    query = (
        select(Product)
        .join(Brand, Product.brand_id == Brand.id)
        .options(selectinload(Product.channel), selectinload(Product.brand))
        .where(Brand.slug == brand_slug)
        .order_by(desc(Product.is_sale), Product.name)
        .limit(limit)
        .offset(offset)
    )
    if is_sale is not None:
        query = query.where(Product.is_sale == is_sale)
    result = await db.execute(query)
    return list(result.scalars().all())
