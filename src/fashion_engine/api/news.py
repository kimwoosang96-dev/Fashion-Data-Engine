from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.api.schemas import FashionNewsOut
from fashion_engine.database import get_db
from fashion_engine.models.brand import Brand
from fashion_engine.models.channel import Channel
from fashion_engine.models.fashion_news import FashionNews

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/", response_model=list[FashionNewsOut])
async def list_news(
    entity_type: str | None = Query(None, description="brand | channel"),
    brand_slug: str | None = Query(None),
    channel_id: int | None = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=300),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(FashionNews)
        .order_by(FashionNews.published_at.desc().nullslast(), FashionNews.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if entity_type:
        query = query.where(FashionNews.entity_type == entity_type)

    if brand_slug:
        brand = (
            await db.execute(select(Brand).where(Brand.slug == brand_slug))
        ).scalar_one_or_none()
        if not brand:
            return []
        query = query.where(
            FashionNews.entity_type == "brand",
            FashionNews.entity_id == brand.id,
        )

    if channel_id:
        query = query.where(
            FashionNews.entity_type == "channel",
            FashionNews.entity_id == channel_id,
        )

    rows = list((await db.execute(query)).scalars().all())
    if not rows:
        return []

    brand_ids = [r.entity_id for r in rows if r.entity_type == "brand"]
    channel_ids = [r.entity_id for r in rows if r.entity_type == "channel"]
    brand_name_map: dict[int, str] = {}
    channel_name_map: dict[int, str] = {}

    if brand_ids:
        b_rows = (
            await db.execute(select(Brand.id, Brand.name).where(Brand.id.in_(brand_ids)))
        ).all()
        brand_name_map = {bid: name for bid, name in b_rows}
    if channel_ids:
        c_rows = (
            await db.execute(select(Channel.id, Channel.name).where(Channel.id.in_(channel_ids)))
        ).all()
        channel_name_map = {cid: name for cid, name in c_rows}

    out: list[FashionNewsOut] = []
    for row in rows:
        entity_name = None
        if row.entity_type == "brand":
            entity_name = brand_name_map.get(row.entity_id)
        elif row.entity_type == "channel":
            entity_name = channel_name_map.get(row.entity_id)
        out.append(
            FashionNewsOut(
                id=row.id,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                entity_name=entity_name,
                title=row.title,
                url=row.url,
                summary=row.summary,
                published_at=row.published_at,
                source=row.source,
                crawled_at=row.crawled_at,
            )
        )
    return out
