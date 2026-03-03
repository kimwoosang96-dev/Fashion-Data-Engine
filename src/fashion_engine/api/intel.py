from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.api.schemas import (
    IntelEventsPage,
    IntelMapPointOut,
    IntelTimelineOut,
    IntelEventOut,
)
from fashion_engine.database import get_db
from fashion_engine.services import intel_service

router = APIRouter(prefix="/intel", tags=["intel"])


def _parse_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    parts = [v.strip() for v in value.split(",") if v.strip()]
    return parts or None


def _parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    if not bbox:
        return None
    try:
        min_lng, min_lat, max_lng, max_lat = [float(v) for v in bbox.split(",")]
    except Exception as exc:  # pragma: no cover - FastAPI validation fallback
        raise HTTPException(status_code=400, detail="invalid bbox format") from exc
    if min_lng > max_lng or min_lat > max_lat:
        raise HTTPException(status_code=400, detail="invalid bbox range")
    return min_lng, min_lat, max_lng, max_lat


@router.get("/events", response_model=IntelEventsPage)
async def list_intel_events(
    layers: str | None = Query(None, description="CSV layers"),
    time_range: str = Query("7d", description="24h|7d|30d|90d|all"),
    brand_slug: str | None = Query(None),
    channel_id: int | None = Query(None, ge=1),
    country: str | None = Query(None, description="ISO2"),
    q: str | None = Query(None),
    min_confidence: str | None = Query(None, description="low|medium|high"),
    min_severity: str | None = Query(None, description="low|medium|high|critical"),
    cursor: str | None = Query(None),
    limit: int = Query(100, ge=1, le=300),
    bbox: str | None = Query(None, description="min_lng,min_lat,max_lng,max_lat"),
    db: AsyncSession = Depends(get_db),
):
    return await intel_service.list_intel_events(
        db,
        layers=_parse_csv(layers),
        time_range=time_range,
        brand_slug=brand_slug,
        channel_id=channel_id,
        country=country,
        q=q,
        min_confidence=min_confidence,
        min_severity=min_severity,
        cursor=cursor,
        limit=limit,
        bbox=_parse_bbox(bbox),
    )


@router.get("/map-points", response_model=list[IntelMapPointOut])
async def get_map_points(
    layers: str | None = Query(None, description="CSV layers"),
    time_range: str = Query("7d", description="24h|7d|30d|90d|all"),
    bbox: str | None = Query(None, description="min_lng,min_lat,max_lng,max_lat"),
    limit: int = Query(1000, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    return await intel_service.get_map_points(
        db,
        layers=_parse_csv(layers),
        time_range=time_range,
        bbox=_parse_bbox(bbox),
        limit=limit,
    )


@router.get("/timeline", response_model=IntelTimelineOut)
async def get_timeline(
    layers: str | None = Query(None, description="CSV layers"),
    time_range: str = Query("30d", description="24h|7d|30d|90d|all"),
    granularity: str = Query("day", description="hour|day|week"),
    db: AsyncSession = Depends(get_db),
):
    return await intel_service.get_timeline(
        db,
        layers=_parse_csv(layers),
        time_range=time_range,
        granularity=granularity,
    )


@router.get("/highlights", response_model=list[IntelEventOut])
async def get_highlights(
    layers: str | None = Query(None, description="CSV layers"),
    time_range: str = Query("7d", description="24h|7d|30d|90d|all"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await intel_service.get_highlights(
        db,
        layers=_parse_csv(layers),
        time_range=time_range,
        limit=limit,
    )


@router.get("/events/{event_id}", response_model=dict)
async def get_event_detail(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    payload = await intel_service.get_event_detail(db, event_id)
    if not payload:
        raise HTTPException(status_code=404, detail="intel event not found")
    return payload
