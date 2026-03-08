from datetime import datetime

from slugify import slugify
from sqlalchemy import case, extract, func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.models.brand import Brand
from fashion_engine.models.channel import Channel
from fashion_engine.models.channel_brand import ChannelBrand
from fashion_engine.models.price_history import PriceHistory
from fashion_engine.models.product import Product


async def get_all_brands(db: AsyncSession) -> list[Brand]:
    result = await db.execute(select(Brand).order_by(Brand.name))
    return list(result.scalars().all())


async def get_brands_by_tier(db: AsyncSession, tier: str) -> list[Brand]:
    """티어별 브랜드 목록"""
    result = await db.execute(
        select(Brand).where(Brand.tier == tier).order_by(Brand.name)
    )
    return list(result.scalars().all())


async def get_brand_by_slug(db: AsyncSession, slug: str) -> Brand | None:
    result = await db.execute(select(Brand).where(Brand.slug == slug))
    return result.scalar_one_or_none()


async def search_brands(db: AsyncSession, query: str) -> list[Brand]:
    q = f"%{query}%"
    result = await db.execute(
        select(Brand)
        .where(or_(Brand.name.ilike(q), Brand.name_ko.ilike(q)))
        .order_by(Brand.name)
        .limit(50)
    )
    return list(result.scalars().all())


async def get_channels_by_brand(db: AsyncSession, brand_id: int) -> list[Channel]:
    """특정 브랜드를 취급하는 채널 목록"""
    result = await db.execute(
        select(Channel)
        .join(ChannelBrand, ChannelBrand.channel_id == Channel.id)
        .where(ChannelBrand.brand_id == brand_id)
        .where(Channel.is_active == True)
        .order_by(Channel.name)
    )
    return list(result.scalars().all())


async def get_brand_highlights(
    db: AsyncSession,
    limit: int = 300,
    offset: int = 0,
) -> list[dict]:
    """브랜드별 하이라이트(신상품 판매 여부)."""
    rows = (
        await db.execute(
            select(
                Brand.id,
                Brand.name,
                Brand.slug,
                Brand.instagram_url,
                Brand.tier,
                Brand.origin_country,
                func.count(Product.id).label("total_product_count"),
                func.sum(case((Product.is_new == True, 1), else_=0)).label("new_product_count"),
            )
            .outerjoin(Product, Product.brand_id == Brand.id)
            .group_by(Brand.id)
            .order_by(
                func.sum(case((Product.is_new == True, 1), else_=0)).desc(),
                func.count(Product.id).desc(),
                Brand.name.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
    ).all()

    result: list[dict] = []
    for row in rows:
        new_count = int(row.new_product_count or 0)
        result.append(
            {
                "brand_id": row.id,
                "brand_name": row.name,
                "brand_slug": row.slug,
                "instagram_url": row.instagram_url,
                "tier": row.tier,
                "origin_country": row.origin_country,
                "total_product_count": int(row.total_product_count or 0),
                "new_product_count": new_count,
                "is_selling_new_products": new_count > 0,
            }
        )
    return result


async def upsert_brand(db: AsyncSession, name: str, name_ko: str | None = None) -> Brand:
    """브랜드 생성 또는 조회 (slug 기준 + 숫자 토큰 기반 보정)"""
    slug = slugify(name)
    result = await db.execute(select(Brand).where(Brand.slug == slug))
    brand = result.scalar_one_or_none()

    # 한글/영문 표기가 다른 동일 브랜드 보정:
    # 예) 1017-alyx-9sm vs 1017-alrigseu-9sm
    # 숫자가 포함된 토큰이 2개 이상이면 해당 토큰이 모두 일치하는 기존 slug를 재사용.
    if not brand:
        digit_tokens = [token for token in slug.split("-") if any(ch.isdigit() for ch in token)]
        if len(digit_tokens) >= 2:
            query = select(Brand)
            for token in digit_tokens:
                query = query.where(Brand.slug.ilike(f"%{token}%"))
            candidates = list((await db.execute(query)).scalars().all())
            if len(candidates) == 1:
                brand = candidates[0]

    if not brand:
        brand = Brand(name=name, slug=slug, name_ko=name_ko)
        db.add(brand)
        await db.commit()
        await db.refresh(brand)

    return brand


async def link_brand_to_channel(
    db: AsyncSession,
    brand_id: int,
    channel_id: int,
    cate_no: str | None = None,
) -> None:
    """채널-브랜드 관계 연결 (중복 무시)"""
    result = await db.execute(
        select(ChannelBrand).where(
            ChannelBrand.brand_id == brand_id,
            ChannelBrand.channel_id == channel_id,
        )
    )
    existing = result.scalar_one_or_none()

    if not existing:
        link = ChannelBrand(
            brand_id=brand_id,
            channel_id=channel_id,
            cate_no=cate_no,
            crawled_at=datetime.utcnow(),
        )
        db.add(link)
        await db.commit()
    elif cate_no and existing.cate_no != cate_no:
        existing.cate_no = cate_no
        existing.crawled_at = datetime.utcnow()
        await db.commit()


async def get_brand_sale_intel(db: AsyncSession, brand_slug: str) -> dict | None:
    brand = await get_brand_by_slug(db, brand_slug)
    if not brand:
        return None

    current_stats = (
        await db.execute(
            select(
                func.count(Product.id).label("sale_count"),
                func.max(Product.discount_rate).label("max_discount"),
                func.max(Product.sale_started_at).label("last_sale_started_at"),
            )
            .where(
                Product.brand_id == brand.id,
                Product.is_active == True,  # noqa: E712
                Product.is_sale == True,  # noqa: E712
            )
        )
    ).one()

    sale_channel_rows = (
        await db.execute(
            select(
                Channel.name.label("channel_name"),
                Channel.url.label("url"),
                func.count(Product.id).label("products_on_sale"),
            )
            .join(Product, Product.channel_id == Channel.id)
            .where(
                Product.brand_id == brand.id,
                Product.is_active == True,  # noqa: E712
                Product.is_sale == True,  # noqa: E712
            )
            .group_by(Channel.id)
            .order_by(func.count(Product.id).desc(), Channel.name.asc())
        )
    ).all()

    monthly_rows = (
        await db.execute(
            select(
                extract("year", PriceHistory.crawled_at).label("year"),
                extract("month", PriceHistory.crawled_at).label("month"),
                func.count(func.distinct(PriceHistory.product_id)).label("product_count"),
                func.avg(PriceHistory.discount_rate).label("avg_discount"),
            )
            .join(Product, Product.id == PriceHistory.product_id)
            .where(
                Product.brand_id == brand.id,
                PriceHistory.is_sale == True,  # noqa: E712
            )
            .group_by(
                extract("year", PriceHistory.crawled_at),
                extract("month", PriceHistory.crawled_at),
            )
            .order_by(
                extract("year", PriceHistory.crawled_at).desc(),
                extract("month", PriceHistory.crawled_at).desc(),
            )
            .limit(12)
        )
    ).all()

    month_totals: dict[int, int] = {}
    monthly_sale_history: list[dict] = []
    for row in monthly_rows:
        month_num = int(row.month or 0)
        year_num = int(row.year or 0)
        month_totals[month_num] = month_totals.get(month_num, 0) + int(row.product_count or 0)
        monthly_sale_history.append(
            {
                "month": f"{year_num:04d}-{month_num:02d}",
                "product_count": int(row.product_count or 0),
                "avg_discount": round(float(row.avg_discount), 1) if row.avg_discount is not None else None,
            }
        )

    typical_sale_months = [
        month
        for month, _count in sorted(month_totals.items(), key=lambda item: (-item[1], item[0]))[:4]
        if month > 0
    ]

    return {
        "brand_slug": brand.slug,
        "brand_name": brand.name,
        "is_currently_on_sale": int(current_stats.sale_count or 0) > 0,
        "current_sale_products": int(current_stats.sale_count or 0),
        "current_max_discount_rate": (
            int(current_stats.max_discount) if current_stats.max_discount is not None else None
        ),
        "sale_channels": [
            {
                "channel_name": row.channel_name,
                "url": row.url,
                "products_on_sale": int(row.products_on_sale or 0),
            }
            for row in sale_channel_rows
        ],
        "monthly_sale_history": monthly_sale_history,
        "last_sale_started_at": current_stats.last_sale_started_at,
        "typical_sale_months": typical_sale_months,
    }
