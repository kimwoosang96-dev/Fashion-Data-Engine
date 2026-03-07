from fastapi import APIRouter, Depends, HTTPException, Query, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.api.schemas import ActivityFeedItemOut, FeedIngestIn
from fashion_engine.config import settings
from fashion_engine.database import get_db
from fashion_engine.services import feed_service

router = APIRouter(prefix="/feed", tags=["feed"])

_bearer = HTTPBearer(auto_error=False)


async def require_bearer(
    creds: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> None:
    expected = (settings.admin_bearer_token or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="ADMIN_BEARER_TOKEN not configured")
    if creds is None or creds.credentials != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing Bearer token")


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


@router.post("/ingest", response_model=ActivityFeedItemOut, status_code=201)
async def ingest_activity_feed(
    payload: FeedIngestIn,
    _: None = Depends(require_bearer),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await feed_service.ingest_activity_feed(
            db,
            event_type=payload.event_type,
            product_name=payload.product_name,
            source_url=payload.source_url,
            brand_slug=payload.brand_slug,
            price_krw=payload.price_krw,
            discount_rate=payload.discount_rate,
            image_url=payload.image_url,
            notes=payload.notes,
            detected_at=payload.detected_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
