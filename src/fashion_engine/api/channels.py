from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.database import get_db
from fashion_engine.services import channel_service, brand_service
from fashion_engine.api.schemas import ChannelOut, ChannelWithBrands, BrandOut

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("/", response_model=list[ChannelOut])
async def list_channels(db: AsyncSession = Depends(get_db)):
    """전체 판매채널 목록"""
    return await channel_service.get_all_channels(db)


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
