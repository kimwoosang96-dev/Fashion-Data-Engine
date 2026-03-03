from __future__ import annotations

import base64
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fashion_engine.config import settings
from fashion_engine.models.brand import Brand
from fashion_engine.models.channel import Channel
from fashion_engine.models.intel import IntelEvent
from fashion_engine.models.product import Product

DEFAULT_LIMIT = 100
MAX_LIMIT = 300
CONFIDENCE_ORDER = {"low": 1, "medium": 2, "high": 3}
SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}
logger = logging.getLogger(__name__)

LAYER_EMOJI = {
    "drops": "🚀",
    "collabs": "🤝",
    "news": "📰",
    "sale_start": "🔥",
    "sold_out": "⚫",
    "restock": "🟢",
    "sales_spike": "📈",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_domain(url: str | None) -> str | None:
    if not url:
        return None
    host = urlparse(url).netloc.lower()
    return host.replace("www.", "") if host else None


def calc_confidence_score(
    source_type: str,
    brand_mapped: bool,
    channel_mapped: bool,
    sources_count: int,
    geo_precision: str,
) -> tuple[int, str]:
    """
    PRD v1.1 §7.1 기반 confidence 점수 계산.
    Returns: (score 0-100, label "low" | "medium" | "high")
    """
    score = 0
    if source_type == "official":
        score += 50
    elif source_type == "crawler":
        score += 40
    elif source_type == "media":
        score += 30
    elif source_type == "social":
        score += 20

    if brand_mapped or channel_mapped:
        score += 10
    if sources_count >= 2:
        score += 15
    if geo_precision in ("point", "city"):
        score += 5

    label = "high" if score >= 80 else "medium" if score >= 50 else "low"
    return score, label


def _calc_sale_start_severity(discount_rate: float | None) -> str:
    """discount_rate(0~1 또는 0~100 입력 지원) 기반 severity."""
    if discount_rate is None:
        return "low"
    pct = discount_rate * 100 if discount_rate <= 1.0 else discount_rate
    if pct >= 50:
        return "critical"
    if pct >= 30:
        return "high"
    if pct >= 15:
        return "medium"
    return "low"


async def notify_discord_if_warranted(event: IntelEvent) -> None:
    """severity=critical/high 이벤트를 Intel 전용 Discord webhook으로 전송."""
    if event.severity not in {"critical", "high"}:
        return
    if not settings.intel_discord_webhook_url:
        return

    emoji = LAYER_EMOJI.get(event.layer, "📌")
    color = 0xFF4444 if event.severity == "critical" else 0xFF8800
    brand_name = event.brand.name if getattr(event, "brand", None) else "-"
    event_ts = event.event_time or event.detected_at

    payload = {
        "embeds": [
            {
                "color": color,
                "title": f"{emoji} {event.title[:200]}",
                "description": event.summary or "",
                "fields": [
                    {"name": "Layer", "value": event.layer, "inline": True},
                    {"name": "Severity", "value": event.severity, "inline": True},
                    {"name": "Brand", "value": brand_name, "inline": True},
                ],
                "url": f"https://fashion-data-engine.vercel.app/intel?event_id={event.id}",
                "timestamp": event_ts.replace(tzinfo=timezone.utc).isoformat()
                if event_ts.tzinfo is None
                else event_ts.isoformat(),
            }
        ]
    }
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(settings.intel_discord_webhook_url, json=payload)
            resp.raise_for_status()
    except Exception as exc:
        logger.warning("Discord intel alert 발송 실패: %s", exc)


def build_time_cutoff(time_range: str) -> datetime | None:
    now = utcnow()
    if time_range == "24h":
        return now - timedelta(hours=24)
    if time_range == "7d":
        return now - timedelta(days=7)
    if time_range == "30d":
        return now - timedelta(days=30)
    if time_range == "90d":
        return now - timedelta(days=90)
    return None


def encode_cursor(sort_time: datetime, row_id: int) -> str:
    raw = json.dumps({"ts": sort_time.isoformat(), "id": row_id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")


def decode_cursor(cursor: str) -> tuple[datetime, int]:
    payload = json.loads(base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8"))
    return datetime.fromisoformat(payload["ts"]), int(payload["id"])


def event_sort_time(event: IntelEvent) -> datetime:
    return event.event_time or event.detected_at


def _rank_ok(value: str | None, min_value: str | None, order: dict[str, int]) -> bool:
    if not min_value:
        return True
    return order.get((value or "").lower(), 0) >= order.get(min_value.lower(), 0)


async def list_intel_events(
    db: AsyncSession,
    *,
    layers: list[str] | None = None,
    brand_slug: str | None = None,
    channel_id: int | None = None,
    country: str | None = None,
    q: str | None = None,
    min_confidence: str | None = None,
    min_severity: str | None = None,
    time_range: str = "7d",
    cursor: str | None = None,
    limit: int = DEFAULT_LIMIT,
    bbox: tuple[float, float, float, float] | None = None,
) -> dict:
    limit = max(1, min(limit, MAX_LIMIT))
    stmt = (
        select(IntelEvent)
        .options(
            selectinload(IntelEvent.brand),
            selectinload(IntelEvent.channel),
            selectinload(IntelEvent.product),
        )
        .where(IntelEvent.is_active == True)
    )

    cutoff = build_time_cutoff(time_range)
    if cutoff:
        stmt = stmt.where(
            or_(
                IntelEvent.event_time >= cutoff,
                IntelEvent.detected_at >= cutoff,
            )
        )
    if layers:
        stmt = stmt.where(IntelEvent.layer.in_(layers))
    if country:
        stmt = stmt.where(IntelEvent.geo_country == country.upper())
    if channel_id:
        stmt = stmt.where(IntelEvent.channel_id == channel_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (IntelEvent.title.ilike(like)) | (IntelEvent.summary.ilike(like))
        )
    if bbox:
        min_lng, min_lat, max_lng, max_lat = bbox
        stmt = stmt.where(
            and_(
                IntelEvent.geo_lng.is_not(None),
                IntelEvent.geo_lat.is_not(None),
                IntelEvent.geo_lng >= min_lng,
                IntelEvent.geo_lng <= max_lng,
                IntelEvent.geo_lat >= min_lat,
                IntelEvent.geo_lat <= max_lat,
            )
        )
    if brand_slug:
        brand_id = (
            await db.execute(select(Brand.id).where(Brand.slug == brand_slug))
        ).scalar_one_or_none()
        if not brand_id:
            return {"items": [], "next_cursor": None, "total": 0}
        stmt = stmt.where(IntelEvent.brand_id == brand_id)

    stmt = stmt.order_by(
        func.coalesce(IntelEvent.event_time, IntelEvent.detected_at).desc(),
        IntelEvent.id.desc(),
    )

    rows = list((await db.execute(stmt)).scalars().all())
    filtered = [
        e
        for e in rows
        if _rank_ok(e.confidence, min_confidence, CONFIDENCE_ORDER)
        and _rank_ok(e.severity, min_severity, SEVERITY_ORDER)
    ]

    if cursor:
        cursor_time, cursor_id = decode_cursor(cursor)
        filtered = [
            e
            for e in filtered
            if (event_sort_time(e), e.id) < (cursor_time, cursor_id)
        ]

    page = filtered[:limit]
    next_cursor = (
        encode_cursor(event_sort_time(page[-1]), page[-1].id) if len(filtered) > limit else None
    )
    return {
        "items": [serialize_event_row(e) for e in page],
        "next_cursor": next_cursor,
        "total": len(filtered),
    }


def serialize_event_row(event: IntelEvent) -> dict:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "layer": event.layer,
        "title": event.title,
        "summary": event.summary,
        "event_time": (event.event_time.isoformat() if event.event_time else None),
        "detected_at": event.detected_at.isoformat(),
        "severity": event.severity,
        "confidence": event.confidence,
        "brand_id": event.brand_id,
        "brand_name": event.brand.name if event.brand else None,
        "brand_slug": event.brand.slug if event.brand else None,
        "channel_id": event.channel_id,
        "channel_name": event.channel.name if event.channel else None,
        "product_id": event.product_id,
        "product_name": event.product.name if event.product else None,
        "product_key": event.product_key,
        "geo_country": event.geo_country,
        "geo_city": event.geo_city,
        "geo_lat": event.geo_lat,
        "geo_lng": event.geo_lng,
        "geo_precision": event.geo_precision,
        "source_url": event.source_url,
        "source_domain": event.source_domain,
        "source_type": event.source_type,
        "is_verified": event.is_verified,
    }


async def get_map_points(
    db: AsyncSession,
    *,
    layers: list[str] | None = None,
    time_range: str = "7d",
    bbox: tuple[float, float, float, float] | None = None,
    limit: int = 1000,
) -> list[dict]:
    payload = await list_intel_events(
        db,
        layers=layers,
        time_range=time_range,
        bbox=bbox,
        limit=min(limit, 2000),
    )
    points = []
    for item in payload["items"]:
        if item["geo_lat"] is None or item["geo_lng"] is None:
            continue
        points.append(
            {
                "id": item["id"],
                "layer": item["layer"],
                "severity": item["severity"],
                "confidence": item["confidence"],
                "lat": item["geo_lat"],
                "lng": item["geo_lng"],
                "title": item["title"],
                "event_time": item["event_time"] or item["detected_at"],
                "geo_precision": item["geo_precision"],
            }
        )
    return points


def _bucket_label(dt: datetime, granularity: str) -> str:
    if granularity == "hour":
        return dt.strftime("%Y-%m-%d %H:00")
    if granularity == "week":
        y, w, _ = dt.isocalendar()
        return f"{y}-W{w:02d}"
    return dt.strftime("%Y-%m-%d")


async def get_timeline(
    db: AsyncSession,
    *,
    layers: list[str] | None = None,
    time_range: str = "30d",
    granularity: str = "day",
) -> dict:
    payload = await list_intel_events(
        db,
        layers=layers,
        time_range=time_range,
        limit=20000,
    )
    buckets: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in payload["items"]:
        when = row["event_time"] or row["detected_at"]
        dt = datetime.fromisoformat(when)
        label = _bucket_label(dt, granularity)
        buckets[label][row["layer"]] += 1
        buckets[label]["_total"] += 1

    timeline = []
    for bucket in sorted(buckets.keys()):
        counts = dict(buckets[bucket])
        timeline.append(
            {
                "bucket": bucket,
                "total": counts.pop("_total", 0),
                "layers": counts,
            }
        )
    return {"granularity": granularity, "items": timeline}


async def get_highlights(
    db: AsyncSession,
    *,
    layers: list[str] | None = None,
    time_range: str = "7d",
    limit: int = 20,
) -> list[dict]:
    payload = await list_intel_events(
        db, layers=layers, time_range=time_range, limit=500
    )
    items = payload["items"]
    items.sort(
        key=lambda x: (
            SEVERITY_ORDER.get((x.get("severity") or "").lower(), 0),
            CONFIDENCE_ORDER.get((x.get("confidence") or "").lower(), 0),
            x.get("event_time") or x.get("detected_at"),
        ),
        reverse=True,
    )
    return items[: max(1, min(limit, 100))]


async def get_event_detail(db: AsyncSession, event_id: int) -> dict | None:
    row = (
        await db.execute(
            select(IntelEvent)
            .options(
                selectinload(IntelEvent.brand),
                selectinload(IntelEvent.channel),
                selectinload(IntelEvent.product),
                selectinload(IntelEvent.sources),
            )
            .where(IntelEvent.id == event_id)
        )
    ).scalar_one_or_none()
    if not row:
        return None
    payload = serialize_event_row(row)
    payload["details_json"] = row.details_json
    payload["sources"] = [
        {
            "id": s.id,
            "source_table": s.source_table,
            "source_pk": s.source_pk,
            "source_url": s.source_url,
            "source_published_at": (
                s.source_published_at.isoformat() if s.source_published_at else None
            ),
        }
        for s in row.sources
    ]
    return payload


async def upsert_derived_product_event(
    db: AsyncSession,
    *,
    event_type: str,
    product: Product,
    channel: Channel,
    brand: Brand | None,
    title: str,
    summary: str | None,
    source_url: str | None,
    details: dict | None = None,
) -> IntelEvent:
    now = utcnow()
    event_time = product.updated_at or now
    dedup_key = f"derived:{event_type}:product:{product.id}:{int(event_time.timestamp())}"
    existing = (
        await db.execute(select(IntelEvent).where(IntelEvent.dedup_key == dedup_key))
    ).scalar_one_or_none()
    if existing:
        return existing

    layer = event_type
    if event_type == "sales_spike":
        layer = "sales_spike"
    if event_type == "sale_start":
        severity = _calc_sale_start_severity(
            float(details.get("discount_rate")) if details and details.get("discount_rate") is not None else None
        )
    elif event_type == "sold_out":
        severity = "high"
    elif event_type == "restock":
        severity = "medium"
    else:
        severity = "medium"
    geo_country = (channel.country or "").upper()[:2] or None
    geo_precision = "country" if geo_country else "global"

    row = IntelEvent(
        event_type=event_type,
        layer=layer,
        title=title[:500],
        summary=summary,
        event_time=event_time,
        detected_at=now,
        severity=severity,
        confidence="high",
        brand_id=brand.id if brand else None,
        channel_id=channel.id,
        product_id=product.id,
        product_key=product.product_key,
        geo_country=geo_country,
        geo_precision=geo_precision,
        source_url=source_url,
        source_domain=normalize_domain(source_url),
        source_type="derived",
        dedup_key=dedup_key,
        details_json=json.dumps(details or {}, ensure_ascii=False),
        is_active=True,
        is_verified=False,
        last_seen_at=now,
    )
    db.add(row)
    await db.flush()
    await notify_discord_if_warranted(row)
    return row
