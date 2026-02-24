from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fashion_engine.models.channel import Channel
from fashion_engine.models.brand import Brand
from fashion_engine.models.channel_brand import ChannelBrand


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
