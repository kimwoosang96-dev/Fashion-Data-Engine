from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.models.channel import Channel
from fashion_engine.models.brand import Brand
from fashion_engine.models.channel_brand import ChannelBrand
from fashion_engine.models.product import Product


async def get_all_channels(db: AsyncSession) -> list[Channel]:
    result = await db.execute(select(Channel).where(Channel.is_active == True).order_by(Channel.name))
    return list(result.scalars().all())


async def get_channel_by_id(db: AsyncSession, channel_id: int) -> Channel | None:
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    return result.scalar_one_or_none()


async def get_brands_by_channel(db: AsyncSession, channel_id: int) -> list[Brand]:
    result = await db.execute(
        select(Brand)
        .join(ChannelBrand, ChannelBrand.brand_id == Brand.id)
        .where(ChannelBrand.channel_id == channel_id)
        .order_by(Brand.name)
    )
    return list(result.scalars().all())


async def get_channel_highlights(
    db: AsyncSession,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    """채널별 하이라이트(세일/신상품 판매 여부)."""
    rows = (
        await db.execute(
            select(
                Channel.id,
                Channel.name,
                Channel.url,
                Channel.instagram_url,
                Channel.channel_type,
                Channel.country,
                func.count(Product.id).label("total_product_count"),
                func.sum(case((Product.is_sale == True, 1), else_=0)).label("sale_product_count"),
                func.sum(case((Product.is_new == True, 1), else_=0)).label("new_product_count"),
            )
            .outerjoin(Product, Product.channel_id == Channel.id)
            .where(Channel.is_active == True)
            .group_by(Channel.id)
            .order_by(
                func.sum(case((Product.is_sale == True, 1), else_=0)).desc(),
                func.sum(case((Product.is_new == True, 1), else_=0)).desc(),
                Channel.name.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
    ).all()

    result: list[dict] = []
    for row in rows:
        sale_count = int(row.sale_product_count or 0)
        new_count = int(row.new_product_count or 0)
        result.append(
            {
                "channel_id": row.id,
                "channel_name": row.name,
                "channel_url": row.url,
                "instagram_url": row.instagram_url,
                "channel_type": row.channel_type,
                "country": row.country,
                "total_product_count": int(row.total_product_count or 0),
                "sale_product_count": sale_count,
                "new_product_count": new_count,
                "is_running_sales": sale_count > 0,
                "is_selling_new_products": new_count > 0,
            }
        )
    return result


async def upsert_channel(db: AsyncSession, data: dict) -> Channel:
    """채널 생성 또는 업데이트 (url 기준)"""
    result = await db.execute(select(Channel).where(Channel.url == data["url"]))
    channel = result.scalar_one_or_none()

    if channel:
        for k, v in data.items():
            setattr(channel, k, v)
    else:
        channel = Channel(**data)
        db.add(channel)

    await db.commit()
    await db.refresh(channel)
    return channel
