from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fashion_engine.config import settings

logger = logging.getLogger(__name__)

_redis = None


async def get_redis():
    global _redis
    if _redis is not None:
        return _redis
    if not settings.redis_url:
        return None
    try:
        import redis.asyncio as aioredis
    except Exception:
        logger.warning("redis package unavailable; caching disabled")
        return None
    _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def cached_json(
    *,
    key: str,
    ttl: int,
    fetch_fn: Callable[[], Awaitable[Any]],
) -> Any:
    client = await get_redis()
    if client is not None:
        cached = await client.get(key)
        if cached:
            return json.loads(cached)

    result = await fetch_fn()

    if client is not None and result is not None:
        await client.setex(key, ttl, json.dumps(result, default=str))
    return result


async def invalidate_prefixes(prefixes: list[str]) -> int:
    client = await get_redis()
    if client is None:
        return 0

    deleted = 0
    for prefix in prefixes:
        async for key in client.scan_iter(match=f"{prefix}*"):
            deleted += int(await client.delete(key))
    return deleted
