from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.api.schemas import ActivityFeedItemOut
from fashion_engine.database import get_db
from fashion_engine.services import feed_service

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("", response_model=list[ActivityFeedItemOut])
async def list_activity_feed(
    event_type: str | None = Query(None, pattern="^(sale_start|new_drop|price_cut|sold_out|restock)$"),
    brand_id: int | None = Query(None, ge=1),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await feed_service.get_activity_feed(
        db,
        event_type=event_type,
        brand_id=brand_id,
        limit=limit,
        offset=offset,
    )
