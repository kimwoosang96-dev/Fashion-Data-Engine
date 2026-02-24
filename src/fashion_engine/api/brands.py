from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.database import get_db
from fashion_engine.services import brand_service
from fashion_engine.api.schemas import BrandOut, ChannelOut

router = APIRouter(prefix="/brands", tags=["brands"])


@router.get("/", response_model=list[BrandOut])
async def list_brands(db: AsyncSession = Depends(get_db)):
    """전체 브랜드 목록"""
    return await brand_service.get_all_brands(db)


@router.get("/search", response_model=list[BrandOut])
async def search_brands(
    q: str = Query(..., min_length=1, description="브랜드명 검색어"),
    db: AsyncSession = Depends(get_db),
):
    """브랜드명 검색 (한글/영문)"""
    return await brand_service.search_brands(db, q)


@router.get("/{slug}", response_model=BrandOut)
async def get_brand(slug: str, db: AsyncSession = Depends(get_db)):
    """브랜드 상세 정보"""
    brand = await brand_service.get_brand_by_slug(db, slug)
    if not brand:
        raise HTTPException(status_code=404, detail="브랜드를 찾을 수 없습니다.")
    return brand


@router.get("/{slug}/channels", response_model=list[ChannelOut])
async def get_brand_channels(slug: str, db: AsyncSession = Depends(get_db)):
    """특정 브랜드를 취급하는 판매채널 목록"""
    brand = await brand_service.get_brand_by_slug(db, slug)
    if not brand:
        raise HTTPException(status_code=404, detail="브랜드를 찾을 수 없습니다.")
    channels = await brand_service.get_channels_by_brand(db, brand.id)
    return channels
