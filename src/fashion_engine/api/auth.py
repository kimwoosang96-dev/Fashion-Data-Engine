from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.config import settings
from fashion_engine.database import get_db
from fashion_engine.services.api_key_service import authenticate_api_key


def verify_admin_header(authorization: str | None) -> None:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    scheme, _, token = authorization.partition(" ")
    expected = settings.admin_bearer_token
    if expected is None:
        if not settings.api_debug:
            raise HTTPException(status_code=503, detail="Admin token not configured")
        return
    if scheme.lower() != "bearer" or token != expected:
        raise HTTPException(status_code=401, detail="Invalid admin token")


async def require_admin(authorization: str | None = Header(None)) -> None:
    verify_admin_header(authorization)


async def resolve_api_key_header(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    authorization: str | None = Header(None),
) -> str:
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if token:
            return token
    raise HTTPException(status_code=401, detail="API key required")


def require_api_key(
    *,
    scope: str,
    export_limited: bool = False,
):
    async def _dependency(
        db: AsyncSession = Depends(get_db),
        raw_key: str = Depends(resolve_api_key_header),
    ):
        return await authenticate_api_key(
            db,
            raw_key=raw_key,
            scope=scope,
            enforce_export_limit=export_limited,
        )

    return _dependency
