from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.database import get_db
from fashion_engine.models.brand_collaboration import BrandCollaboration
from fashion_engine.models.channel_brand import ChannelBrand
from fashion_engine.api.schemas import CollabOut

router = APIRouter(prefix="/collabs", tags=["collabs"])


@router.get("/", response_model=list[CollabOut])
async def list_collabs(
    category: str | None = Query(None, description="카테고리 필터: footwear | apparel | accessories | lifestyle"),
    db: AsyncSession = Depends(get_db),
):
    """협업 목록 (hype_score 내림차순)"""
    query = select(BrandCollaboration).order_by(BrandCollaboration.hype_score.desc())
    if category:
        query = query.where(BrandCollaboration.collab_category == category)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/hype-by-category")
async def hype_by_category(db: AsyncSession = Depends(get_db)):
    """카테고리별 평균 hype_score 집계"""
    result = await db.execute(
        select(
            BrandCollaboration.collab_category,
            func.count(BrandCollaboration.id).label("count"),
            func.avg(BrandCollaboration.hype_score).label("avg_hype"),
            func.max(BrandCollaboration.hype_score).label("max_hype"),
        )
        .where(BrandCollaboration.collab_category.isnot(None))
        .group_by(BrandCollaboration.collab_category)
        .order_by(func.avg(BrandCollaboration.hype_score).desc())
    )
    return [
        {
            "category": row.collab_category,
            "count": row.count,
            "avg_hype": round(row.avg_hype or 0, 1),
            "max_hype": row.max_hype or 0,
        }
        for row in result.all()
    ]
