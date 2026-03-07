from datetime import datetime, timedelta
from decimal import Decimal
import logging

from slugify import slugify
from sqlalchemy import select, func, desc, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fashion_engine.crawler.product_crawler import ProductInfo
from fashion_engine.models.brand import Brand
from fashion_engine.models.channel import Channel
from fashion_engine.models.exchange_rate import ExchangeRate
from fashion_engine.models.price_history import PriceHistory
from fashion_engine.models.product import Product

logger = logging.getLogger(__name__)

# ── 환율 조회 ────────────────────────────────────────────────────────────

_FALLBACK_RATES: dict[str, float] = {
    "USD": 1400.0,
    "EUR": 1680.0,
    "GBP": 1930.0,
    "JPY": 9.0,
    "HKD": 182.0,
    "SGD": 1130.0,
    "CNY": 207.0,
    "AUD": 1020.0,
    "CAD": 1050.0,
    "TWD": 45.0,
    "DKK": 228.0,
    "SEK": 159.0,
}


async def get_rate_to_krw(db: AsyncSession, currency: str) -> float | None:
    """currency → KRW 환율. 미등록 시 하드코딩 fallback, 알 수 없는 통화는 None."""
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
    if row:
        rate = row.rate
        fallback = _FALLBACK_RATES.get(currency.upper())
        # sanity: DB 환율이 fallback 대비 5배 이상 차이나면 fallback 사용
        if fallback and (rate > fallback * 5 or rate < fallback / 5):
            logger.error(
                "환율 이상값 감지: %s DB=%.4f fallback=%.1f → fallback 적용",
                currency, rate, fallback,
            )
            return fallback
        return rate
    fallback = _FALLBACK_RATES.get(currency.upper())
    if fallback:
        logger.warning(
            "환율 DB 미등록: %s → 하드코딩 fallback %.1f 적용 (정확도 낮음)",
            currency,
            fallback,
        )
        return fallback
    logger.error("알 수 없는 통화: %s — 가격 저장 스킵", currency)
    return None


# ── 브랜드 조회 (vendor명으로) ────────────────────────────────────────────

async def find_brand_by_vendor(db: AsyncSession, vendor: str) -> Brand | None:
    """Shopify vendor 이름으로 Brand 찾기 (slug 기반)."""
    slug = slugify(vendor)
    return (
        await db.execute(select(Brand).where(Brand.slug == slug))
    ).scalar_one_or_none()


async def find_brands_by_vendors(
    db: AsyncSession,
    vendors: list[str],
) -> dict[str, Brand | None]:
    """vendor 목록을 slug로 정규화해 일괄 조회한다."""
    slug_to_vendor: dict[str, str] = {}
    for vendor in vendors:
        if not vendor:
            continue
        slug = slugify(vendor)
        if slug:
            slug_to_vendor.setdefault(slug, vendor)

    if not slug_to_vendor:
        return {}

    rows = (
        await db.execute(select(Brand).where(Brand.slug.in_(list(slug_to_vendor.keys()))))
    ).scalars().all()
    brand_by_slug = {brand.slug: brand for brand in rows}
    return {
        vendor: brand_by_slug.get(slugify(vendor))
        for vendor in vendors
        if vendor
    }


async def get_existing_products_by_urls(
    db: AsyncSession,
    urls: list[str],
) -> dict[str, Product]:
    """url 목록의 기존 Product를 한 번에 조회한다."""
    clean_urls = [url for url in urls if url]
    if not clean_urls:
        return {}

    rows = (
        await db.execute(select(Product).where(Product.url.in_(clean_urls)))
    ).scalars().all()
    return {row.url: row for row in rows}


async def get_prev_prices_by_product_ids(
    db: AsyncSession,
    product_ids: list[int],
) -> dict[int, int]:
    """제품별 현재 KRW 가격을 한 번에 조회한다."""
    clean_ids = [pid for pid in product_ids if pid]
    if not clean_ids:
        return {}
    rows = (
        await db.execute(
            select(Product.id, Product.price_krw)
            .where(Product.id.in_(clean_ids), Product.price_krw.is_not(None))
        )
    ).all()
    return {int(product_id): int(price) for product_id, price in rows}


# ── 제품 upsert ───────────────────────────────────────────────────────────


def build_product_upsert_row(
    channel_id: int,
    info: ProductInfo,
    rate_to_krw: float | None,
    brand_id: int | None = None,
    existing: Product | None = None,
    now: datetime | None = None,
) -> tuple[dict, bool, bool, str | None]:
    """Product upsert용 row와 상태 메타데이터를 만든다."""
    row_now = now or datetime.utcnow()
    is_sale = info.compare_at_price is not None and info.compare_at_price > info.price
    discount_rate: int | None = None
    if is_sale and info.compare_at_price:
        discount_rate = round((1 - info.price / info.compare_at_price) * 100)
    price_krw = _to_krw_int(info.price, rate_to_krw)
    original_price_krw = (
        _to_krw_int(info.compare_at_price, rate_to_krw)
        if info.compare_at_price
        else None
    )
    currency = (info.currency or "KRW").upper()[:3]
    raw_price = Decimal(str(info.price))

    if existing:
        prev_sale = bool(existing.is_sale)
        sale_just_started = (not prev_sale) and is_sale
        was_active = bool(existing.is_active)
        availability_transition: str | None = None
        archived_at = existing.archived_at
        sale_started_at = existing.sale_started_at

        if was_active and not info.is_available:
            archived_at = row_now
            availability_transition = "sold_out"
        elif info.is_available:
            archived_at = None
            if not was_active:
                availability_transition = "restock"
        if sale_just_started:
            sale_started_at = row_now
        elif not is_sale:
            sale_started_at = None

        return (
            {
                "channel_id": channel_id,
                "brand_id": brand_id,
                "name": info.title,
                "vendor": info.vendor or None,
                "product_key": info.product_key,
                "normalized_key": info.normalized_key,
                "match_confidence": info.match_confidence,
                "gender": info.gender,
                "subcategory": info.subcategory,
                "sku": info.sku,
                "tags": info.tags,
                "url": info.product_url,
                "image_url": info.image_url,
                "price_krw": price_krw if price_krw is not None else existing.price_krw,
                "original_price_krw": (
                    original_price_krw
                    if original_price_krw is not None or not is_sale
                    else existing.original_price_krw
                ),
                "discount_rate": discount_rate,
                "currency": currency,
                "raw_price": raw_price,
                "price_updated_at": row_now,
                "sale_started_at": sale_started_at,
                "is_active": info.is_available,
                "is_sale": is_sale,
                "archived_at": archived_at,
                "updated_at": row_now,
            },
            False,
            sale_just_started,
            availability_transition,
        )

    return (
        {
            "channel_id": channel_id,
            "brand_id": brand_id,
            "name": info.title,
            "vendor": info.vendor or None,
            "product_key": info.product_key,
            "normalized_key": info.normalized_key,
            "match_confidence": info.match_confidence,
            "gender": info.gender,
            "subcategory": info.subcategory,
            "sku": info.sku,
            "tags": info.tags,
            "url": info.product_url,
            "image_url": info.image_url,
            "price_krw": price_krw,
            "original_price_krw": original_price_krw,
            "discount_rate": discount_rate,
            "currency": currency,
            "raw_price": raw_price,
            "price_updated_at": row_now,
            "sale_started_at": row_now if is_sale else None,
            "is_active": info.is_available,
            "is_sale": is_sale,
            "archived_at": None if info.is_available else row_now,
            "created_at": row_now,
            "updated_at": row_now,
        },
        True,
        False,
        None,
)


def _to_krw_int(value: float | Decimal | None, rate_to_krw: float | None) -> int | None:
    if value is None or rate_to_krw is None:
        return None
    price_krw_int = round(float(value) * rate_to_krw)
    if price_krw_int < 1_000 or price_krw_int > 50_000_000:
        return None
    return price_krw_int


def build_price_history_row(
    product_id: int,
    info: ProductInfo,
    rate_to_krw: float | None,
    crawled_at: datetime | None = None,
) -> dict | None:
    """PriceHistory insert용 row를 만든다."""
    if rate_to_krw is None:
        logger.warning("rate=None → 가격 저장 스킵 (product_id=%d)", product_id)
        return None

    is_sale = info.compare_at_price is not None and info.compare_at_price > info.price
    discount_rate: int | None = None
    if is_sale and info.compare_at_price:
        discount_rate = round((1 - info.price / info.compare_at_price) * 100)

    price_krw_int = _to_krw_int(info.price, rate_to_krw)
    if price_krw_int is None:
        logger.warning(
            "비현실적 가격 감지: product_id=%d, price=%s %s (rate=%.2f) → %d KRW, 저장 스킵",
            product_id,
            info.price,
            info.currency,
            rate_to_krw,
            round(float(info.price) * rate_to_krw),
        )
        return None

    return {
        "product_id": product_id,
        "price": Decimal(str(price_krw_int)),
        "original_price": (
            Decimal(str(original_price_krw))
            if (original_price_krw := _to_krw_int(info.compare_at_price, rate_to_krw)) is not None
            else None
        ),
        "currency": "KRW",
        "is_sale": is_sale,
        "discount_rate": discount_rate,
        "crawled_at": crawled_at or datetime.utcnow(),
    }

async def upsert_product(
    db: AsyncSession,
    channel_id: int,
    info: ProductInfo,
    rate_to_krw: float | None,
    brand_id: int | None = None,
    existing: Product | None = None,
) -> tuple["Product", bool, bool, str | None]:
    """
    url 기준으로 제품 upsert.
    반환: (product, is_new, sale_just_started, availability_transition)
      - is_new: product_key가 이 크롤에서 처음 등장한 경우
      - sale_just_started: 이전 is_sale=False → 이번 True 전환
      - availability_transition: "sold_out" | "restock" | None
    """
    if existing is None:
        existing = (
            await db.execute(select(Product).where(Product.url == info.product_url))
        ).scalar_one_or_none()

    row, is_new, sale_just_started, availability_transition = build_product_upsert_row(
        channel_id=channel_id,
        info=info,
        rate_to_krw=rate_to_krw,
        brand_id=brand_id,
        existing=existing,
    )

    if existing:
        for key, value in row.items():
            setattr(existing, key, value)
        return existing, is_new, sale_just_started, availability_transition

    product = Product(**row)
    db.add(product)
    await db.flush()  # id 확보
    return product, is_new, sale_just_started, availability_transition


async def record_price(
    db: AsyncSession,
    product_id: int,
    info: ProductInfo,
    rate_to_krw: float | None,
) -> PriceHistory | None:
    """
    가격 이력 INSERT (항상 새 레코드 — 시계열 추적).
    price, original_price는 KRW 환산값으로 저장.
    """
    row = build_price_history_row(product_id, info, rate_to_krw)
    if row is None:
        return None

    ph = PriceHistory(**row)
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
    """세일 중인 제품 목록 (products 현재 가격 기준 할인율 내림차순)."""
    query = (
        select(Product)
        .options(selectinload(Product.channel), selectinload(Product.brand))
        .where(
            Product.is_sale == True,
            Product.is_active == True,
            Product.price_krw.is_not(None),
        )
        .order_by(
            desc(Product.discount_rate).nullslast(),
            Product.price_krw.asc(),
        )
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
        query = query.where(Product.price_krw >= min_price)
    if max_price is not None:
        query = query.where(Product.price_krw <= max_price)

    return list((await db.execute(query)).scalars().all())


async def search_products(
    db: AsyncSession, q: str, limit: int = 30
) -> list[Product]:
    """제품명 검색."""
    pct = f"%{q}%"
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.channel), selectinload(Product.brand))
        .where(Product.name.ilike(pct), Product.is_active == True)
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
    """세일 제품 하이라이트 (product_key 기준 최저가 1건 + 채널 수)."""
    dedup_key = func.coalesce(Product.product_key, cast(Product.id, String))
    ranked = (
        select(Product, Channel)
        .join(Channel, Product.channel_id == Channel.id)
        .where(
            Product.is_sale == True,
            Product.is_active == True,
            Product.price_krw.is_not(None),
        )
        .with_only_columns(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.product_key.label("product_key"),
            Product.url.label("product_url"),
            Product.image_url.label("image_url"),
            Product.is_new.label("is_new"),
            Product.is_active.label("is_active"),
            Channel.name.label("channel_name"),
            Channel.country.label("channel_country"),
            Product.price_krw.label("price_krw"),
            Product.original_price_krw.label("original_price_krw"),
            Product.discount_rate.label("discount_rate"),
            func.count(Product.id).over(partition_by=dedup_key).label("total_channels"),
            func.row_number()
            .over(
                partition_by=dedup_key,
                order_by=(Product.price_krw.asc(), Product.id.asc()),
            )
            .label("price_rank"),
        )
    )
    if gender:
        ranked = ranked.where(Product.gender == gender)
    if category:
        ranked = ranked.where(Product.subcategory == category)
    if min_price is not None:
        ranked = ranked.where(Product.price_krw >= min_price)
    if max_price is not None:
        ranked = ranked.where(Product.price_krw <= max_price)

    ranked_sub = ranked.subquery()
    rows = (
        await db.execute(
            select(ranked_sub)
            .where(ranked_sub.c.price_rank == 1)
            .order_by(desc(ranked_sub.c.discount_rate), ranked_sub.c.product_name.asc())
            .limit(limit)
            .offset(offset)
        )
    ).all()

    result: list[dict] = []
    for row in rows:
        result.append(
            {
                "product_id": row.product_id,
                "product_name": row.product_name,
                "product_key": row.product_key,
                "product_url": row.product_url,
                "image_url": row.image_url,
                "channel_name": row.channel_name,
                "channel_country": row.channel_country,
                "is_new": bool(row.is_new),
                "is_active": bool(row.is_active),
                "price_krw": int(row.price_krw),
                "original_price_krw": int(row.original_price_krw) if row.original_price_krw else None,
                "discount_rate": row.discount_rate,
                "total_channels": int(row.total_channels or 1),
            }
        )
    return result


async def get_sale_products_count(db: AsyncSession) -> int:
    """현재 세일 제품 총 개수."""
    result = await db.execute(
        select(func.count(Product.id)).where(Product.is_sale == True, Product.is_active == True)
    )
    return int(result.scalar_one() or 0)


async def get_sale_products_count_filtered(
    db: AsyncSession,
    gender: str | None = None,
    category: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
) -> int:
    query = (
        select(func.count(Product.id))
        .where(
            Product.is_sale == True,
            Product.is_active == True,
            Product.price_krw.is_not(None),
        )
    )
    if gender:
        query = query.where(Product.gender == gender)
    if category:
        query = query.where(Product.subcategory == category)
    if min_price is not None:
        query = query.where(Product.price_krw >= min_price)
    if max_price is not None:
        query = query.where(Product.price_krw <= max_price)

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
            .where(Product.name.ilike(f"%{query}%"), Product.is_active == True)
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
) -> dict | None:
    """
    동일 product_key를 가진 모든 채널 제품의 최신 가격 비교.
    KRW 기준 오름차순 정렬.
    """
    rows = (
        await db.execute(
            select(Product, Channel, Brand)
            .join(Channel, Product.channel_id == Channel.id)
            .join(Brand, Product.brand_id == Brand.id, isouter=True)
            .where(
                Product.product_key == product_key,
                Product.is_active == True,
                Product.price_krw.is_not(None),
            )
            .order_by(Product.price_krw.asc())
        )
    ).all()

    listings = []
    product_name: str | None = None
    brand_name: str | None = None
    image_url: str | None = None
    for product, channel, brand in rows:
        if product_name is None and product.name:
            product_name = product.name
        if brand_name is None and brand and brand.name:
            brand_name = brand.name
        if image_url is None and product.image_url:
            image_url = product.image_url
        is_official = bool(
            channel.channel_type == "brand-store"
            and brand
            and (channel.name or "").strip().lower() == (brand.name or "").strip().lower()
        )
        listings.append(
            {
                "channel_name": channel.name,
                "channel_country": channel.country,
                "channel_url": channel.url,
                "channel_type": channel.channel_type,
                "is_official": is_official,
                "price_krw": int(product.price_krw),
                "original_price_krw": int(product.original_price_krw) if product.original_price_krw else None,
                "is_sale": product.is_sale,
                "discount_rate": product.discount_rate,
                "product_url": product.url,
                "image_url": product.image_url,
            }
        )
    if not listings:
        return None

    fallback_name = product_key.split(":", 1)[-1].replace("-", " ").title()
    return {
        "product_key": product_key,
        "product_name": product_name or fallback_name,
        "brand_name": brand_name,
        "image_url": image_url,
        "listings": listings,
        "cheapest_channel": listings[0]["channel_name"],
        "cheapest_price_krw": listings[0]["price_krw"],
        "total_listings": len(listings),
    }


async def get_product_keys(
    db: AsyncSession,
    limit: int | None = None,
) -> list[str]:
    query = (
        select(Product.product_key)
        .where(Product.product_key.isnot(None), Product.is_active == True)
        .distinct()
        .order_by(Product.product_key.asc())
    )
    if limit:
        query = query.limit(limit)
    rows = (await db.execute(query)).all()
    return [product_key for (product_key,) in rows if product_key]


async def get_product_ranking(
    db: AsyncSession,
    ranking_type: str,
    limit: int = 100,
) -> list[dict]:
    channel_count_sub = (
        select(
            Product.product_key.label("product_key"),
            func.count(func.distinct(Product.channel_id)).label("total_channels"),
        )
        .where(Product.product_key.isnot(None), Product.is_active == True)
        .group_by(Product.product_key)
        .subquery()
    )

    if ranking_type == "sale_hot":
        dedup_key = func.coalesce(Product.product_key, cast(Product.id, String))
        ranked = (
            select(
                Product.product_key.label("product_key"),
                Product.name.label("product_name"),
                Brand.name.label("brand_name"),
                Product.image_url.label("image_url"),
                Channel.name.label("channel_name"),
                Channel.country.label("channel_country"),
                Product.url.label("product_url"),
                Product.price_krw.label("price_krw"),
                Product.original_price_krw.label("original_price_krw"),
                Product.discount_rate.label("discount_rate"),
                func.coalesce(channel_count_sub.c.total_channels, 1).label("total_channels"),
                func.row_number()
                .over(
                    partition_by=dedup_key,
                    order_by=(Product.price_krw.asc(), Product.id.asc()),
                )
                .label("product_rank"),
            )
            .join(Channel, Channel.id == Product.channel_id)
            .join(Brand, Brand.id == Product.brand_id, isouter=True)
            .join(channel_count_sub, channel_count_sub.c.product_key == Product.product_key, isouter=True)
            .where(
                Product.is_sale == True,
                Product.is_active == True,
                Product.price_krw.is_not(None),
            )
            .subquery()
        )
        rows = (
            await db.execute(
                select(ranked)
                .where(ranked.c.product_rank == 1)
                .order_by(
                    ranked.c.discount_rate.desc().nullslast(),
                    ranked.c.total_channels.desc(),
                    ranked.c.price_krw.asc(),
                )
                .limit(limit)
            )
        ).all()
        return [
            {
                "product_key": row.product_key,
                "product_name": row.product_name,
                "brand_name": row.brand_name,
                "image_url": row.image_url,
                "channel_name": row.channel_name,
                "channel_country": row.channel_country,
                "product_url": row.product_url,
                "price_krw": int(row.price_krw),
                "original_price_krw": int(row.original_price_krw) if row.original_price_krw else None,
                "discount_rate": row.discount_rate,
                "total_channels": int(row.total_channels or 1),
                "price_drop_pct": None,
                "price_drop_krw": None,
            }
            for row in rows
        ]

    if ranking_type == "price_drop":
        threshold = datetime.utcnow() - timedelta(days=7)
        recent_sub = (
            select(
                Product.id.label("product_id"),
                Product.product_key.label("product_key"),
                Product.name.label("product_name"),
                Product.url.label("product_url"),
                Product.image_url.label("image_url"),
                Channel.name.label("channel_name"),
                Channel.country.label("channel_country"),
                Brand.name.label("brand_name"),
                PriceHistory.price.label("price_krw"),
                PriceHistory.original_price.label("original_price_krw"),
                PriceHistory.discount_rate.label("discount_rate"),
                func.row_number()
                .over(
                    partition_by=Product.id,
                    order_by=PriceHistory.crawled_at.desc(),
                )
                .label("rn"),
            )
            .join(Product, Product.id == PriceHistory.product_id)
            .join(Channel, Channel.id == Product.channel_id)
            .join(Brand, Brand.id == Product.brand_id, isouter=True)
            .where(
                Product.is_active == True,
                Product.product_key.isnot(None),
                PriceHistory.crawled_at >= threshold,
            )
            .subquery()
        )
        latest = recent_sub.alias("latest")
        prev = recent_sub.alias("prev")
        drop_expr = ((prev.c.price_krw - latest.c.price_krw) * 100.0 / prev.c.price_krw)
        ranked = (
            select(
                latest.c.product_key,
                latest.c.product_name,
                latest.c.brand_name,
                latest.c.image_url,
                latest.c.channel_name,
                latest.c.channel_country,
                latest.c.product_url,
                latest.c.price_krw,
                latest.c.original_price_krw,
                latest.c.discount_rate,
                func.coalesce(channel_count_sub.c.total_channels, 1).label("total_channels"),
                drop_expr.label("price_drop_pct"),
                (prev.c.price_krw - latest.c.price_krw).label("price_drop_krw"),
                func.row_number()
                .over(
                    partition_by=latest.c.product_key,
                    order_by=(drop_expr.desc(), latest.c.price_krw.asc()),
                )
                .label("product_rank"),
            )
            .join(
                prev,
                (prev.c.product_id == latest.c.product_id) & (prev.c.rn == 2),
            )
            .join(channel_count_sub, channel_count_sub.c.product_key == latest.c.product_key, isouter=True)
            .where(
                latest.c.rn == 1,
                prev.c.price_krw.isnot(None),
                latest.c.price_krw.isnot(None),
                prev.c.price_krw > latest.c.price_krw,
            )
            .subquery()
        )
        rows = (
            await db.execute(
                select(ranked)
                .where(ranked.c.product_rank == 1)
                .order_by(
                    ranked.c.price_drop_pct.desc(),
                    ranked.c.price_drop_krw.desc(),
                )
                .limit(limit)
            )
        ).all()
        return [
            {
                "product_key": row.product_key,
                "product_name": row.product_name,
                "brand_name": row.brand_name,
                "image_url": row.image_url,
                "channel_name": row.channel_name,
                "channel_country": row.channel_country,
                "product_url": row.product_url,
                "price_krw": int(row.price_krw),
                "original_price_krw": int(row.original_price_krw) if row.original_price_krw else None,
                "discount_rate": row.discount_rate,
                "total_channels": int(row.total_channels or 1),
                "price_drop_pct": round(float(row.price_drop_pct), 1) if row.price_drop_pct is not None else None,
                "price_drop_krw": int(row.price_drop_krw) if row.price_drop_krw is not None else None,
            }
            for row in rows
        ]

    raise ValueError(f"unknown ranking_type: {ranking_type}")


async def get_brand_sale_ranking(
    db: AsyncSession,
    limit: int = 50,
) -> list[dict]:
    rows = (
        await db.execute(
            select(
                Brand.id.label("brand_id"),
                Brand.name.label("brand_name"),
                Brand.slug.label("brand_slug"),
                Brand.tier.label("tier"),
                Brand.origin_country.label("origin_country"),
                func.count(Product.id).label("sale_product_count"),
                func.avg(Product.discount_rate).label("avg_discount_rate"),
                func.max(Product.discount_rate).label("max_discount_rate"),
                func.count(func.distinct(Product.channel_id)).label("active_channel_count"),
            )
            .join(Product, Product.brand_id == Brand.id)
            .where(
                Product.is_sale == True,
                Product.is_active == True,
                Product.discount_rate.is_not(None),
            )
            .group_by(Brand.id, Brand.name, Brand.slug, Brand.tier, Brand.origin_country)
            .order_by(
                desc(func.count(Product.id)),
                desc(func.avg(Product.discount_rate)),
                Brand.name.asc(),
            )
            .limit(limit)
        )
    ).all()
    return [
        {
            "brand_id": row.brand_id,
            "brand_name": row.brand_name,
            "brand_slug": row.brand_slug,
            "tier": row.tier,
            "origin_country": row.origin_country,
            "sale_product_count": int(row.sale_product_count or 0),
            "avg_discount_rate": round(float(row.avg_discount_rate or 0), 1),
            "max_discount_rate": int(row.max_discount_rate) if row.max_discount_rate is not None else None,
            "active_channel_count": int(row.active_channel_count or 0),
        }
        for row in rows
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
        .where(Brand.slug == brand_slug, Product.is_active == True)
        .order_by(desc(Product.is_sale), Product.name)
        .limit(limit)
        .offset(offset)
    )
    if is_sale is not None:
        query = query.where(Product.is_sale == is_sale)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_archived_products(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0,
) -> list[Product]:
    """아카이브(품절 전환) 제품 목록."""
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.channel), selectinload(Product.brand))
        .where(Product.is_active == False, Product.archived_at.isnot(None))
        .order_by(Product.archived_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_multi_channel_products(
    db: AsyncSession,
    min_channels: int = 2,
    limit: int = 100,
    offset: int = 0,
    sort: str = "spread",
) -> list[dict]:
    """멀티채널에서 판매되는 product_key 집계 목록."""
    rows = (
        await db.execute(
            select(
                Product.product_key.label("product_key"),
                func.min(Product.name).label("product_name"),
                func.min(Product.image_url).label("image_url"),
                func.count(func.distinct(Product.channel_id)).label("channel_count"),
                func.min(Product.price_krw).label("min_price"),
                func.max(Product.price_krw).label("max_price"),
            )
            .where(
                Product.product_key.isnot(None),
                Product.is_active == True,
                Product.price_krw.is_not(None),
            )
            .group_by(Product.product_key)
            .having(func.count(func.distinct(Product.channel_id)) >= min_channels)
            .having(func.min(Product.price_krw).isnot(None))
            .having(func.min(Product.price_krw) >= 10_000)
            .order_by(
                desc(func.max(Product.price_krw) - func.min(Product.price_krw))
                if sort == "spread"
                else (
                    desc(func.count(func.distinct(Product.channel_id)))
                    if sort == "channels"
                    else func.min(Product.price_krw)
                ),
            )
            .limit(limit)
            .offset(offset)
        )
    ).all()

    result: list[dict] = []
    for row in rows:
        min_price = int(row.min_price)
        max_price = int(row.max_price)
        spread = max_price - min_price
        spread_rate = round((spread / min_price) * 100, 1) if min_price > 0 else 0.0
        result.append(
            {
                "product_key": row.product_key,
                "product_name": row.product_name,
                "image_url": row.image_url,
                "channel_count": int(row.channel_count),
                "min_price_krw": min_price,
                "max_price_krw": max_price,
                "price_spread_krw": spread,
                "spread_rate_pct": spread_rate,
            }
        )
    return result
