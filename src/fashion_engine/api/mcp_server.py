from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.config import settings
from fashion_engine.database import get_db
from fashion_engine.models.brand import Brand
from fashion_engine.models.channel import Channel
from fashion_engine.services.brand_service import get_brand_sale_intel

router = APIRouter(prefix="/mcp", tags=["mcp"])

_request_counts: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(api_key: str, max_rpm: int = 60) -> bool:
    now = time.time()
    window = [t for t in _request_counts[api_key] if now - t < 60]
    _request_counts[api_key] = window
    if len(window) >= max_rpm:
        return False
    _request_counts[api_key].append(now)
    return True


async def require_mcp_auth(
    authorization: str | None = Header(None),
) -> str:
    expected = (settings.mcp_api_key or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="MCP_API_KEY not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    api_key = authorization.split(" ", 1)[1].strip()
    if api_key != expected:
        raise HTTPException(status_code=401, detail="invalid api key")
    if not _check_rate_limit(api_key):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    return api_key


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
