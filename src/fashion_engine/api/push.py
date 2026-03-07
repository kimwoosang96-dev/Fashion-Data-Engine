from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.config import settings
from fashion_engine.database import get_db
from fashion_engine.models.push_subscription import PushSubscription

router = APIRouter(prefix="/push", tags=["push"])


class PushKeysIn(BaseModel):
    p256dh: str
    auth: str


class PushSubscribeIn(BaseModel):
    endpoint: str
    keys: PushKeysIn
    brand_ids: list[int] = []


class PushUnsubscribeIn(BaseModel):
    endpoint: str


@router.get("/public-key")
async def get_push_public_key():
    if not settings.push_vapid_public_key:
        raise HTTPException(status_code=503, detail="push not configured")
    return {"public_key": settings.push_vapid_public_key}


@router.post("/subscribe")
async def subscribe_push(
    payload: PushSubscribeIn,
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(select(PushSubscription).where(PushSubscription.endpoint == payload.endpoint))
    ).scalar_one_or_none()
    if row is None:
        row = PushSubscription(
            endpoint=payload.endpoint,
            p256dh=payload.keys.p256dh,
            auth=payload.keys.auth,
            brand_ids=payload.brand_ids,
        )
        db.add(row)
    else:
        row.p256dh = payload.keys.p256dh
        row.auth = payload.keys.auth
        row.brand_ids = payload.brand_ids
    await db.commit()
    return {"ok": True, "endpoint": row.endpoint, "brand_ids": row.brand_ids or []}


@router.delete("/subscribe")
async def unsubscribe_push(
    payload: PushUnsubscribeIn,
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(select(PushSubscription).where(PushSubscription.endpoint == payload.endpoint))
    ).scalar_one_or_none()
    if row is not None:
        await db.delete(row)
        await db.commit()
    return {"ok": True}
