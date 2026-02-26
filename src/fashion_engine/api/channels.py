from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.database import get_db
from fashion_engine.models.brand import Brand
from fashion_engine.models.channel import Channel
from fashion_engine.models.channel_brand import ChannelBrand
from fashion_engine.services import channel_service, brand_service
from fashion_engine.api.schemas import (
    ChannelOut,
    ChannelWithBrands,
    BrandOut,
    ChannelLandscape,
    ChannelLandscapeItem,
    ChannelHighlightOut,
)

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("/", response_model=list[ChannelOut])
async def list_channels(db: AsyncSession = Depends(get_db)):
    """전체 판매채널 목록"""
    return await channel_service.get_all_channels(db)


@router.get("/highlights", response_model=list[ChannelHighlightOut])
async def list_channel_highlights(
    limit: int = 200,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """판매채널 하이라이트 (세일/신상품 판매 여부 포함)."""
    return await channel_service.get_channel_highlights(db, limit=limit, offset=offset)


@router.get("/landscape", response_model=ChannelLandscape)
async def get_channel_landscape(db: AsyncSession = Depends(get_db)):
    """시각화용 채널 지형 데이터 (국가/타입 분포 + 브랜드 수)"""
    rows = (
        await db.execute(
            select(
                Channel.id,
                Channel.name,
                Channel.country,
                Channel.channel_type,
                func.count(func.distinct(ChannelBrand.brand_id)).label("brand_count"),
            )
            .outerjoin(ChannelBrand, ChannelBrand.channel_id == Channel.id)
            .where(Channel.is_active == True)
            .group_by(Channel.id)
            .order_by(Channel.name)
        )
    ).all()

    tier_rows = (
        await db.execute(
            select(
                ChannelBrand.channel_id,
                Brand.tier,
                func.count().label("tier_count"),
            )
            .join(Brand, Brand.id == ChannelBrand.brand_id)
            .group_by(ChannelBrand.channel_id, Brand.tier)
        )
    ).all()

    tier_map: dict[int, list[tuple[str, int]]] = {}
    for channel_id, tier, tier_count in tier_rows:
        tier_key = tier or "unknown"
        tier_map.setdefault(channel_id, []).append((tier_key, tier_count))

    channels: list[ChannelLandscapeItem] = []
    by_country: dict[str, int] = {}
    by_type: dict[str, int] = {}

    for channel_id, name, country, channel_type, brand_count in rows:
        country_key = country or "unknown"
        type_key = channel_type or "unknown"
        by_country[country_key] = by_country.get(country_key, 0) + 1
        by_type[type_key] = by_type.get(type_key, 0) + 1

        top_tiers = [
            tier for tier, _ in sorted(tier_map.get(channel_id, []), key=lambda x: x[1], reverse=True)[:2]
        ]
        channels.append(
            ChannelLandscapeItem(
                id=channel_id,
                name=name,
                country=country,
                channel_type=channel_type,
                brand_count=brand_count,
                top_tiers=top_tiers,
            )
        )

    return ChannelLandscape(
        channels=channels,
        stats={
            "by_country": by_country,
            "by_type": by_type,
        },
    )


@router.get("/{channel_id}", response_model=ChannelOut)
async def get_channel(channel_id: int, db: AsyncSession = Depends(get_db)):
    """채널 상세 정보"""
    channel = await channel_service.get_channel_by_id(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="채널을 찾을 수 없습니다.")
    return channel


@router.get("/{channel_id}/brands", response_model=list[BrandOut])
async def get_channel_brands(channel_id: int, db: AsyncSession = Depends(get_db)):
    """특정 채널이 취급하는 브랜드 목록"""
    channel = await channel_service.get_channel_by_id(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="채널을 찾을 수 없습니다.")
    return await channel_service.get_brands_by_channel(db, channel_id)
