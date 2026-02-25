from datetime import datetime

from slugify import slugify
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.models.brand import Brand
from fashion_engine.models.channel import Channel
from fashion_engine.models.channel_brand import ChannelBrand


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


async def upsert_brand(db: AsyncSession, name: str, name_ko: str | None = None) -> Brand:
    """브랜드 생성 또는 조회 (slug 기준)"""
    slug = slugify(name)
    result = await db.execute(select(Brand).where(Brand.slug == slug))
    brand = result.scalar_one_or_none()

    if not brand:
        brand = Brand(name=name, slug=slug, name_ko=name_ko)
        db.add(brand)
        await db.commit()
        await db.refresh(brand)

    return brand


async def link_brand_to_channel(db: AsyncSession, brand_id: int, channel_id: int) -> None:
    """채널-브랜드 관계 연결 (중복 무시)"""
    result = await db.execute(
        select(ChannelBrand).where(
            ChannelBrand.brand_id == brand_id,
            ChannelBrand.channel_id == channel_id,
        )
    )
    existing = result.scalar_one_or_none()

    if not existing:
        link = ChannelBrand(brand_id=brand_id, channel_id=channel_id, crawled_at=datetime.utcnow())
        db.add(link)
        await db.commit()
