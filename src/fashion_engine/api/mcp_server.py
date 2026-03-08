from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.cache import get_redis
from fashion_engine.api.auth import resolve_api_key_header
from fashion_engine.config import settings
from fashion_engine.database import get_db
from fashion_engine.services.api_key_service import authenticate_api_key
from fashion_engine.models.brand import Brand
from fashion_engine.models.channel import Channel
from fashion_engine.services.brand_service import get_brand_sale_intel

router = APIRouter(prefix="/mcp", tags=["mcp"])

_request_counts: dict[str, list[float]] = defaultdict(list)


async def _check_rate_limit(api_key: str, max_rpm: int = 60) -> bool:
    redis = await get_redis()
    if redis is not None:
        key = f"mcp:rate:{api_key}"
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, 60)
        return current <= max_rpm

    now = time.time()
    window = [t for t in _request_counts[api_key] if now - t < 60]
    _request_counts[api_key] = window
    if len(window) >= max_rpm:
        return False
    _request_counts[api_key].append(now)
    return True


async def require_mcp_auth(
    raw_key: str = Depends(resolve_api_key_header),
    db: AsyncSession = Depends(get_db),
) -> str:
    expected = (settings.mcp_api_key or "").strip()
    if expected and raw_key == expected:
        if not await _check_rate_limit(raw_key):
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        return raw_key
    api_key = await authenticate_api_key(db, raw_key=raw_key, scope="mcp")
    return api_key.key_prefix


@router.get("")
async def mcp_index(
    _api_key: str = Depends(require_mcp_auth),
):
    return {
        "server": "fashion-data-engine",
        "transport": "http-json",
        "resources": ["brands://list", "channels://active"],
        "tools": ["get_brand_sale_status"],
    }


@router.get("/resources/brands")
async def list_brands_resource(
    _api_key: str = Depends(require_mcp_auth),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Brand.slug, Brand.name, Brand.tier)
            .order_by(Brand.name.asc())
        )
    ).all()
    return {
        "uri": "brands://list",
        "items": [
            {"slug": slug, "name": name, "tier": tier}
            for slug, name, tier in rows
        ],
    }


@router.get("/resources/channels")
async def list_active_channels_resource(
    _api_key: str = Depends(require_mcp_auth),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Channel.name, Channel.platform, Channel.country)
            .where(Channel.is_active == True)  # noqa: E712
            .order_by(Channel.name.asc())
        )
    ).all()
    return {
        "uri": "channels://active",
        "items": [
            {"name": name, "platform": platform, "country": country}
            for name, platform, country in rows
        ],
    }


@router.post("/tools/get_brand_sale_status")
async def get_brand_sale_status_tool(
    request: Request,
    _api_key: str = Depends(require_mcp_auth),
    db: AsyncSession = Depends(get_db),
):
    payload = await request.json()
    brand_slug = str(payload.get("brand_slug") or "").strip()
    if not brand_slug:
        raise HTTPException(status_code=400, detail="brand_slug required")
    result = await get_brand_sale_intel(db, brand_slug)
    if not result:
        raise HTTPException(status_code=404, detail="brand not found")
    return {"tool": "get_brand_sale_status", "result": result}
