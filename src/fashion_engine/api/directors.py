from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.api.schemas import BrandDirectorOut, DirectorsByBrand
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


@router.get("/by-brand", response_model=list[DirectorsByBrand])
async def list_directors_by_brand(
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(BrandDirector, Brand.name, Brand.slug)
            .join(Brand, Brand.id == BrandDirector.brand_id)
            .order_by(
                Brand.name.asc(),
                BrandDirector.end_year.is_(None).desc(),
                BrandDirector.end_year.desc().nullslast(),
                BrandDirector.start_year.desc().nullslast(),
                BrandDirector.id.desc(),
            )
        )
    ).all()

    grouped: dict[str, DirectorsByBrand] = {}
    for director, brand_name, brand_slug in rows:
        bucket = grouped.get(brand_slug)
        if bucket is None:
            bucket = DirectorsByBrand(
                brand_slug=brand_slug,
                brand_name=brand_name,
                current_directors=[],
                past_directors=[],
            )
            grouped[brand_slug] = bucket

        item = BrandDirectorOut(
            id=director.id,
            brand_id=director.brand_id,
            brand_name=brand_name,
            brand_slug=brand_slug,
            name=director.name,
            role=director.role,
            start_year=director.start_year,
            end_year=director.end_year,
            note=director.note,
            created_at=director.created_at,
        )
        if director.end_year is None:
            bucket.current_directors.append(item)
        else:
            bucket.past_directors.append(item)

    return list(grouped.values())
