from __future__ import annotations

import hashlib
import secrets
import time
from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.cache import get_redis
from fashion_engine.models.api_key import ApiKey, ApiKeyDailyUsage

TIER_LIMITS: dict[str, dict] = {
    "free": {"rpm": 10, "daily": 100, "scopes": ["search", "availability", "docs"]},
    "pro": {"rpm": 60, "daily": 10_000, "scopes": ["search", "availability", "seasonality", "mcp", "feed", "docs"]},
    "enterprise": {"rpm": 300, "daily": 100_000, "scopes": ["*", "export"]},
}

_memory_counts: dict[str, list[float]] = defaultdict(list)
_export_counts: dict[str, list[float]] = defaultdict(list)


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _scopes_for(api_key: ApiKey) -> list[str]:
    raw = (api_key.endpoint_scope or "").strip()
    if raw:
        return [part.strip() for part in raw.split(",") if part.strip()]
    return list(TIER_LIMITS.get(api_key.tier, TIER_LIMITS["free"])["scopes"])


def _scope_allowed(api_key: ApiKey, scope: str) -> bool:
    scopes = _scopes_for(api_key)
    return "*" in scopes or scope in scopes


async def _check_rpm_limit(api_key: ApiKey) -> bool:
    redis = await get_redis()
    key = f"apikey:rpm:{api_key.id}"
    if redis is not None:
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, 60)
        return current <= api_key.rpm_limit

    now = time.time()
    window = [t for t in _memory_counts[key] if now - t < 60]
    _memory_counts[key] = window
    if len(window) >= api_key.rpm_limit:
        return False
    _memory_counts[key].append(now)
    return True


async def _check_export_limit(api_key: ApiKey) -> bool:
    redis = await get_redis()
    key = f"apikey:export:{api_key.id}"
    if redis is not None:
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, 3600)
        return current <= 1

    now = time.time()
    window = [t for t in _export_counts[key] if now - t < 3600]
    _export_counts[key] = window
    if len(window) >= 1:
        return False
    _export_counts[key].append(now)
    return True


async def create_api_key(
    db: AsyncSession,
    *,
    name: str,
    tier: str,
) -> tuple[ApiKey, str]:
    if tier not in TIER_LIMITS:
        raise ValueError("invalid tier")
    raw_key = f"fde_{tier}_{secrets.token_urlsafe(24)}"
    key_hash = _hash_key(raw_key)
    prefix = raw_key[:12]
    cfg = TIER_LIMITS[tier]
    row = ApiKey(
        key_prefix=prefix,
        key_hash=key_hash,
        name=name.strip()[:100],
        tier=tier,
        rpm_limit=int(cfg["rpm"]),
        daily_limit=int(cfg["daily"]),
        endpoint_scope=",".join(cfg["scopes"]),
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row, raw_key


async def list_api_keys_with_stats(db: AsyncSession) -> list[dict]:
    since = date.today() - timedelta(days=30)
    rows = (
        await db.execute(
            select(
                ApiKey,
                func.coalesce(func.sum(ApiKeyDailyUsage.request_count), 0).label("monthly_requests"),
            )
            .outerjoin(
                ApiKeyDailyUsage,
                (ApiKeyDailyUsage.api_key_id == ApiKey.id) & (ApiKeyDailyUsage.usage_date >= since),
            )
            .group_by(ApiKey.id)
            .order_by(ApiKey.created_at.desc(), ApiKey.id.desc())
        )
    ).all()
    payload: list[dict] = []
    for api_key, monthly_requests in rows:
        payload.append(
            {
                "id": api_key.id,
                "key_prefix": api_key.key_prefix,
                "name": api_key.name,
                "tier": api_key.tier,
                "rpm_limit": api_key.rpm_limit,
                "daily_limit": api_key.daily_limit,
                "is_active": api_key.is_active,
                "created_at": api_key.created_at,
                "last_used_at": api_key.last_used_at,
                "monthly_requests": int(monthly_requests or 0),
            }
        )
    return payload


async def authenticate_api_key(
    db: AsyncSession,
    *,
    raw_key: str,
    scope: str,
    enforce_export_limit: bool = False,
) -> ApiKey:
    key_hash = _hash_key(raw_key.strip())
    api_key = (
        await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    ).scalar_one_or_none()
    if not api_key or not api_key.is_active:
        raise HTTPException(status_code=401, detail="invalid api key")
    if not _scope_allowed(api_key, scope):
        raise HTTPException(status_code=403, detail="endpoint not allowed for this api key")
    if not await _check_rpm_limit(api_key):
        raise HTTPException(status_code=429, detail="rate limit exceeded", headers={"Retry-After": "60"})
    usage_day = date.today()
    usage = (
        await db.execute(
            select(ApiKeyDailyUsage).where(
                ApiKeyDailyUsage.api_key_id == api_key.id,
                ApiKeyDailyUsage.usage_date == usage_day,
            )
        )
    ).scalar_one_or_none()
    if usage and usage.request_count >= api_key.daily_limit:
        raise HTTPException(status_code=429, detail="daily quota exceeded", headers={"Retry-After": "86400"})
    if enforce_export_limit and not await _check_export_limit(api_key):
        raise HTTPException(status_code=429, detail="export limit exceeded", headers={"Retry-After": "3600"})

    if usage is None:
        usage = ApiKeyDailyUsage(api_key_id=api_key.id, usage_date=usage_day, request_count=0)
        db.add(usage)
    usage.request_count += 1
    api_key.last_used_at = datetime.utcnow()
    await db.commit()
    await db.refresh(api_key)
    return api_key
