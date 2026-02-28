from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.database import get_db
from fashion_engine.models.brand import Brand
from fashion_engine.models.brand_collaboration import BrandCollaboration
from fashion_engine.models.brand_director import BrandDirector
from fashion_engine.models.channel import Channel
from fashion_engine.models.channel_brand import ChannelBrand
from fashion_engine.services import brand_service, product_service
from fashion_engine.api.schemas import (
    BrandOut,
    BrandLandscape,
    LandscapeNode,
    LandscapeEdge,
    ChannelOut,
    ProductOut,
    BrandHighlightOut,
    CollabOut,
    BrandDirectorOut,
)

router = APIRouter(prefix="/brands", tags=["brands"])

VALID_TIERS = {"high-end", "premium", "street", "sports", "spa"}


@router.get("/landscape", response_model=BrandLandscape)
async def get_brand_landscape(db: AsyncSession = Depends(get_db)):
    """시각화용 브랜드-채널 전체 지형 데이터"""
    brands_result = await db.execute(select(Brand))
    brands = list(brands_result.scalars().all())

    edges_result = await db.execute(
        select(ChannelBrand.brand_id, ChannelBrand.channel_id, Channel.name)
        .join(Channel, Channel.id == ChannelBrand.channel_id)
    )
    edges_rows = edges_result.all()

    brand_channel_map: dict[int, list[str]] = {}
    for brand_id, channel_id, channel_name in edges_rows:
        brand_channel_map.setdefault(brand_id, []).append(channel_name)

    nodes = [
        LandscapeNode(
            id=b.id,
            name=b.name,
            slug=b.slug,
            tier=b.tier,
            channel_count=len(brand_channel_map.get(b.id, [])),
            channels=brand_channel_map.get(b.id, []),
        )
        for b in brands
    ]

    edges = [
        LandscapeEdge(brand_id=brand_id, channel_id=channel_id)
        for brand_id, channel_id, _ in edges_rows
    ]

    tier_counts: dict[str, int] = {}
    for b in brands:
        key = b.tier or "unknown"
        tier_counts[key] = tier_counts.get(key, 0) + 1

    return BrandLandscape(
        nodes=nodes,
        edges=edges,
        stats={"total_brands": len(brands), "by_tier": tier_counts},
    )


@router.get("/", response_model=list[BrandOut])
async def list_brands(
    tier: str | None = Query(None, description="티어 필터: high-end | premium | street | sports | spa"),
    db: AsyncSession = Depends(get_db),
):
    """전체 브랜드 목록 (tier 파라미터로 필터링 가능)"""
    if tier:
        if tier not in VALID_TIERS:
            raise HTTPException(status_code=400, detail=f"유효하지 않은 tier. 허용값: {', '.join(sorted(VALID_TIERS))}")
        return await brand_service.get_brands_by_tier(db, tier)
    return await brand_service.get_all_brands(db)


@router.get("/highlights", response_model=list[BrandHighlightOut])
async def list_brand_highlights(
    limit: int = Query(300, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """브랜드 하이라이트 (신상품 판매 여부 포함)."""
    return await brand_service.get_brand_highlights(db, limit=limit, offset=offset)


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


@router.get("/{slug}/products", response_model=list[ProductOut])
async def get_brand_products(
    slug: str,
    is_sale: bool | None = Query(None, description="세일 제품만 보기"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """브랜드별 제품 목록 (가격 비교용)"""
    brand = await brand_service.get_brand_by_slug(db, slug)
    if not brand:
        raise HTTPException(status_code=404, detail="브랜드를 찾을 수 없습니다.")
    return await product_service.get_brand_products(
        db,
        brand_slug=slug,
        is_sale=is_sale,
        limit=limit,
        offset=offset,
    )


@router.get("/{slug}/collabs", response_model=list[CollabOut])
async def get_brand_collabs(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """브랜드 관련 협업 목록 (release_year desc, hype_score desc)."""
    brand = await brand_service.get_brand_by_slug(db, slug)
    if not brand:
        raise HTTPException(status_code=404, detail="브랜드를 찾을 수 없습니다.")

    rows = (
        await db.execute(
            select(BrandCollaboration)
            .where(
                (BrandCollaboration.brand_a_id == brand.id)
                | (BrandCollaboration.brand_b_id == brand.id)
            )
            .order_by(
                BrandCollaboration.release_year.desc().nullslast(),
                BrandCollaboration.hype_score.desc(),
            )
        )
    ).scalars().all()
    return list(rows)


@router.get("/{slug}/directors", response_model=list[BrandDirectorOut])
async def get_brand_directors(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """브랜드 크리에이티브 디렉터 목록."""
    brand = await brand_service.get_brand_by_slug(db, slug)
    if not brand:
        raise HTTPException(status_code=404, detail="브랜드를 찾을 수 없습니다.")

    rows = (
        await db.execute(
            select(BrandDirector)
            .where(BrandDirector.brand_id == brand.id)
            .order_by(BrandDirector.start_year.desc().nullslast(), BrandDirector.id.desc())
        )
    ).scalars().all()

    return [
        BrandDirectorOut(
            id=row.id,
            brand_id=row.brand_id,
            brand_name=brand.name,
            brand_slug=brand.slug,
            name=row.name,
            role=row.role,
            start_year=row.start_year,
            end_year=row.end_year,
            note=row.note,
            created_at=row.created_at,
        )
        for row in rows
    ]
