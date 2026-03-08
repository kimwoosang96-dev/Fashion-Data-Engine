from __future__ import annotations

import logging
from typing import Any

import httpx

from fashion_engine.config import settings

logger = logging.getLogger(__name__)


async def broadcast_feed_item(payload: dict[str, Any]) -> bool:
    base_url = (settings.internal_api_base_url or "").strip()
    api_key = (settings.internal_api_key or "").strip()
    if not base_url or not api_key:
        return False

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/internal/broadcast",
                json=payload,
                headers={"X-Internal-Key": api_key},
            )
            return response.status_code == 200
    except Exception as exc:
        logger.warning("realtime broadcast failed: %s", exc)
        return False
