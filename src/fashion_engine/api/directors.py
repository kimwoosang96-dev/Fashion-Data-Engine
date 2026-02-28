from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.api.schemas import BrandDirectorOut
from fashion_engine.database import get_db
from fashion_engine.models.brand import Brand
from fashion_engine.models.brand_director import BrandDirector

router = APIRouter(prefix="/directors", tags=["directors"])


@router.get("/", response_model=list[BrandDirectorOut])
async def list_directors(
    brand_slug: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(BrandDirector, Brand.name, Brand.slug)
        .join(Brand, Brand.id == BrandDirector.brand_id)
        .order_by(BrandDirector.start_year.desc().nullslast(), BrandDirector.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if brand_slug:
        query = query.where(Brand.slug == brand_slug)

    rows = (await db.execute(query)).all()
    return [
        BrandDirectorOut(
            id=row[0].id,
            brand_id=row[0].brand_id,
            brand_name=row[1],
            brand_slug=row[2],
            name=row[0].name,
            role=row[0].role,
            start_year=row[0].start_year,
            end_year=row[0].end_year,
            note=row[0].note,
            created_at=row[0].created_at,
        )
        for row in rows
    ]
