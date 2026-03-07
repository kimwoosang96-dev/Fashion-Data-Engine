from calendar import monthrange
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.api.schemas import DropIn, DropOut, DropsCalendarEntryOut
from fashion_engine.database import get_db
from fashion_engine.models.activity_feed import ActivityFeed
from fashion_engine.models.brand import Brand
from fashion_engine.models.intel import IntelEvent
from fashion_engine.services import drop_service

router = APIRouter(prefix="/drops", tags=["drops"])


@router.get("/upcoming", response_model=list[DropOut])
async def get_upcoming_drops(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """예정 발매(upcoming) 목록."""
    return await drop_service.get_upcoming_drops(db, limit=limit)


@router.get("/", response_model=list[DropOut])
async def list_drops(
    status: str | None = Query(None, description="upcoming | released | sold_out"),
    brand: str | None = Query(None, description="브랜드 slug"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """전체 드롭 목록 (status·brand 필터 지원)."""
    return await drop_service.list_drops(
        db, status=status, brand_slug=brand, limit=limit, offset=offset
    )


@router.get("/calendar", response_model=dict[str, list[DropsCalendarEntryOut]])
async def drops_calendar(
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
):
    start = datetime(year, month, 1)
    end = datetime(year, month, monthrange(year, month)[1], 23, 59, 59)

    intel_rows = (
        await db.execute(
            select(IntelEvent, Brand.name)
            .join(Brand, Brand.id == IntelEvent.brand_id, isouter=True)
            .where(
                IntelEvent.layer == "drops",
                or_(
                    IntelEvent.event_time.between(start, end),
                    IntelEvent.detected_at.between(start, end),
                ),
            )
            .order_by(IntelEvent.event_time.asc().nullslast(), IntelEvent.detected_at.asc())
        )
    ).all()

    feed_rows = (
        await db.execute(
            select(ActivityFeed, Brand.name)
            .join(Brand, Brand.id == ActivityFeed.brand_id, isouter=True)
            .where(
                ActivityFeed.event_type == "new_drop",
                ActivityFeed.detected_at >= start,
                ActivityFeed.detected_at <= end + timedelta(seconds=1),
            )
            .order_by(ActivityFeed.detected_at.asc(), ActivityFeed.id.asc())
        )
    ).all()

    grouped: dict[str, list[dict]] = defaultdict(list)
    for event, brand_name in intel_rows:
        event_dt = event.event_time or event.detected_at
        if not event_dt:
            continue
        grouped[event_dt.date().isoformat()].append(
            {
                "brand_name": brand_name,
                "title": event.title,
                "event_type": event.event_type,
                "source_url": event.source_url,
            }
        )
    for event, brand_name in feed_rows:
        if not event.detected_at:
            continue
        grouped[event.detected_at.date().isoformat()].append(
            {
                "brand_name": brand_name,
                "title": event.product_name or "신제품",
                "event_type": event.event_type,
                "source_url": event.source_url,
            }
        )
    return dict(sorted(grouped.items()))


@router.post("/", response_model=DropOut, status_code=201)
async def create_drop(
    body: DropIn,
    db: AsyncSession = Depends(get_db),
):
    """수동 드롭 추가 (관리용)."""
    return await drop_service.create_drop_manual(db, body.model_dump())
