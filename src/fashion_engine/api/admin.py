from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.config import settings
from fashion_engine.database import get_db
from fashion_engine.models.channel import Channel
from fashion_engine.models.channel_brand import ChannelBrand
from fashion_engine.models.exchange_rate import ExchangeRate
from fashion_engine.models.price_history import PriceHistory
from fashion_engine.models.product import Product

router = APIRouter(prefix="/admin", tags=["admin"])

ROOT_DIR = Path(__file__).resolve().parents[3]
SCRIPT_MAP = {
    "brands": ["scripts/crawl_brands.py"],
    "products": ["scripts/crawl_products.py"],
    "drops": ["scripts/crawl_drops.py"],
}


def _auth_bearer(authorization: str | None) -> None:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != settings.admin_bearer_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


async def require_admin(authorization: str | None = Header(None)) -> None:
    _auth_bearer(authorization)


@router.get("/stats")
async def get_admin_stats(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    counts = (
        await db.execute(
            select(
                func.count(Channel.id).label("channels"),
                select(func.count(ChannelBrand.channel_id)).scalar_subquery().label("channel_brands"),
                select(func.count(Product.id)).scalar_subquery().label("products"),
                select(func.count(PriceHistory.id)).scalar_subquery().label("price_history"),
            )
        )
    ).one()
    latest_crawls = (
        await db.execute(
            select(
                func.max(ChannelBrand.crawled_at).label("brands_latest"),
                func.max(PriceHistory.crawled_at).label("products_latest"),
            )
        )
    ).one()
    rates = (
        await db.execute(
            select(ExchangeRate.from_currency, ExchangeRate.rate, ExchangeRate.fetched_at)
            .where(ExchangeRate.to_currency == "KRW")
            .order_by(ExchangeRate.fetched_at.desc())
            .limit(20)
        )
    ).all()
    return {
        "counts": {
            "channels": int(counts.channels or 0),
            "channel_brands": int(counts.channel_brands or 0),
            "products": int(counts.products or 0),
            "price_history": int(counts.price_history or 0),
        },
        "latest_crawls": {
            "brands": latest_crawls.brands_latest.isoformat() if latest_crawls.brands_latest else None,
            "products": latest_crawls.products_latest.isoformat() if latest_crawls.products_latest else None,
        },
        "exchange_rates": [
            {
                "from_currency": row.from_currency,
                "rate": row.rate,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
            }
            for row in rates
        ],
    }


@router.get("/channels-health")
async def get_channels_health(
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(
                Channel.id,
                Channel.name,
                Channel.url,
                Channel.channel_type,
                Channel.country,
                func.count(func.distinct(ChannelBrand.brand_id)).label("brand_count"),
                func.count(func.distinct(Product.id)).label("product_count"),
                func.count(func.distinct(case((Product.is_sale == True, Product.id), else_=None))).label("sale_count"),
            )
            .outerjoin(ChannelBrand, ChannelBrand.channel_id == Channel.id)
            .outerjoin(Product, Product.channel_id == Channel.id)
            .group_by(Channel.id)
            .order_by(Channel.name.asc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    payload = []
    for row in rows:
        brand_count = int(row.brand_count or 0)
        product_count = int(row.product_count or 0)
        health = "ok" if (brand_count > 0 or product_count > 0) else "needs_review"
        payload.append(
            {
                "channel_id": row.id,
                "name": row.name,
                "url": row.url,
                "channel_type": row.channel_type,
                "country": row.country,
                "brand_count": brand_count,
                "product_count": product_count,
                "sale_count": int(row.sale_count or 0),
                "health": health,
            }
        )
    return payload


@router.post("/crawl-trigger")
async def trigger_crawl(
    job: str = Query(..., description="brands/products/drops"),
    dry_run: bool = Query(False),
    _: None = Depends(require_admin),
):
    if job not in SCRIPT_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown job: {job}")
    cmd = [sys.executable, *SCRIPT_MAP[job]]
    if dry_run:
        return {"ok": True, "job": job, "dry_run": True, "command": " ".join(cmd)}

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(ROOT_DIR),
    )
    return {
        "ok": True,
        "job": job,
        "dry_run": False,
        "pid": proc.pid,
        "command": " ".join(cmd),
    }
