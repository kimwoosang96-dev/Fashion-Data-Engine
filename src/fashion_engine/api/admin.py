from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi.responses import StreamingResponse

from fashion_engine.config import settings
from fashion_engine.database import get_db
from fashion_engine.models.channel import Channel
from fashion_engine.models.channel_brand import ChannelBrand
from fashion_engine.models.brand import Brand
from fashion_engine.models.brand_collaboration import BrandCollaboration
from fashion_engine.models.brand_director import BrandDirector
from fashion_engine.models.exchange_rate import ExchangeRate
from fashion_engine.models.price_history import PriceHistory
from fashion_engine.models.product import Product
from fashion_engine.models.product_catalog import ProductCatalog
from fashion_engine.models.crawl_run import CrawlRun, CrawlChannelLog
from fashion_engine.models.channel_note import ChannelNote
from fashion_engine.models.activity_feed import ActivityFeed
from fashion_engine.models.intel import IntelEvent, IntelIngestRun
from fashion_engine.models.channel_crawl_stat import ChannelCrawlStat
from fashion_engine.api.schemas import (
    ApiKeyCreateIn,
    ApiKeyCreateOut,
    ApiKeyOut,
    CrawlRunOut,
    CrawlRunDetail,
    CrawlChannelLogOut,
    ChannelNoteOut,
    ChannelNoteCreate,
    ChannelSignalOut,
    AdminDraftChannelOut,
)
from fashion_engine.api.auth import require_admin
from fashion_engine.monitoring import get_response_metrics, get_slow_queries
from fashion_engine.services.analytics_service import get_channel_competitiveness
from fashion_engine.services.api_key_service import create_api_key, list_api_keys_with_stats

router = APIRouter(prefix="/admin", tags=["admin"])

ROOT_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT_DIR / "scripts"))
from channel_probe import probe_channel  # noqa: E402

LLM_COSTS_PER_1K = {
    "groq": 0.0,
    "gemini": 0.000075,
    "openai": 0.00015,
}
SCRIPT_MAP = {
    "brands": ["scripts/crawl_brands.py"],
    "products": ["scripts/crawl_products.py"],
    "drops": ["scripts/crawl_drops.py"],
    "channel": ["scripts/crawl_products.py"],
}

def _compute_traffic_light(crawl_status: str, recent_logs: list, inactive_rate: float) -> str:
    if crawl_status == "never":
        return "red"

    last_3 = recent_logs[:3]
    if len(last_3) >= 3 and all(log.status == "failed" for log in last_3):
        return "red"
    if crawl_status == "stale" and inactive_rate >= 0.8:
        return "red"

    if crawl_status == "stale":
        return "yellow"
    if any(log.status == "failed" for log in recent_logs):
        return "yellow"
    if inactive_rate >= 0.5:
        return "yellow"

    return "green"


def _health_status_from_yields(recent_yields: list[int]) -> str:
    last_three = recent_yields[:3]
    positives = sum(1 for value in last_three if value > 0)
    if positives >= 2:
        return "healthy"
    if positives == 1:
        return "degraded"
    return "dead"


def _utc_iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


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


@router.post("/api-keys", response_model=ApiKeyCreateOut, status_code=201)
async def create_admin_api_key(
    payload: ApiKeyCreateIn,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row, raw_key = await create_api_key(
        db,
        name=payload.name,
        tier=payload.tier,
    )
    return {
        "id": row.id,
        "key": raw_key,
        "key_prefix": row.key_prefix,
        "name": row.name,
        "tier": row.tier,
        "rpm_limit": row.rpm_limit,
        "daily_limit": row.daily_limit,
    }


@router.get("/api-keys", response_model=list[ApiKeyOut])
async def list_admin_api_keys(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await list_api_keys_with_stats(db)


@router.get("/intel-status")
async def get_admin_intel_status(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    latest_run = (
        await db.execute(
            select(IntelIngestRun).order_by(IntelIngestRun.started_at.desc()).limit(1)
        )
    ).scalar_one_or_none()
    total_events = (
        await db.execute(select(func.count(IntelEvent.id)))
    ).scalar_one()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now_utc - timedelta(hours=24)
    events_last_24h = (
        await db.execute(
            select(func.count(IntelEvent.id)).where(IntelEvent.detected_at >= cutoff)
        )
    ).scalar_one()
    latest_event_at = (
        await db.execute(select(func.max(IntelEvent.detected_at)))
    ).scalar_one_or_none()
    freshness_minutes = None
    if latest_event_at:
        freshness_minutes = int((now_utc - latest_event_at).total_seconds() // 60)
    layer_rows = (
        await db.execute(
            select(IntelEvent.layer, func.count(IntelEvent.id))
            .group_by(IntelEvent.layer)
            .order_by(func.count(IntelEvent.id).desc())
        )
    ).all()
    derived_rows = (
        await db.execute(
            select(IntelEvent.event_type, func.count(IntelEvent.id))
            .where(
                IntelEvent.event_type.in_(
                    ["sale_start", "sold_out", "restock", "sales_spike"]
                ),
                IntelEvent.detected_at >= cutoff,
            )
            .group_by(IntelEvent.event_type)
        )
    ).all()
    derived = {k: int(v) for k, v in derived_rows}
    for key in ["sale_start", "sold_out", "restock", "sales_spike"]:
        derived.setdefault(key, 0)

    activity_feed_24h = (
        await db.execute(
            select(func.count(ActivityFeed.id)).where(ActivityFeed.detected_at >= cutoff)
        )
    ).scalar_one()
    activity_feed_type_rows = (
        await db.execute(
            select(ActivityFeed.event_type, func.count(ActivityFeed.id))
            .where(ActivityFeed.detected_at >= cutoff)
            .group_by(ActivityFeed.event_type)
            .order_by(func.count(ActivityFeed.id).desc())
        )
    ).all()
    gpt_enabled_channels = (
        await db.execute(
            select(func.count(Channel.id)).where(Channel.use_gpt_parser == True)  # noqa: E712
        )
    ).scalar_one()
    gpt_calls_last_24h = (
        await db.execute(
            select(func.count(CrawlChannelLog.id))
            .where(
                CrawlChannelLog.strategy == "gpt-parser",
                CrawlChannelLog.crawled_at >= cutoff,
            )
        )
    ).scalar_one()
    top_active_brand_rows = (
        await db.execute(
            select(Brand.name, func.count(ActivityFeed.id).label("event_count"))
            .join(Brand, Brand.id == ActivityFeed.brand_id)
            .where(ActivityFeed.detected_at >= now_utc - timedelta(hours=72))
            .group_by(Brand.id, Brand.name)
            .order_by(func.count(ActivityFeed.id).desc(), Brand.name.asc())
            .limit(5)
        )
    ).all()
    activity_feed_by_type = {event_type: int(count) for event_type, count in activity_feed_type_rows}

    return {
        "latest_run": {
            "id": latest_run.id if latest_run else None,
            "job_name": latest_run.job_name if latest_run else None,
            "status": latest_run.status if latest_run else None,
            "started_at": latest_run.started_at.isoformat() if latest_run and latest_run.started_at else None,
            "finished_at": latest_run.finished_at.isoformat() if latest_run and latest_run.finished_at else None,
            "inserted_count": int(latest_run.inserted_count or 0) if latest_run else 0,
            "updated_count": int(latest_run.updated_count or 0) if latest_run else 0,
            "error_count": int(latest_run.error_count or 0) if latest_run else 0,
        },
        "events_total": int(total_events or 0),
        "events_last_24h": int(events_last_24h or 0),
        "latest_event_at": latest_event_at.isoformat() if latest_event_at else None,
        "freshness_minutes": freshness_minutes,
        "layers": [{"layer": layer, "count": int(count)} for layer, count in layer_rows],
        "derived_24h": derived,
        "activity_feed_24h": int(activity_feed_24h or 0),
        "activity_feed_by_type": activity_feed_by_type,
        "gpt_parser_usage": {
            "enabled_channels": int(gpt_enabled_channels or 0),
            "last_24h_calls": int(gpt_calls_last_24h or 0),
        },
        "oauth_active": settings.admin_bearer_token is not None,
        "top_active_brands": [
            {"brand_name": brand_name, "event_count": int(event_count or 0)}
            for brand_name, event_count in top_active_brand_rows
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
    job: str = Query(..., description="brands/products/drops/channel"),
    channel_id: int | None = Query(None, ge=1, description="job=channel일 때 대상 채널 ID"),
    dry_run: bool = Query(False),
    _: None = Depends(require_admin),
):
    if job not in SCRIPT_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown job: {job}")
    cmd = [sys.executable, *SCRIPT_MAP[job]]
    if job == "channel":
        if not channel_id:
            raise HTTPException(status_code=400, detail="job=channel에는 channel_id가 필요합니다.")
        cmd += ["--channel-id", str(channel_id)]
    if dry_run:
        return {
            "ok": True,
            "job": job,
            "channel_id": channel_id,
            "dry_run": True,
            "command": " ".join(cmd),
        }

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(ROOT_DIR),
    )
    return {
        "ok": True,
        "job": job,
        "channel_id": channel_id,
        "dry_run": False,
        "pid": proc.pid,
        "command": " ".join(cmd),
    }


@router.get("/crawl-status")
async def get_crawl_status(
    limit: int = Query(500, ge=1, le=2000),
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
                func.count(Product.id).label("product_count"),
                func.count(case((Product.is_active == True, 1), else_=None)).label("active_count"),
                func.count(case((Product.is_active == False, 1), else_=None)).label("inactive_count"),
                func.max(Product.created_at).label("last_crawled_at"),
            )
            .outerjoin(Product, Product.channel_id == Channel.id)
            .group_by(Channel.id)
            .order_by(Channel.name.asc())
            .limit(limit)
            .offset(offset)
        )
    ).all()

    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    payload = []
    for row in rows:
        last = row.last_crawled_at
        if last is None:
            status = "never"
        else:
            dt = last
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            status = "stale" if dt < stale_cutoff else "ok"

        payload.append(
            {
                "channel_id": row.id,
                "channel_name": row.name,
                "channel_url": row.url,
                "channel_type": row.channel_type,
                "product_count": int(row.product_count or 0),
                "active_count": int(row.active_count or 0),
                "inactive_count": int(row.inactive_count or 0),
                "last_crawled_at": last.isoformat() if last else None,
                "status": status,
            }
        )

    return payload


@router.get("/channel-signals", response_model=list[ChannelSignalOut])
async def get_channel_signals(
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(
                Channel.id,
                Channel.name,
                Channel.channel_type,
                Channel.country,
                Channel.poll_priority,
                func.count(Product.id).label("product_count"),
                func.count(case((Product.is_active == True, 1), else_=None)).label("active_count"),
                func.count(case((Product.is_active == False, 1), else_=None)).label("inactive_count"),
                func.max(Product.created_at).label("last_crawled_at"),
            )
            .outerjoin(Product, Product.channel_id == Channel.id)
            .group_by(Channel.id)
            .order_by(Channel.name.asc())
            .limit(limit)
            .offset(offset)
        )
    ).all()

    recent_logs_rows = (
        await db.execute(
            text(
                """
                SELECT channel_id, status, error_msg, error_type, crawled_at
                FROM (
                    SELECT channel_id, status, error_msg, error_type, crawled_at,
                           ROW_NUMBER() OVER (PARTITION BY channel_id ORDER BY crawled_at DESC) AS rn
                    FROM crawl_channel_logs
                ) sub
                WHERE rn <= 5
                ORDER BY channel_id ASC, crawled_at DESC
                """
            )
        )
    ).all()

    logs_by_channel: dict[int, list] = defaultdict(list)
    for log in recent_logs_rows:
        logs_by_channel[int(log.channel_id)].append(log)

    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    payload: list[dict] = []
    for row in rows:
        product_count = int(row.product_count or 0)
        active_count = int(row.active_count or 0)
        inactive_count = int(row.inactive_count or 0)

        last = row.last_crawled_at
        if last is None:
            crawl_status = "never"
        else:
            dt = last if last.tzinfo else last.replace(tzinfo=timezone.utc)
            crawl_status = "stale" if dt < stale_cutoff else "ok"

        channel_logs = logs_by_channel.get(int(row.id), [])
        inactive_rate = (inactive_count / product_count) if product_count > 0 else 0.0
        success_count = sum(1 for log in channel_logs if log.status == "success")
        recent_success_rate = (success_count / len(channel_logs)) if channel_logs else 0.0
        last_error = next((log.error_msg for log in channel_logs if log.status == "failed"), None)
        last_error_type = next((log.error_type for log in channel_logs if log.status == "failed"), None)
        traffic_light = _compute_traffic_light(crawl_status, channel_logs, inactive_rate)

        payload.append(
            {
                "channel_id": row.id,
                "name": row.name,
                "channel_type": row.channel_type,
                "country": row.country,
                "poll_priority": int(row.poll_priority or 2),
                "product_count": product_count,
                "active_count": active_count,
                "inactive_count": inactive_count,
                "last_crawled_at": last.isoformat() if last else None,
                "crawl_status": crawl_status,
                "recent_success_rate": round(recent_success_rate, 2),
                "last_error_msg": (last_error or "")[:200] if last_error else None,
                "error_type": last_error_type,
                "traffic_light": traffic_light,
            }
        )
    return payload


@router.get("/channel-health")
async def get_channel_health(
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    channels = (
        await db.execute(
            select(
                Channel.id,
                Channel.name,
                Channel.url,
                Channel.platform,
                Channel.is_active,
                Channel.last_probe_at,
            )
            .order_by(Channel.name.asc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    stat_rows = (
        await db.execute(
            text(
                """
                SELECT channel_id, products_found, parse_method, error_msg, crawled_at
                FROM (
                    SELECT channel_id, products_found, parse_method, error_msg, crawled_at,
                           ROW_NUMBER() OVER (PARTITION BY channel_id ORDER BY crawled_at DESC) AS rn
                    FROM channel_crawl_stats
                ) sub
                WHERE rn <= 5
                ORDER BY channel_id ASC, crawled_at DESC
                """
            )
        )
    ).all()

    stats_by_channel: dict[int, list] = defaultdict(list)
    for row in stat_rows:
        stats_by_channel[int(row.channel_id)].append(row)

    payload = []
    for row in channels:
        recent = stats_by_channel.get(int(row.id), [])
        recent_yields = [int(item.products_found or 0) for item in recent]
        last_success_at = next(
            (
                item.crawled_at
                for item in recent
                if int(item.products_found or 0) > 0 and not item.error_msg
            ),
            None,
        )
        parse_method = next((item.parse_method for item in recent if item.parse_method), None)
        payload.append(
            {
                "channel_id": int(row.id),
                "channel_name": row.name,
                "channel_url": row.url,
                "platform": row.platform,
                "is_active": bool(row.is_active),
                "recent_yields": recent_yields,
                "avg_yield": round(sum(recent_yields) / len(recent_yields), 2) if recent_yields else 0.0,
                "last_success_at": _utc_iso(last_success_at),
                "last_probe_at": _utc_iso(row.last_probe_at),
                "parse_method": parse_method,
                "status": _health_status_from_yields(recent_yields),
            }
        )
    return payload


@router.get("/llm-costs")
async def get_admin_llm_costs(
    days: int = Query(30, ge=1, le=180),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(days=days)
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    daily_rows = (
        await db.execute(
            select(
                func.date(ChannelCrawlStat.crawled_at).label("day"),
                ChannelCrawlStat.llm_provider,
                func.coalesce(func.sum(ChannelCrawlStat.llm_prompt_tokens), 0).label("prompt_tokens"),
                func.coalesce(func.sum(ChannelCrawlStat.llm_completion_tokens), 0).label("completion_tokens"),
                func.coalesce(func.sum(ChannelCrawlStat.llm_cost_usd), 0).label("cost_usd"),
            )
            .where(
                ChannelCrawlStat.crawled_at >= cutoff,
                ChannelCrawlStat.llm_provider.is_not(None),
            )
            .group_by(func.date(ChannelCrawlStat.crawled_at), ChannelCrawlStat.llm_provider)
            .order_by(func.date(ChannelCrawlStat.crawled_at).desc(), ChannelCrawlStat.llm_provider.asc())
        )
    ).all()
    channel_rows = (
        await db.execute(
            select(
                Channel.id,
                Channel.name,
                ChannelCrawlStat.llm_provider,
                func.coalesce(func.sum(ChannelCrawlStat.llm_prompt_tokens), 0).label("prompt_tokens"),
                func.coalesce(func.sum(ChannelCrawlStat.llm_completion_tokens), 0).label("completion_tokens"),
                func.coalesce(func.sum(ChannelCrawlStat.llm_cost_usd), 0).label("cost_usd"),
                func.max(ChannelCrawlStat.crawled_at).label("last_used_at"),
            )
            .join(Channel, Channel.id == ChannelCrawlStat.channel_id)
            .where(
                ChannelCrawlStat.crawled_at >= cutoff,
                ChannelCrawlStat.llm_provider.is_not(None),
            )
            .group_by(Channel.id, Channel.name, ChannelCrawlStat.llm_provider)
            .order_by(func.coalesce(func.sum(ChannelCrawlStat.llm_cost_usd), 0).desc(), Channel.name.asc())
            .limit(50)
        )
    ).all()
    monthly_total_usd = (
        await db.execute(
            select(func.coalesce(func.sum(ChannelCrawlStat.llm_cost_usd), 0))
            .where(
                ChannelCrawlStat.crawled_at >= month_start,
                ChannelCrawlStat.llm_provider.is_not(None),
            )
        )
    ).scalar_one()

    return {
        "window_days": days,
        "monthly_total_usd": round(float(monthly_total_usd or 0), 6),
        "providers": LLM_COSTS_PER_1K,
        "daily": [
            {
                "day": str(row.day),
                "provider": row.llm_provider,
                "prompt_tokens": int(row.prompt_tokens or 0),
                "completion_tokens": int(row.completion_tokens or 0),
                "cost_usd": round(float(row.cost_usd or 0), 6),
            }
            for row in daily_rows
        ],
        "by_channel": [
            {
                "channel_id": int(row.id),
                "channel_name": row.name,
                "provider": row.llm_provider,
                "prompt_tokens": int(row.prompt_tokens or 0),
                "completion_tokens": int(row.completion_tokens or 0),
                "cost_usd": round(float(row.cost_usd or 0), 6),
                "last_used_at": _utc_iso(row.last_used_at),
            }
            for row in channel_rows
        ],
    }


@router.get("/performance")
async def get_admin_performance(
    _: None = Depends(require_admin),
):
    endpoints = get_response_metrics()
    return {
        "captured_at": datetime.utcnow().isoformat(),
        "endpoints": endpoints,
        "slow_queries": get_slow_queries(limit=25),
        "alerts": [row for row in endpoints if row["p95_ms"] > 1000],
    }


@router.get("/channel-compete")
async def get_admin_channel_compete(
    min_matches: int = Query(5, ge=1, le=100),
    limit: int = Query(100, ge=1, le=500),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_channel_competitiveness(db, min_matches=min_matches, limit=limit)


@router.get("/collabs")
async def admin_list_collabs(
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(
                BrandCollaboration.id,
                BrandCollaboration.brand_a_id,
                BrandCollaboration.brand_b_id,
                BrandCollaboration.collab_name,
                BrandCollaboration.collab_category,
                BrandCollaboration.release_year,
                BrandCollaboration.hype_score,
                BrandCollaboration.source_url,
                BrandCollaboration.notes,
                BrandCollaboration.created_at,
                Brand.name.label("brand_a_name"),
                Brand.slug.label("brand_a_slug"),
            )
            .join(Brand, Brand.id == BrandCollaboration.brand_a_id)
            .order_by(BrandCollaboration.hype_score.desc(), BrandCollaboration.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return [
        {
            "id": row.id,
            "brand_a_id": row.brand_a_id,
            "brand_b_id": row.brand_b_id,
            "collab_name": row.collab_name,
            "collab_category": row.collab_category,
            "release_year": row.release_year,
            "hype_score": row.hype_score,
            "source_url": row.source_url,
            "notes": row.notes,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "brand_a_name": row.brand_a_name,
            "brand_a_slug": row.brand_a_slug,
        }
        for row in rows
    ]


@router.post("/collabs")
async def admin_create_collab(
    payload: dict,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    brand_a_id = payload.get("brand_a_id")
    brand_b_id = payload.get("brand_b_id")
    if not brand_a_id and payload.get("brand_a_slug"):
        row = (
            await db.execute(select(Brand.id).where(Brand.slug == payload["brand_a_slug"]))
        ).first()
        brand_a_id = row[0] if row else None
    if not brand_b_id and payload.get("brand_b_slug"):
        row = (
            await db.execute(select(Brand.id).where(Brand.slug == payload["brand_b_slug"]))
        ).first()
        brand_b_id = row[0] if row else None

    if not brand_a_id or not brand_b_id:
        raise HTTPException(status_code=400, detail="brand_a_id/brand_b_id 또는 유효한 brand_slug가 필요합니다.")
    if int(brand_a_id) == int(brand_b_id):
        raise HTTPException(status_code=400, detail="같은 브랜드끼리는 협업으로 등록할 수 없습니다.")
    collab_name = str(payload.get("collab_name") or "").strip()
    if not collab_name:
        raise HTTPException(status_code=400, detail="collab_name은 필수입니다.")

    hype_score = payload.get("hype_score")
    if hype_score in (None, ""):
        overlap_channels = (
            await db.execute(
                select(func.count())
                .select_from(
                    select(ChannelBrand.channel_id)
                    .where(ChannelBrand.brand_id.in_([int(brand_a_id), int(brand_b_id)]))
                    .group_by(ChannelBrand.channel_id)
                    .having(func.count(func.distinct(ChannelBrand.brand_id)) == 2)
                    .subquery()
                )
            )
        ).scalar_one()
        hype_score = min(100, int(overlap_channels or 0) * 10)

    row = BrandCollaboration(
        brand_a_id=int(brand_a_id),
        brand_b_id=int(brand_b_id),
        collab_name=collab_name[:255],
        collab_category=(str(payload["collab_category"]).strip()[:50] if payload.get("collab_category") else None),
        release_year=(int(payload["release_year"]) if payload.get("release_year") not in (None, "") else None),
        hype_score=max(0, min(100, int(hype_score))),
        source_url=(str(payload["source_url"]).strip()[:500] if payload.get("source_url") else None),
        notes=(str(payload["notes"]).strip() if payload.get("notes") else None),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"ok": True, "id": row.id}


@router.delete("/collabs/{collab_id}")
async def admin_delete_collab(
    collab_id: int,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(select(BrandCollaboration).where(BrandCollaboration.id == collab_id))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="collab not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}


@router.get("/brand-channel-audit")
async def admin_brand_channel_audit(
    limit: int = Query(200, ge=1, le=1000),
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
                func.count(func.distinct(ChannelBrand.brand_id)).label("brand_count"),
            )
            .outerjoin(ChannelBrand, ChannelBrand.channel_id == Channel.id)
            .group_by(Channel.id)
            .order_by(Channel.name.asc())
        )
    ).all()

    brand_names_by_channel: dict[int, list[str]] = {}
    linked = (
        await db.execute(
            select(ChannelBrand.channel_id, Brand.name)
            .join(Brand, Brand.id == ChannelBrand.brand_id)
            .order_by(ChannelBrand.channel_id.asc(), Brand.name.asc())
        )
    ).all()
    for channel_id, brand_name in linked:
        brand_names_by_channel.setdefault(channel_id, []).append(brand_name)

    suspicious: list[dict] = []
    seen: set[tuple[str, int]] = set()
    official_types = {"official", "brand-store"}
    multi_types = {"multi-brand", "edit-shop"}

    for row in rows:
        brand_count = int(row.brand_count or 0)
        channel_type = (row.channel_type or "").strip().lower()
        linked_brands = brand_names_by_channel.get(row.id, [])

        if channel_type in official_types and brand_count != 1:
            key = ("official_count_mismatch", row.id)
            if key not in seen:
                seen.add(key)
                suspicious.append(
                    {
                        "audit_type": "official_count_mismatch",
                        "channel_id": row.id,
                        "channel_name": row.name,
                        "channel_type": row.channel_type,
                        "channel_url": row.url,
                        "brand_count": brand_count,
                        "linked_brands": linked_brands[:8],
                        "reason": "공식몰/브랜드스토어인데 연결 브랜드 수가 1이 아님",
                        "suggestion": "해당 채널의 브랜드 매핑을 재검토하세요.",
                    }
                )

        if channel_type in multi_types and brand_count == 1:
            key = ("multi_brand_too_low", row.id)
            if key not in seen:
                seen.add(key)
                suspicious.append(
                    {
                        "audit_type": "multi_brand_too_low",
                        "channel_id": row.id,
                        "channel_name": row.name,
                        "channel_type": row.channel_type,
                        "channel_url": row.url,
                        "brand_count": brand_count,
                        "linked_brands": linked_brands[:8],
                        "reason": "멀티브랜드 채널인데 연결 브랜드가 1개뿐임",
                        "suggestion": "크롤러 셀렉터/전략을 재점검하거나 채널 유형을 확인하세요.",
                    }
                )

    name_collision_rows = (
        await db.execute(
            select(Channel.id, Channel.name, Channel.url, Channel.channel_type, Brand.id, Brand.slug)
            .join(Brand, func.lower(Channel.name) == func.lower(Brand.name))
            .where(Channel.channel_type.isnot(None))
            .where(func.lower(Channel.channel_type).notin_(tuple(official_types)))
            .limit(limit)
        )
    ).all()
    for row in name_collision_rows:
        key = ("name_collision", row[0])
        if key in seen:
            continue
        seen.add(key)
        suspicious.append(
            {
                "audit_type": "name_collision",
                "channel_id": row[0],
                "channel_name": row[1],
                "channel_type": row[3],
                "channel_url": row[2],
                "brand_count": len(brand_names_by_channel.get(row[0], [])),
                "linked_brands": brand_names_by_channel.get(row[0], [])[:8],
                "reason": f"채널명과 브랜드명이 동일(brand_slug={row[5]})",
                "suggestion": "브랜드/채널 엔티티 분리와 channel_type 적절성을 검토하세요.",
            }
        )

    # ── edit_shop_as_brand: 편집샵과 동명 브랜드 감지 ────────────────────────
    edit_shop_channels = {
        row.name.lower(): row for row in rows if (row.channel_type or "").lower() in {"edit-shop", "multi-brand"}
    }
    brand_name_rows = (
        await db.execute(select(Brand.id, Brand.name, Brand.slug))
    ).all()
    for b_id, b_name, b_slug in brand_name_rows:
        if not b_name:
            continue
        ch = edit_shop_channels.get(b_name.lower())
        if ch:
            key = ("edit_shop_as_brand", b_id)
            if key not in seen:
                seen.add(key)
                suspicious.append(
                    {
                        "audit_type": "edit_shop_as_brand",
                        "channel_id": ch.id,
                        "channel_name": ch.name,
                        "channel_type": ch.channel_type,
                        "channel_url": ch.url,
                        "brand_count": 0,
                        "linked_brands": [b_slug],
                        "reason": f"편집샵과 동일한 이름의 브랜드 존재(brand_id={b_id}, slug={b_slug})",
                        "suggestion": f"brands 테이블에서 해당 브랜드(id={b_id})를 삭제하거나 편집샵 채널로 재분류하세요.",
                    }
                )

    # ── high_archive_rate: 품절률 70% 초과 채널 감지 ─────────────────────────
    archive_rows = (
        await db.execute(
            select(
                Product.channel_id,
                func.count(Product.id).label("total"),
                func.sum(case((Product.is_active == False, 1), else_=0)).label("inactive"),  # noqa: E712
            )
            .group_by(Product.channel_id)
            .having(func.count(Product.id) >= 10)  # 10개 미만 채널은 제외
        )
    ).all()
    channel_map = {row.id: row for row in rows}
    for arc_row in archive_rows:
        total = int(arc_row.total or 0)
        inactive = int(arc_row.inactive or 0)
        if total > 0 and inactive / total >= 0.7:
            ch = channel_map.get(arc_row.channel_id)
            if ch:
                key = ("high_archive_rate", arc_row.channel_id)
                if key not in seen:
                    seen.add(key)
                    suspicious.append(
                        {
                            "audit_type": "high_archive_rate",
                            "channel_id": arc_row.channel_id,
                            "channel_name": ch.name,
                            "channel_type": ch.channel_type,
                            "channel_url": ch.url,
                            "brand_count": len(brand_names_by_channel.get(arc_row.channel_id, [])),
                            "linked_brands": brand_names_by_channel.get(arc_row.channel_id, [])[:8],
                            "reason": f"품절 비율 {round(inactive/total*100)}% ({inactive}/{total}개) — 채널 폐점 의심",
                            "suggestion": "채널 실제 운영 여부를 확인하고 필요시 is_active=False 처리하세요.",
                        }
                    )

    suspicious.sort(key=lambda x: (x["audit_type"], x["channel_name"]))
    return {"total": len(suspicious), "items": suspicious[:limit]}


@router.get("/directors")
async def admin_list_directors(
    brand_id: int | None = Query(None, ge=1),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(BrandDirector, Brand.name, Brand.slug)
        .join(Brand, Brand.id == BrandDirector.brand_id)
        .order_by(BrandDirector.start_year.desc().nullslast(), BrandDirector.id.desc())
    )
    if brand_id:
        query = query.where(BrandDirector.brand_id == brand_id)
    rows = (await db.execute(query)).all()
    return [
        {
            "id": row[0].id,
            "brand_id": row[0].brand_id,
            "brand_name": row[1],
            "brand_slug": row[2],
            "name": row[0].name,
            "role": row[0].role,
            "start_year": row[0].start_year,
            "end_year": row[0].end_year,
            "note": row[0].note,
            "created_at": row[0].created_at.isoformat(),
        }
        for row in rows
    ]


@router.post("/directors")
async def admin_create_director(
    payload: dict,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    brand_id = payload.get("brand_id")
    if brand_id is None and payload.get("brand_slug"):
        brand = (
            await db.execute(select(Brand).where(Brand.slug == payload["brand_slug"]))
        ).scalar_one_or_none()
        brand_id = brand.id if brand else None
    if not brand_id:
        raise HTTPException(status_code=400, detail="brand_id 또는 유효한 brand_slug가 필요합니다.")
    if not payload.get("name"):
        raise HTTPException(status_code=400, detail="name은 필수입니다.")

    row = BrandDirector(
        brand_id=int(brand_id),
        name=str(payload["name"]).strip()[:255],
        role=str(payload.get("role") or "Creative Director").strip()[:100],
        start_year=int(payload["start_year"]) if payload.get("start_year") not in (None, "") else None,
        end_year=int(payload["end_year"]) if payload.get("end_year") not in (None, "") else None,
        note=(str(payload["note"]).strip() if payload.get("note") else None),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"ok": True, "id": row.id}


@router.delete("/directors/{director_id}")
async def admin_delete_director(
    director_id: int,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(select(BrandDirector).where(BrandDirector.id == director_id))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="director not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}


@router.patch("/brands/{brand_id}/instagram")
async def admin_patch_brand_instagram(
    brand_id: int,
    payload: dict,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    brand = (
        await db.execute(select(Brand).where(Brand.id == brand_id))
    ).scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="brand not found")
    brand.instagram_url = (payload.get("instagram_url") or None)
    await db.commit()
    return {"ok": True, "id": brand.id, "instagram_url": brand.instagram_url}


@router.patch("/channels/{channel_id}/instagram")
async def admin_patch_channel_instagram(
    channel_id: int,
    payload: dict,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    channel = (
        await db.execute(select(Channel).where(Channel.id == channel_id))
    ).scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="channel not found")
    channel.instagram_url = (payload.get("instagram_url") or None)
    await db.commit()
    return {"ok": True, "id": channel.id, "instagram_url": channel.instagram_url}


@router.get("/channels", response_model=list[AdminDraftChannelOut])
async def list_admin_channels(
    status: str = Query("all", pattern="^(all|draft)$"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(
            Channel.id,
            Channel.name,
            Channel.url,
            Channel.channel_type,
            Channel.platform,
            Channel.country,
            Channel.description,
            Channel.poll_priority,
            Channel.use_gpt_parser,
            Channel.created_at,
            func.count(Product.id).label("product_count"),
        )
        .outerjoin(Product, Product.channel_id == Channel.id)
        .group_by(Channel.id)
        .order_by(Channel.created_at.desc(), Channel.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if status == "draft":
        stmt = stmt.where(Channel.is_active == False)  # noqa: E712
    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": int(row.id),
            "name": row.name,
            "url": row.url,
            "channel_type": row.channel_type,
            "platform": row.platform,
            "country": row.country,
            "description": row.description,
            "poll_priority": int(row.poll_priority or 2),
            "use_gpt_parser": bool(row.use_gpt_parser),
            "created_at": row.created_at,
            "product_count": int(row.product_count or 0),
        }
        for row in rows
    ]


@router.patch("/channels/{channel_id}/activate")
async def activate_admin_channel(
    channel_id: int,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    channel = (
        await db.execute(select(Channel).where(Channel.id == channel_id))
    ).scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="channel not found")
    channel.is_active = True
    await db.commit()
    return {"ok": True, "id": channel.id, "is_active": channel.is_active}


@router.post("/channels/{channel_id}/reactivate")
async def reactivate_admin_channel(
    channel_id: int,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    channel = (
        await db.execute(select(Channel).where(Channel.id == channel_id))
    ).scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="channel not found")

    probe = await probe_channel(channel.url, channel.name)
    channel.last_probe_at = datetime.utcnow()
    reactivated = bool(probe.http_status and probe.http_status < 400 and probe.platform_detected)
    if reactivated:
        channel.is_active = True
        if probe.platform_detected:
            channel.platform = probe.platform_detected
    await db.commit()
    return {
        "ok": True,
        "id": channel.id,
        "reactivated": reactivated,
        "http_status": probe.http_status,
        "platform_detected": probe.platform_detected,
        "note": probe.note,
        "is_active": channel.is_active,
    }


@router.patch("/channels/{channel_id}/poll-priority")
async def patch_admin_channel_poll_priority(
    channel_id: int,
    payload: dict,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    value = payload.get("poll_priority")
    if value not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="poll_priority must be 1, 2, or 3")
    channel = (
        await db.execute(select(Channel).where(Channel.id == channel_id))
    ).scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="channel not found")
    channel.poll_priority = int(value)
    await db.commit()
    return {"ok": True, "id": channel.id, "poll_priority": channel.poll_priority}


@router.patch("/channels/{channel_id}/webhook-secret")
async def patch_admin_channel_webhook_secret(
    channel_id: int,
    payload: dict,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    channel = (
        await db.execute(select(Channel).where(Channel.id == channel_id))
    ).scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="channel not found")
    secret = (payload.get("webhook_secret") or "").strip()
    channel.webhook_secret = secret or None
    await db.commit()
    return {"ok": True, "id": channel.id, "has_webhook_secret": bool(channel.webhook_secret)}


@router.patch("/channels/{channel_id}/use-gpt-parser")
async def patch_admin_channel_use_gpt_parser(
    channel_id: int,
    payload: dict,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    channel = (
        await db.execute(select(Channel).where(Channel.id == channel_id))
    ).scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="channel not found")
    channel.use_gpt_parser = bool(payload.get("use_gpt_parser"))
    await db.commit()
    return {"ok": True, "id": channel.id, "use_gpt_parser": channel.use_gpt_parser}


# ── 크롤 모니터 ───────────────────────────────────────────────────────────────


@router.get("/crawl-runs", response_model=list[CrawlRunOut])
async def get_crawl_runs(
    limit: int = Query(20, le=100),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """최근 크롤 실행 목록."""
    gpt_counts = (
        select(
            CrawlChannelLog.run_id.label("run_id"),
            func.count(CrawlChannelLog.id).label("gpt_fallback_count"),
        )
        .where(CrawlChannelLog.strategy == "gpt-parser")
        .group_by(CrawlChannelLog.run_id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(
                CrawlRun,
                func.coalesce(gpt_counts.c.gpt_fallback_count, 0).label("gpt_fallback_count"),
            )
            .outerjoin(gpt_counts, gpt_counts.c.run_id == CrawlRun.id)
            .order_by(desc(CrawlRun.started_at))
            .limit(limit)
        )
    ).all()
    return [
        CrawlRunOut(
            id=run.id,
            started_at=run.started_at,
            finished_at=run.finished_at,
            status=run.status,
            total_channels=run.total_channels,
            done_channels=run.done_channels,
            new_products=run.new_products,
            updated_products=run.updated_products,
            error_channels=run.error_channels,
            gpt_fallback_count=int(gpt_fallback_count or 0),
        )
        for run, gpt_fallback_count in rows
    ]


@router.get("/crawl-runs/{run_id}", response_model=CrawlRunDetail)
async def get_crawl_run_detail(
    run_id: int,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """특정 크롤 실행 상세 (채널별 로그 포함)."""
    run = (
        await db.execute(
            select(CrawlRun)
            .where(CrawlRun.id == run_id)
            .options(selectinload(CrawlRun.logs).selectinload(CrawlChannelLog.channel))
        )
    ).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="crawl run not found")

    logs_out = [
        CrawlChannelLogOut(
            id=log.id,
            channel_id=log.channel_id,
            channel_name=log.channel.name if log.channel else str(log.channel_id),
            status=log.status,
            products_found=log.products_found,
            products_new=log.products_new,
            products_updated=log.products_updated,
            error_msg=log.error_msg,
            error_type=log.error_type,
            strategy=log.strategy,
            duration_ms=log.duration_ms,
            crawled_at=log.crawled_at,
        )
        for log in sorted(run.logs, key=lambda l: l.crawled_at)
    ]
    return CrawlRunDetail(
        id=run.id,
        started_at=run.started_at,
        finished_at=run.finished_at,
        status=run.status,
        total_channels=run.total_channels,
        done_channels=run.done_channels,
        new_products=run.new_products,
        updated_products=run.updated_products,
        error_channels=run.error_channels,
        logs=logs_out,
    )


@router.get("/crawl-runs/{run_id}/stream")
async def stream_crawl_run(
    run_id: int,
    token: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    # SSE는 Authorization 헤더를 쓸 수 없어 쿼리 파라미터로 인증
    expected = settings.admin_bearer_token
    if expected is None and settings.api_debug:
        pass  # 로컬 개발 허용
    elif token != expected:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    """SSE — 크롤 실행 중 실시간 진행상황 스트리밍 (3초 폴링)."""

    async def event_generator():
        from fashion_engine.database import AsyncSessionLocal
        sent_log_ids: set[int] = set()
        while True:
            # 매 3초마다 DB 폴링
            try:
                async with AsyncSessionLocal() as sess:
                    run = (
                        await sess.execute(select(CrawlRun).where(CrawlRun.id == run_id))
                    ).scalar_one_or_none()
                    if not run:
                        yield f"event: error\ndata: {json.dumps({'detail': 'not found'})}\n\n"
                        return

                    # 새 로그만 전송
                    log_query = (
                        select(CrawlChannelLog)
                        .where(CrawlChannelLog.run_id == run_id)
                        .options(selectinload(CrawlChannelLog.channel))
                        .order_by(CrawlChannelLog.crawled_at)
                    )
                    if sent_log_ids:
                        log_query = log_query.where(CrawlChannelLog.id.not_in(sent_log_ids))
                    new_logs = (await sess.execute(log_query)).scalars().all()

                for log in new_logs:
                    sent_log_ids.add(log.id)
                    payload = json.dumps({
                        "id": log.id,
                        "channel_id": log.channel_id,
                        "channel_name": log.channel.name if log.channel else str(log.channel_id),
                        "status": log.status,
                        "products_found": log.products_found,
                        "products_new": log.products_new,
                        "products_updated": log.products_updated,
                        "error_msg": log.error_msg,
                        "error_type": log.error_type,
                        "strategy": log.strategy,
                        "duration_ms": log.duration_ms,
                        "crawled_at": log.crawled_at.isoformat(),
                    })
                    yield f"event: log\ndata: {payload}\n\n"

                # 진행률 업데이트
                progress = json.dumps({
                    "run_id": run.id,
                    "status": run.status,
                    "total_channels": run.total_channels,
                    "done_channels": run.done_channels,
                    "new_products": run.new_products,
                    "error_channels": run.error_channels,
                })
                yield f"event: progress\ndata: {progress}\n\n"

                is_done = run.status != "running"

                if is_done:
                    yield f"event: done\ndata: {json.dumps({'status': run.status})}\n\n"
                    return

            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"
                return

            await asyncio.sleep(3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/catalog-stats")
async def get_catalog_stats(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total = int((await db.execute(select(func.count(ProductCatalog.id)))).scalar() or 0)
    with_brand = int(
        (
            await db.execute(
                select(func.count(ProductCatalog.id)).where(ProductCatalog.brand_id.is_not(None))
            )
        ).scalar()
        or 0
    )
    multi_channel = int(
        (
            await db.execute(
                select(func.count(ProductCatalog.id)).where(ProductCatalog.listing_count >= 2)
            )
        ).scalar()
        or 0
    )
    last_updated = (
        await db.execute(select(func.max(ProductCatalog.updated_at)))
    ).scalar_one_or_none()
    return {
        "total": total,
        "with_brand": with_brand,
        "multi_channel": multi_channel,
        "last_updated": last_updated.isoformat() if last_updated else None,
    }


# ── 채널 노트 (운영자 피드백) ─────────────────────────────────────────────────


@router.get("/channels/{channel_id}/notes", response_model=list[ChannelNoteOut])
async def list_channel_notes(
    channel_id: int,
    include_resolved: bool = Query(False, description="해결된 노트 포함"),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """채널별 운영자 노트 목록."""
    query = (
        select(ChannelNote, Channel.name)
        .join(Channel, Channel.id == ChannelNote.channel_id)
        .where(ChannelNote.channel_id == channel_id)
        .order_by(ChannelNote.created_at.desc())
    )
    if not include_resolved:
        query = query.where(ChannelNote.resolved_at.is_(None))
    rows = (await db.execute(query)).all()
    return [
        ChannelNoteOut(
            id=note.id,
            channel_id=note.channel_id,
            channel_name=channel_name,
            note_type=note.note_type,
            body=note.body,
            operator=note.operator,
            created_at=note.created_at,
            resolved_at=note.resolved_at,
        )
        for note, channel_name in rows
    ]


@router.post("/channels/{channel_id}/notes", response_model=ChannelNoteOut)
async def create_channel_note(
    channel_id: int,
    payload: ChannelNoteCreate,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """채널 노트 생성."""
    channel = (await db.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="channel not found")
    note = ChannelNote(
        channel_id=channel_id,
        note_type=payload.note_type,
        body=payload.body,
        operator=payload.operator,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return ChannelNoteOut(
        id=note.id,
        channel_id=note.channel_id,
        channel_name=channel.name,
        note_type=note.note_type,
        body=note.body,
        operator=note.operator,
        created_at=note.created_at,
        resolved_at=note.resolved_at,
    )


@router.patch("/channels/{channel_id}/notes/{note_id}/resolve")
async def resolve_channel_note(
    channel_id: int,
    note_id: int,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """채널 노트 해결 처리."""
    note = (
        await db.execute(
            select(ChannelNote)
            .where(ChannelNote.id == note_id, ChannelNote.channel_id == channel_id)
        )
    ).scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="note not found")
    note.resolved_at = datetime.utcnow()
    await db.commit()
    return {"ok": True, "resolved_at": note.resolved_at.isoformat()}
