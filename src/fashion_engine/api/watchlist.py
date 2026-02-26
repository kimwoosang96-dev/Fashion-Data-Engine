from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.database import get_db
from fashion_engine.services import watchlist_service

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

VALID_TYPES = {"brand", "channel", "product_key"}


class WatchListItemIn(BaseModel):
    watch_type: str   # "brand" | "channel" | "product_key"
    watch_value: str  # brand_slug / channel_url / product_key
    notes: str | None = None


class WatchListItemOut(BaseModel):
    id: int
    watch_type: str
    watch_value: str
    notes: str | None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[WatchListItemOut])
async def list_watchlist(
    watch_type: str | None = Query(None, description="brand | channel | product_key"),
    db: AsyncSession = Depends(get_db),
):
    """내 관심 목록."""
    return await watchlist_service.list_items(db, watch_type=watch_type)


@router.post("/", response_model=WatchListItemOut, status_code=201)
async def add_watchlist(
    body: WatchListItemIn,
    db: AsyncSession = Depends(get_db),
):
    """
    관심 항목 추가.
    - watch_type: "brand" → watch_value: brand slug (예: "new-balance")
    - watch_type: "channel" → watch_value: channel URL (예: "https://kr.patta.nl")
    - watch_type: "product_key" → watch_value: "brand-slug:handle"
    """
    if body.watch_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"watch_type은 {VALID_TYPES} 중 하나여야 합니다.")
    item, _ = await watchlist_service.add_item(db, body.watch_type, body.watch_value, body.notes)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_watchlist(item_id: int, db: AsyncSession = Depends(get_db)):
    """관심 항목 제거."""
    deleted = await watchlist_service.delete_item(db, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다.")
