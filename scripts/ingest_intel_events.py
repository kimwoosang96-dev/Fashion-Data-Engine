from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import typer
from rich.console import Console
from sqlalchemy import Float, Integer, and_, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.brand import Brand  # noqa: E402
from fashion_engine.models.brand_collaboration import BrandCollaboration  # noqa: E402
from fashion_engine.models.channel import Channel  # noqa: E402
from fashion_engine.models.drop import Drop  # noqa: E402
from fashion_engine.models.fashion_news import FashionNews  # noqa: E402
from fashion_engine.models.intel import (  # noqa: E402
    IntelEvent,
    IntelEventSource,
    IntelIngestLog,
    IntelIngestRun,
)
from fashion_engine.models.price_history import PriceHistory  # noqa: E402
from fashion_engine.models.product import Product  # noqa: E402
from fashion_engine.services.intel_service import normalize_domain  # noqa: E402

app = typer.Typer()
console = Console()


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _date_to_dt(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is None else value.astimezone(UTC).replace(tzinfo=None)
    return datetime.combine(value, time.min)


def _build_dedup_key(event_type: str, source_table: str, source_pk: int) -> str:
    return f"{event_type}:{source_table}:{source_pk}"


def _details_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


async def _log(
    db: AsyncSession,
    run_id: int,
    level: str,
    message: str,
    source_table: str | None = None,
    source_pk: int | None = None,
) -> None:
    db.add(
        IntelIngestLog(
            run_id=run_id,
            level=level,
            message=message,
            source_table=source_table,
            source_pk=source_pk,
        )
    )


async def _upsert_event(
    db: AsyncSession,
    *,
    run: IntelIngestRun,
    source_table: str,
    source_pk: int,
    event_type: str,
    layer: str,
    title: str,
    summary: str | None,
    event_time: datetime | None,
    brand_id: int | None = None,
    channel_id: int | None = None,
    product_id: int | None = None,
    product_key: str | None = None,
    geo_country: str | None = None,
    source_url: str | None = None,
    source_type: str = "crawler",
    severity: str = "medium",
    confidence: str = "medium",
    details: dict | None = None,
    published_at: datetime | None = None,
) -> None:
    dedup_key = _build_dedup_key(event_type, source_table, source_pk)
    now = utcnow()
    norm_country = (geo_country or "").upper()
    if len(norm_country) != 2:
        norm_country = ""
    geo_precision = "country" if norm_country else "global"
    existing = (
        await db.execute(select(IntelEvent).where(IntelEvent.dedup_key == dedup_key))
    ).scalar_one_or_none()
    if existing:
        existing.layer = layer
        existing.title = title
        existing.summary = summary
        existing.event_time = event_time
        existing.brand_id = brand_id
        existing.channel_id = channel_id
        existing.product_id = product_id
        existing.product_key = product_key
        existing.geo_country = norm_country or None
        existing.geo_precision = geo_precision
        existing.source_url = source_url
        existing.source_domain = normalize_domain(source_url)
        existing.source_type = source_type
        existing.severity = severity
        existing.confidence = confidence
        existing.details_json = _details_json(details or {})
        existing.last_seen_at = now
        run.updated_count += 1
        event = existing
    else:
        event = IntelEvent(
            event_type=event_type,
            layer=layer,
            title=title[:500],
            summary=summary,
            event_time=event_time,
            detected_at=now,
            severity=severity,
            confidence=confidence,
            brand_id=brand_id,
            channel_id=channel_id,
            product_id=product_id,
            product_key=product_key,
            geo_country=norm_country or None,
            geo_precision=geo_precision,
            source_url=source_url,
            source_domain=normalize_domain(source_url),
            source_type=source_type,
            dedup_key=dedup_key,
            details_json=_details_json(details or {}),
            is_active=True,
            is_verified=False,
            last_seen_at=now,
        )
        db.add(event)
        await db.flush()
        run.inserted_count += 1

    source_row = (
        await db.execute(
            select(IntelEventSource).where(
                IntelEventSource.source_table == source_table,
                IntelEventSource.source_pk == source_pk,
            )
        )
    ).scalar_one_or_none()
    if source_row:
        source_row.event_id = event.id
        source_row.run_id = run.id
        source_row.source_url = source_url
        source_row.source_published_at = published_at
    else:
        db.add(
            IntelEventSource(
                event_id=event.id,
                run_id=run.id,
                source_table=source_table,
                source_pk=source_pk,
                source_url=source_url,
                source_published_at=published_at,
            )
        )


async def _ingest_drops(db: AsyncSession, run: IntelIngestRun) -> None:
    rows = list((await db.execute(select(Drop))).scalars().all())
    for row in rows:
        await _upsert_event(
            db,
            run=run,
            source_table="drops",
            source_pk=row.id,
            event_type="drop",
            layer="drops",
            title=row.product_name,
            summary=f"status={row.status}",
            event_time=_date_to_dt(row.release_date) or row.detected_at,
            brand_id=row.brand_id,
            product_key=row.product_key,
            source_url=row.source_url,
            source_type="crawler",
            severity="high" if row.status in {"upcoming", "released"} else "medium",
            confidence="high",
            details={
                "drop_status": row.status,
                "price_krw": row.price_krw,
                "image_url": row.image_url,
            },
            published_at=row.detected_at,
        )


async def _ingest_collabs(db: AsyncSession, run: IntelIngestRun) -> None:
    rows = list((await db.execute(select(BrandCollaboration))).scalars().all())
    for row in rows:
        event_time = None
        if row.release_year:
            event_time = datetime(row.release_year, 1, 1)
        await _upsert_event(
            db,
            run=run,
            source_table="brand_collaborations",
            source_pk=row.id,
            event_type="collab",
            layer="collabs",
            title=row.collab_name,
            summary=row.notes,
            event_time=event_time,
            brand_id=row.brand_a_id,
            source_url=row.source_url,
            source_type="crawler",
            severity="high" if row.hype_score >= 80 else "medium",
            confidence="medium",
            details={
                "brand_a_id": row.brand_a_id,
                "brand_b_id": row.brand_b_id,
                "hype_score": row.hype_score,
                "release_year": row.release_year,
                "collab_category": row.collab_category,
            },
            published_at=row.created_at,
        )


async def _ingest_news(db: AsyncSession, run: IntelIngestRun) -> None:
    rows = list((await db.execute(select(FashionNews))).scalars().all())
    for row in rows:
        await _upsert_event(
            db,
            run=run,
            source_table="fashion_news",
            source_pk=row.id,
            event_type="news",
            layer="news",
            title=row.title,
            summary=row.summary,
            event_time=row.published_at or row.crawled_at,
            brand_id=row.entity_id if row.entity_type == "brand" else None,
            channel_id=row.entity_id if row.entity_type == "channel" else None,
            source_url=row.url,
            source_type="media" if row.source not in {"instagram", "website"} else "social",
            severity="low",
            confidence="medium",
            details={"entity_type": row.entity_type, "source": row.source},
            published_at=row.published_at,
        )


async def _pick_sales_spike_candidates(
    db: AsyncSession, window_hours: int
) -> list[tuple[int, int, float, float]]:
    """
    (brand_id, sale_count, sale_ratio_48h, avg_discount_48h) 반환.
    조건: sale_count >= 15 AND (sale_ratio_delta >= 0.15 OR discount_delta >= 0.10)
    """
    since_window = utcnow() - timedelta(hours=window_hours)
    since_baseline = utcnow() - timedelta(days=7)

    window_rows = (
        await db.execute(
            select(
                Product.brand_id,
                func.count(Product.id).label("total_count"),
                func.sum(cast(Product.is_sale, Integer)).label("sale_count"),
            )
            .where(
                Product.brand_id.is_not(None),
                Product.is_active == True,
                Product.updated_at >= since_window,
            )
            .group_by(Product.brand_id)
            .having(func.sum(cast(Product.is_sale, Integer)) >= 15)
        )
    ).all()

    if not window_rows:
        return []

    brand_ids = [int(r.brand_id) for r in window_rows if r.brand_id is not None]
    baseline_rows = (
        await db.execute(
            select(
                Product.brand_id,
                func.count(Product.id).label("total_count"),
                func.sum(cast(Product.is_sale, Integer)).label("sale_count"),
            )
            .where(
                Product.brand_id.in_(brand_ids),
                Product.is_active == True,
                Product.updated_at >= since_baseline,
            )
            .group_by(Product.brand_id)
        )
    ).all()

    baseline_map = {
        int(r.brand_id): (
            float((r.sale_count or 0) / max(r.total_count or 1, 1)),
            0.0,
        )
        for r in baseline_rows
        if r.brand_id is not None
    }

    window_discount_rows = (
        await db.execute(
            select(
                Product.brand_id,
                func.avg(cast(PriceHistory.discount_rate, Float) / 100.0).label("avg_discount"),
            )
            .join(PriceHistory, PriceHistory.product_id == Product.id)
            .where(
                Product.brand_id.in_(brand_ids),
                PriceHistory.is_sale == True,
                PriceHistory.discount_rate.is_not(None),
                PriceHistory.crawled_at >= since_window,
            )
            .group_by(Product.brand_id)
        )
    ).all()
    baseline_discount_rows = (
        await db.execute(
            select(
                Product.brand_id,
                func.avg(cast(PriceHistory.discount_rate, Float) / 100.0).label("avg_discount"),
            )
            .join(PriceHistory, PriceHistory.product_id == Product.id)
            .where(
                Product.brand_id.in_(brand_ids),
                PriceHistory.is_sale == True,
                PriceHistory.discount_rate.is_not(None),
                PriceHistory.crawled_at >= since_baseline,
            )
            .group_by(Product.brand_id)
        )
    ).all()
    window_discount_map = {
        int(r.brand_id): float(r.avg_discount or 0.0)
        for r in window_discount_rows
        if r.brand_id is not None
    }
    baseline_discount_map = {
        int(r.brand_id): float(r.avg_discount or 0.0)
        for r in baseline_discount_rows
        if r.brand_id is not None
    }

    results: list[tuple[int, int, float, float]] = []
    for r in window_rows:
        if r.brand_id is None:
            continue
        brand_id = int(r.brand_id)
        sale_count = int(r.sale_count or 0)
        ratio_48h = float((r.sale_count or 0) / max(r.total_count or 1, 1))
        discount_48h = window_discount_map.get(brand_id, 0.0)
        base_ratio, base_discount = baseline_map.get(brand_id, (0.0, 0.0))
        if brand_id in baseline_discount_map:
            base_discount = baseline_discount_map[brand_id]
        ratio_delta = ratio_48h - base_ratio
        discount_delta = discount_48h - base_discount

        if ratio_delta >= 0.15 or discount_delta >= 0.10:
            results.append((brand_id, sale_count, ratio_48h, discount_48h))
    return results


async def _ingest_derived_spike(db: AsyncSession, run: IntelIngestRun, window_hours: int) -> None:
    now = utcnow()
    for brand_id, sale_count, sale_ratio, avg_discount in await _pick_sales_spike_candidates(
        db, window_hours
    ):
        brand = (
            await db.execute(select(Brand).where(Brand.id == brand_id))
        ).scalar_one_or_none()
        if not brand:
            continue
        source_pk = int(now.timestamp()) + brand_id
        severity = "critical" if sale_ratio >= 0.4 else "high" if sale_ratio >= 0.25 else "medium"
        geo_country = None
        if brand.origin_country and len(brand.origin_country.strip()) == 2:
            geo_country = brand.origin_country.strip().upper()
        await _upsert_event(
            db,
            run=run,
            source_table="derived_spike",
            source_pk=source_pk,
            event_type="sales_spike",
            layer="sales_spike",
            title=f"{brand.name} 세일 급증",
            summary=f"{window_hours}시간 내 세일 활성 상품 {sale_count}개",
            event_time=now,
            brand_id=brand_id,
            geo_country=geo_country,
            source_url=brand.official_url,
            source_type="derived",
            severity=severity,
            confidence="medium",
            details={
                "window_hours": window_hours,
                "sale_count": sale_count,
                "sale_ratio_48h": round(sale_ratio, 4),
                "avg_discount_48h": round(avg_discount, 4),
            },
            published_at=now,
        )


async def run(job: str, window_hours: int = 48) -> int:
    await init_db()
    async with AsyncSessionLocal() as db:
        run_row = IntelIngestRun(job_name=job, status="running", started_at=utcnow())
        db.add(run_row)
        await db.flush()

        try:
            if job in {"mirror", "drops_collabs_news"}:
                await _ingest_drops(db, run_row)
                await _ingest_collabs(db, run_row)
                await _ingest_news(db, run_row)
            elif job == "derived_spike":
                await _ingest_derived_spike(db, run_row, window_hours=window_hours)
            else:
                await _log(db, run_row.id, "ERROR", f"unknown job: {job}")
                run_row.error_count += 1
                run_row.status = "failed"
                run_row.finished_at = utcnow()
                await db.commit()
                return 1

            run_row.status = "done"
            run_row.finished_at = utcnow()
            await db.commit()
            console.print(
                f"[bold green]intel ingest 완료[/bold green] job={job} "
                f"inserted={run_row.inserted_count} updated={run_row.updated_count} errors={run_row.error_count}"
            )
            return 0
        except Exception as exc:  # pragma: no cover - runtime guard
            run_row.status = "failed"
            run_row.error_count += 1
            run_row.finished_at = utcnow()
            await _log(db, run_row.id, "ERROR", str(exc)[:500])
            await db.commit()
            console.print(f"[bold red]intel ingest 실패[/bold red] {exc}")
            return 1


@app.command()
def main(
    job: str = typer.Option(
        "mirror",
        "--job",
        help="mirror | drops_collabs_news | derived_spike",
    ),
    window_hours: int = typer.Option(48, "--window-hours", min=1, max=240),
):
    raise SystemExit(asyncio.run(run(job=job, window_hours=window_hours)))


if __name__ == "__main__":
    app()
