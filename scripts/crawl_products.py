"""
채널별 제품·가격 크롤링 및 DB 저장 스크립트.

알림 트리거 (DISCORD_WEBHOOK_URL 설정 시 자동 전송):
  🚀 신제품 — product_key 처음 등장
  🔥 세일 전환 — is_sale False → True
  📉 가격 하락 — 직전 KRW 대비 10%+ 하락

사용법:
    uv run python scripts/crawl_products.py              # 전체 Shopify 채널
    uv run python scripts/crawl_products.py --limit 3    # 처음 3개 채널만 (테스트)
    uv run python scripts/crawl_products.py --channel-type edit-shop
    uv run python scripts/crawl_products.py --concurrency 3  # 동시 처리 채널 수

주의:
    크롤 직전에 `channel_probe.py --all --force-retag`를 실행하면 Shopify IP rate-limit
    (429)이 발생할 수 있습니다. probe는 별도 시간대(권장: 크롤 30분 이상 전)에 실행하세요.
"""
import asyncio
from dataclasses import dataclass, field
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import typer
from sqlalchemy.dialects.postgresql import insert as pg_insert
from rich.console import Console
from rich.table import Table
from sqlalchemy import desc, func, select, text
from sqlalchemy.exc import DBAPIError

from fashion_engine.config import settings
from fashion_engine.database import init_db, AsyncSessionLocal
from fashion_engine.models.channel import Channel
from fashion_engine.models.channel_brand import ChannelBrand
from fashion_engine.models.brand import Brand
from fashion_engine.models.price_history import PriceHistory
from fashion_engine.models.product import Product
from fashion_engine.models.crawl_run import CrawlRun, CrawlChannelLog
from fashion_engine.models.activity_feed import ActivityFeed
from fashion_engine.crawler.product_crawler import ProductCrawler, ChannelProductResult
from fashion_engine.services.product_service import (
    build_price_history_row,
    build_product_upsert_row,
    get_rate_to_krw,
    find_brands_by_vendors,
    get_existing_products_by_urls,
    get_prev_prices_by_product_ids,
    upsert_product,
)
from fashion_engine.services.channel_service import update_platform
from fashion_engine.services.catalog_service import build_catalog_incremental
from watch_agent import run_channel_watch
from fashion_engine.services.intel_service import upsert_derived_product_event
from fashion_engine.services.alert_service import (
    AlertPayload,
    new_product_alert,
    sale_alert,
    price_drop_alert,
)
from fashion_engine.services.watchlist_service import should_alert

logger = logging.getLogger(__name__)
console = Console()
app = typer.Typer()

SKIP_TYPES = {"secondhand-marketplace", "non-fashion"}

# 채널 타입별 크롤 우선순위 (낮을수록 먼저)
_CHANNEL_PRIORITY = {"brand-store": 0, "edit-shop": 1}

# 채널 platform별 최대 크롤 시간 (초) — asyncio.wait_for 상한
_CHANNEL_TIMEOUT_SECS: dict[str, int] = {
    "cafe24": 600,   # 카테고리 수십~수백 개 가능
    "shopify": 180,
    "default": 300,
}

_POSTGRES_CRAWL_TIMEOUT_SQL = (
    "SET LOCAL idle_in_transaction_session_timeout = '60s'",
    "SET LOCAL lock_timeout = '5s'",
    "SET LOCAL statement_timeout = '120s'",
)
_PRODUCT_BULK_CHUNK_SIZE = 500
_PRICE_HISTORY_BULK_CHUNK_SIZE = 1000


async def _apply_crawl_db_timeouts(db) -> None:
    """PostgreSQL 저장 세션에 크롤 전용 timeout을 건다."""
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for sql in _POSTGRES_CRAWL_TIMEOUT_SQL:
        await db.execute(text(sql))


def _classify_db_error(exc: Exception) -> str | None:
    """DB 예외를 lock/statement timeout 중심으로 분류한다."""
    if not isinstance(exc, DBAPIError):
        return None

    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    msg = str(orig or exc).lower()

    if sqlstate == "55P03" or "lock timeout" in msg:
        return "lock_timeout"
    if sqlstate == "57014" or "statement timeout" in msg:
        return "statement_timeout"
    return None


@dataclass
class PendingDerivedEvent:
    event_type: str
    product_id: int
    brand_id: int | None
    title: str
    summary: str
    source_url: str
    details: dict


@dataclass
class PendingAlertJob:
    alert_kind: str
    brand_slug: str | None
    product_key: str | None
    payload: AlertPayload


@dataclass
class ChannelPostCommitWork:
    derived_events: list[PendingDerivedEvent] = field(default_factory=list)
    alert_jobs: list[PendingAlertJob] = field(default_factory=list)


@dataclass
class ChannelSaveOutcome:
    products_count: int = 0
    sale_count: int = 0
    new_count: int = 0
    updated_count: int = 0
    post_commit_work: ChannelPostCommitWork = field(default_factory=ChannelPostCommitWork)


def _dedupe_product_infos(products: list) -> list:
    deduped: dict[str, object] = {}
    for info in products:
        deduped[info.product_url] = info
    return list(deduped.values())


def _chunk_rows(rows: list[dict], chunk_size: int) -> list[list[dict]]:
    return [rows[idx:idx + chunk_size] for idx in range(0, len(rows), chunk_size)]


async def _load_fast_poll_sale_counts(db, channel_ids: list[int]) -> dict[int, int]:
    if not channel_ids:
        return {}
    cutoff = datetime.utcnow() - timedelta(days=14)
    rows = (
        await db.execute(
            select(
                ActivityFeed.channel_id,
                func.count(ActivityFeed.id).label("event_count"),
            )
            .where(
                ActivityFeed.channel_id.in_(channel_ids),
                ActivityFeed.event_type == "sale_start",
                ActivityFeed.detected_at >= cutoff,
            )
            .group_by(ActivityFeed.channel_id)
        )
    ).all()
    return {int(channel_id): int(event_count or 0) for channel_id, event_count in rows}


def _render_target_channels(channels: list[Channel], sale_counts: dict[int, int] | None = None) -> None:
    table = Table(title="대상 채널", show_lines=True)
    table.add_column("ID", justify="right", style="dim")
    table.add_column("채널", style="cyan")
    table.add_column("타입", style="white")
    table.add_column("플랫폼", style="magenta")
    table.add_column("국가", style="dim")
    table.add_column("P", justify="right", style="yellow")
    table.add_column("최근 세일", justify="right", style="green")
    for channel in channels:
        table.add_row(
            str(channel.id),
            channel.name,
            channel.channel_type or "-",
            channel.platform or "-",
            channel.country or "-",
            str(channel.poll_priority),
            str((sale_counts or {}).get(channel.id, 0)),
        )
    console.print(table)


def _build_alert_job(
    *,
    channel: Channel,
    info,
    brand_slug: str | None,
    prev_price_krw: int | None,
    current_krw: int,
    threshold: float,
    is_new: bool,
    sale_just_started: bool,
) -> PendingAlertJob | None:
    is_sale = (
        info.compare_at_price is not None
        and info.compare_at_price > info.price
    )
    discount_rate = None
    if is_sale and info.compare_at_price:
        discount_rate = round((1 - info.price / info.compare_at_price) * 100)
    original_krw = (
        int(info.compare_at_price * (current_krw / info.price))
        if info.compare_at_price and info.price
        else None
    )
    payload = AlertPayload(
        product_name=info.title,
        product_key=info.product_key,
        channel_name=channel.name,
        product_url=info.product_url,
        image_url=info.image_url,
        price_krw=current_krw,
        original_price_krw=original_krw,
        discount_rate=discount_rate,
        prev_price_krw=prev_price_krw,
    )
    if is_new:
        return PendingAlertJob(
            alert_kind="new_product",
            brand_slug=brand_slug,
            product_key=info.product_key,
            payload=payload,
        )
    if sale_just_started:
        return PendingAlertJob(
            alert_kind="sale_start",
            brand_slug=brand_slug,
            product_key=info.product_key,
            payload=payload,
        )
    if (
        prev_price_krw
        and prev_price_krw > 0
        and current_krw < prev_price_krw * (1 - threshold)
    ):
        return PendingAlertJob(
            alert_kind="price_drop",
            brand_slug=brand_slug,
            product_key=info.product_key,
            payload=payload,
        )
    return None


def _build_derived_event(
    *,
    event_type: str,
    product_id: int,
    brand_id: int | None,
    channel: Channel,
    info,
    details: dict,
) -> PendingDerivedEvent:
    if event_type == "sale_start":
        title = f"{info.title} 세일 시작"
        summary = f"{channel.name}에서 세일 전환 감지"
    elif event_type == "sold_out":
        title = f"{info.title} 품절 전환"
        summary = f"{channel.name} sold_out 감지"
    else:
        title = f"{info.title} 재입고"
        summary = f"{channel.name} restock 감지"
    return PendingDerivedEvent(
        event_type=event_type,
        product_id=product_id,
        brand_id=brand_id,
        title=title,
        summary=summary,
        source_url=info.product_url,
        details=details,
    )


async def _save_channel_products_sqlite(
    db,
    *,
    channel: Channel,
    products: list,
    rate: float,
    threshold: float,
    alerts_enabled: bool,
    no_intel: bool,
) -> ChannelSaveOutcome:
    outcome = ChannelSaveOutcome(products_count=len(products))
    vendor_names = sorted({info.vendor for info in products if info.vendor})
    brand_by_vendor = await find_brands_by_vendors(db, vendor_names)
    existing_by_url = await get_existing_products_by_urls(
        db,
        [info.product_url for info in products],
    )
    prev_price_by_product_id = (
        await get_prev_prices_by_product_ids(
            db,
            [row.id for row in existing_by_url.values()],
        )
        if alerts_enabled
        else {}
    )

    for info in products:
        brand = brand_by_vendor.get(info.vendor or "")
        brand_id = brand.id if brand else None
        brand_slug = brand.slug if brand else None
        existing_row = existing_by_url.get(info.product_url)
        prev_price_krw = (
            prev_price_by_product_id.get(existing_row.id)
            if existing_row
            else None
        )

        product, is_new, sale_just_started, availability_transition = await upsert_product(
            db,
            channel.id,
            info,
            rate,
            brand_id=brand_id,
            existing=existing_row,
        )
        price_row = build_price_history_row(product.id, info, rate)
        if price_row is not None:
            db.add(PriceHistory(**price_row))
            current_krw = int(price_row["price"])
        else:
            current_krw = round(float(info.price) * rate)

        is_sale = (
            info.compare_at_price is not None
            and info.compare_at_price > info.price
        )
        if is_sale:
            outcome.sale_count += 1
        if is_new:
            outcome.new_count += 1
        else:
            outcome.updated_count += 1

        if sale_just_started and not no_intel:
            discount_rate = None
            if (
                info.compare_at_price
                and info.price
                and info.compare_at_price > 0
                and info.compare_at_price > info.price
            ):
                discount_rate = round(1 - (info.price / info.compare_at_price), 4)
            outcome.post_commit_work.derived_events.append(
                _build_derived_event(
                    event_type="sale_start",
                    product_id=product.id,
                    brand_id=brand_id,
                    channel=channel,
                    info=info,
                    details={
                        "discount_rate": discount_rate,
                        "channel_name": channel.name,
                        "price": info.price,
                        "compare_at_price": info.compare_at_price,
                    },
                )
            )
        if availability_transition in {"sold_out", "restock"} and not no_intel:
            outcome.post_commit_work.derived_events.append(
                _build_derived_event(
                    event_type=availability_transition,
                    product_id=product.id,
                    brand_id=brand_id,
                    channel=channel,
                    info=info,
                    details={"channel_name": channel.name},
                )
            )

        if alerts_enabled:
            alert_job = _build_alert_job(
                channel=channel,
                info=info,
                brand_slug=brand_slug,
                prev_price_krw=prev_price_krw,
                current_krw=current_krw,
                threshold=threshold,
                is_new=is_new,
                sale_just_started=sale_just_started,
            )
            if alert_job:
                outcome.post_commit_work.alert_jobs.append(alert_job)

    return outcome


async def _save_channel_products_postgres(
    db,
    *,
    channel: Channel,
    products: list,
    rate: float,
    threshold: float,
    alerts_enabled: bool,
    no_intel: bool,
) -> ChannelSaveOutcome:
    outcome = ChannelSaveOutcome(products_count=len(products))
    vendor_names = sorted({info.vendor for info in products if info.vendor})
    brand_by_vendor = await find_brands_by_vendors(db, vendor_names)
    existing_by_url = await get_existing_products_by_urls(
        db,
        [info.product_url for info in products],
    )
    prev_price_by_product_id = (
        await get_prev_prices_by_product_ids(
            db,
            [row.id for row in existing_by_url.values()],
        )
        if alerts_enabled
        else {}
    )

    upsert_rows: list[dict] = []
    meta_by_url: dict[str, dict] = {}
    row_now = datetime.utcnow()

    for info in products:
        brand = brand_by_vendor.get(info.vendor or "")
        brand_id = brand.id if brand else None
        brand_slug = brand.slug if brand else None
        existing_row = existing_by_url.get(info.product_url)
        prev_price_krw = (
            prev_price_by_product_id.get(existing_row.id)
            if existing_row
            else None
        )
        row, is_new, sale_just_started, availability_transition = build_product_upsert_row(
            channel_id=channel.id,
            info=info,
            rate_to_krw=rate,
            brand_id=brand_id,
            existing=existing_row,
            now=row_now,
        )
        upsert_rows.append(row)
        meta_by_url[info.product_url] = {
            "info": info,
            "brand_id": brand_id,
            "brand_slug": brand_slug,
            "prev_price_krw": prev_price_krw,
            "is_new": is_new,
            "sale_just_started": sale_just_started,
            "availability_transition": availability_transition,
        }
        if (
            info.compare_at_price is not None
            and info.compare_at_price > info.price
        ):
            outcome.sale_count += 1
        if is_new:
            outcome.new_count += 1
        else:
            outcome.updated_count += 1

    product_id_by_url: dict[str, int] = {}
    for chunk in _chunk_rows(upsert_rows, _PRODUCT_BULK_CHUNK_SIZE):
        stmt = pg_insert(Product).values(chunk)
        excluded = stmt.excluded
        upsert_stmt = (
            stmt.on_conflict_do_update(
                index_elements=[Product.url],
                set_={
                    "channel_id": excluded.channel_id,
                    "brand_id": excluded.brand_id,
                    "name": excluded.name,
                    "vendor": excluded.vendor,
                    "product_key": excluded.product_key,
                    "normalized_key": excluded.normalized_key,
                    "match_confidence": excluded.match_confidence,
                    "gender": excluded.gender,
                    "subcategory": excluded.subcategory,
                    "sku": excluded.sku,
                    "tags": excluded.tags,
                    "image_url": excluded.image_url,
                    "is_active": excluded.is_active,
                    "is_sale": excluded.is_sale,
                    "archived_at": excluded.archived_at,
                    "updated_at": excluded.updated_at,
                },
            )
            .returning(Product.id, Product.url)
        )
        upserted_rows = (await db.execute(upsert_stmt)).all()
        product_id_by_url.update({row.url: row.id for row in upserted_rows})

    price_rows: list[dict] = []
    for product_url, meta in meta_by_url.items():
        info = meta["info"]
        product_id = product_id_by_url[product_url]
        price_row = build_price_history_row(product_id, info, rate, crawled_at=row_now)
        if price_row is not None:
            price_rows.append(price_row)
            current_krw = int(price_row["price"])
        else:
            current_krw = round(float(info.price) * rate)

        if meta["sale_just_started"] and not no_intel:
            discount_rate = None
            if (
                info.compare_at_price
                and info.price
                and info.compare_at_price > 0
                and info.compare_at_price > info.price
            ):
                discount_rate = round(1 - (info.price / info.compare_at_price), 4)
            outcome.post_commit_work.derived_events.append(
                _build_derived_event(
                    event_type="sale_start",
                    product_id=product_id,
                    brand_id=meta["brand_id"],
                    channel=channel,
                    info=info,
                    details={
                        "discount_rate": discount_rate,
                        "channel_name": channel.name,
                        "price": info.price,
                        "compare_at_price": info.compare_at_price,
                    },
                )
            )
        if meta["availability_transition"] in {"sold_out", "restock"} and not no_intel:
            outcome.post_commit_work.derived_events.append(
                _build_derived_event(
                    event_type=meta["availability_transition"],
                    product_id=product_id,
                    brand_id=meta["brand_id"],
                    channel=channel,
                    info=info,
                    details={"channel_name": channel.name},
                )
            )

        if alerts_enabled:
            alert_job = _build_alert_job(
                channel=channel,
                info=info,
                brand_slug=meta["brand_slug"],
                prev_price_krw=meta["prev_price_krw"],
                current_krw=current_krw,
                threshold=threshold,
                is_new=meta["is_new"],
                sale_just_started=meta["sale_just_started"],
            )
            if alert_job:
                outcome.post_commit_work.alert_jobs.append(alert_job)

    for chunk in _chunk_rows(price_rows, _PRICE_HISTORY_BULK_CHUNK_SIZE):
        await db.execute(pg_insert(PriceHistory).values(chunk))

    return outcome


async def run_channel_post_commit_pipeline(
    *,
    channel: Channel,
    work: ChannelPostCommitWork,
) -> None:
    if work.derived_events:
        try:
            async with AsyncSessionLocal() as db:
                await _apply_crawl_db_timeouts(db)
                product_rows = (
                    await db.execute(
                        select(Product).where(
                            Product.id.in_([item.product_id for item in work.derived_events])
                        )
                    )
                ).scalars().all()
                brand_ids = sorted({item.brand_id for item in work.derived_events if item.brand_id})
                brand_rows = (
                    await db.execute(select(Brand).where(Brand.id.in_(brand_ids)))
                ).scalars().all() if brand_ids else []
                product_by_id = {row.id: row for row in product_rows}
                brand_by_id = {row.id: row for row in brand_rows}

                for item in work.derived_events:
                    product = product_by_id.get(item.product_id)
                    if not product:
                        continue
                    brand = brand_by_id.get(item.brand_id) if item.brand_id else None
                    await upsert_derived_product_event(
                        db,
                        event_type=item.event_type,
                        product=product,
                        channel=channel,
                        brand=brand,
                        title=item.title,
                        summary=item.summary,
                        source_url=item.source_url,
                        details=item.details,
                    )
                await db.commit()
        except Exception as exc:
            logger.warning("channel post-commit intel failed channel=%s: %s", channel.name, exc)

    if work.alert_jobs and settings.discord_webhook_url:
        try:
            allowed_jobs: list[PendingAlertJob] = []
            async with AsyncSessionLocal() as db:
                await _apply_crawl_db_timeouts(db)
                for job in work.alert_jobs:
                    if await should_alert(
                        db,
                        brand_slug=job.brand_slug,
                        channel_url=channel.url,
                        product_key=job.product_key,
                    ):
                        allowed_jobs.append(job)

            for job in allowed_jobs:
                if job.alert_kind == "new_product":
                    await new_product_alert(job.payload)
                elif job.alert_kind == "sale_start":
                    await sale_alert(job.payload)
                elif job.alert_kind == "price_drop":
                    await price_drop_alert(job.payload)
        except Exception as exc:
            logger.warning("channel post-commit alerts failed channel=%s: %s", channel.name, exc)


async def run_channel_watch_pipeline(
    *,
    channel: Channel,
    run_id: int,
) -> None:
    try:
        inserted = await run_channel_watch(channel.id, run_id)
        if inserted:
            console.print(f"[dim][WATCH][/dim] {channel.name} activity_feed +{inserted}")
    except Exception as exc:
        logger.warning("channel watch failed channel=%s: %s", channel.name, exc)


async def run_post_commit_pipeline(
    *,
    run_started_at: datetime,
    skip_catalog: bool,
    no_intel: bool,
    total_upserted: int,
) -> None:
    if not skip_catalog:
        try:
            console.print("[cyan]▶ ProductCatalog 증분 빌드 시작[/cyan]")
            updated = await build_catalog_incremental(since=run_started_at)
            console.print(f"[green]✅ ProductCatalog 증분 빌드 완료[/green] (updated={updated})")
        except Exception as exc:
            console.print(f"[yellow]catalog 증분 빌드 실패(무시): {exc}[/yellow]")

    if not no_intel and total_upserted > 0:
        try:
            console.print("[cyan][INTEL][/cyan] derived_spike 자동 실행")
            import ingest_intel_events

            code_spike = await ingest_intel_events.run(job="derived_spike", window_hours=48)
            console.print(f"[cyan][INTEL][/cyan] derived_spike 완료 code={code_spike}")
        except Exception as exc:
            console.print(f"[yellow][INTEL] derived_spike 자동 실행 실패(무시): {exc}[/yellow]")
        try:
            console.print("[cyan][INTEL][/cyan] mirror 자동 실행")
            import ingest_intel_events

            code_mirror = await ingest_intel_events.run(job="mirror")
            console.print(f"[cyan][INTEL][/cyan] mirror 완료 code={code_mirror}")
        except Exception as exc:
            console.print(f"[yellow][INTEL] mirror 자동 실행 실패(무시): {exc}[/yellow]")
    elif no_intel:
        console.print("[dim][INTEL] --no-intel 설정으로 자동 실행 스킵[/dim]")
    else:
        console.print("[dim][INTEL] 변경 데이터 없음(total_upserted=0)으로 자동 실행 스킵[/dim]")


async def _crawl_one_channel(
    channel: Channel,
    run_id: int,
    no_alerts: bool,
    no_intel: bool,
    new_only: bool,
    threshold: float,
    sem: asyncio.Semaphore,
    run_lock: asyncio.Lock,
) -> dict:
    """단일 채널 크롤 — 독립적인 ProductCrawler + DB 세션 사용."""
    async with sem:
        console.print(f"[dim]▶ 시작:[/dim] {channel.name}")
        t_start = time.time()

        cafe24_categories: list[tuple[str, str]] = []
        if channel.channel_type == "edit-shop":
            async with AsyncSessionLocal() as db:
                await _apply_crawl_db_timeouts(db)
                rows = (
                    await db.execute(
                        select(Brand.name, ChannelBrand.cate_no)
                        .join(Brand, Brand.id == ChannelBrand.brand_id)
                        .where(
                            ChannelBrand.channel_id == channel.id,
                            ChannelBrand.cate_no.is_not(None),
                        )
                        .order_by(Brand.name.asc())
                    )
                ).all()
                cafe24_categories = [
                    (str(r.name), str(r.cate_no))
                    for r in rows
                    if r.name and r.cate_no
                ]

        chan_timeout = _CHANNEL_TIMEOUT_SECS.get(
            channel.platform or "default",
            _CHANNEL_TIMEOUT_SECS["default"],
        )
        async with ProductCrawler(request_delay=0.5) as crawler:
            try:
                result = await asyncio.wait_for(
                    crawler.crawl_channel(
                        channel.url,
                        country=channel.country,
                        cafe24_brand_categories=cafe24_categories,
                        new_only=new_only,
                        channel_platform=channel.platform,
                        use_gpt_parser=channel.use_gpt_parser,
                    ),
                    timeout=chan_timeout,
                )
            except asyncio.TimeoutError:
                console.print(f"[red]⏱ timeout:[/red] {channel.name} ({chan_timeout}s 초과)")
                result = ChannelProductResult(
                    channel_url=channel.url,
                    products=[],
                    error=f"Channel timeout after {chan_timeout}s",
                    error_type="timeout",
                )

        duration_ms = int((time.time() - t_start) * 1000)
        save_outcome = ChannelSaveOutcome()

        if result.products and not result.error:
            result.products = _dedupe_product_infos(result.products)
            try:
                async with AsyncSessionLocal() as db:
                    await _apply_crawl_db_timeouts(db)
                    if result.crawl_strategy == "shopify-api":
                        await update_platform(db, channel.id, "shopify")
                    elif result.crawl_strategy == "cafe24-html":
                        await update_platform(db, channel.id, "cafe24")
                    elif result.crawl_strategy == "woocommerce-api":
                        await update_platform(db, channel.id, "woocommerce")

                    currency = result.products[0].currency if result.products else "KRW"
                    rate = await get_rate_to_krw(db, currency)
                    if rate is None:
                        console.print(
                            f"[yellow]환율 없음[/yellow] {currency} → 채널 {channel.name} 가격 저장 스킵"
                        )
                        await db.commit()
                        result.error = f"Missing FX rate for {currency}"
                        result.error_type = "parse_error"
                        result.products = []
                    else:
                        alerts_enabled = (not no_alerts) and bool(settings.discord_webhook_url)
                        if db.get_bind().dialect.name == "postgresql":
                            save_outcome = await _save_channel_products_postgres(
                                db,
                                channel=channel,
                                products=result.products,
                                rate=rate,
                                threshold=threshold,
                                alerts_enabled=alerts_enabled,
                                no_intel=no_intel,
                            )
                        else:
                            save_outcome = await _save_channel_products_sqlite(
                                db,
                                channel=channel,
                                products=result.products,
                                rate=rate,
                                threshold=threshold,
                                alerts_enabled=alerts_enabled,
                                no_intel=no_intel,
                            )
                        await db.commit()
            except Exception as save_exc:
                db_error_type = _classify_db_error(save_exc)
                if db_error_type == "lock_timeout":
                    console.print(f"[yellow]lock timeout:[/yellow] {channel.name}")
                elif db_error_type == "statement_timeout":
                    console.print(f"[yellow]statement timeout:[/yellow] {channel.name}")
                result.error = f"save_error: {str(save_exc)[:180]}"
                result.error_type = db_error_type or "internal_error"
                result.products = []
                save_outcome = ChannelSaveOutcome()

        log_status = "success" if not result.error else "failed"
        if not result.products and not result.error:
            log_status = "skipped"

        try:
            async with run_lock:
                async with AsyncSessionLocal() as db:
                    await _apply_crawl_db_timeouts(db)
                    db.add(
                        CrawlChannelLog(
                            run_id=run_id,
                            channel_id=channel.id,
                            status=log_status,
                            products_found=save_outcome.products_count if not result.error else 0,
                            products_new=save_outcome.new_count,
                            products_updated=save_outcome.updated_count,
                            error_msg=(result.error or "")[:500] if result.error else None,
                            error_type=(
                                result.error_type
                                if result.error
                                else ("zero_products" if log_status == "skipped" else None)
                            ),
                            strategy=result.crawl_strategy,
                            duration_ms=duration_ms,
                        )
                    )
                    await db.execute(
                        text(
                            "UPDATE crawl_runs SET"
                            "  done_channels    = done_channels + 1,"
                            "  new_products     = new_products + :new_p,"
                            "  updated_products = updated_products + :upd_p,"
                            "  error_channels   = error_channels + :err"
                            " WHERE id = :run_id"
                        ),
                        {
                            "new_p": save_outcome.new_count,
                            "upd_p": save_outcome.updated_count,
                            "err": 1 if result.error else 0,
                            "run_id": run_id,
                        },
                    )
                    await db.commit()
        except Exception as log_exc:
            console.print(f"[red]CrawlChannelLog 기록 실패[/red] {channel.name}: {log_exc}")
            try:
                async with AsyncSessionLocal() as db2:
                    db2.add(
                        CrawlChannelLog(
                            run_id=run_id,
                            channel_id=channel.id,
                            status="failed",
                            products_found=0,
                            products_new=0,
                            products_updated=0,
                            error_msg=f"Internal log error: {str(log_exc)[:200]}",
                            error_type="internal_error",
                            strategy=result.crawl_strategy,
                            duration_ms=duration_ms,
                        )
                    )
                    await db2.execute(
                        text(
                            "UPDATE crawl_runs SET done_channels = done_channels + 1,"
                            " error_channels = error_channels + 1 WHERE id = :run_id"
                        ),
                        {"run_id": run_id},
                    )
                    await db2.commit()
            except Exception as log_retry_exc:
                console.print(
                    f"[bold red]CrawlChannelLog 재시도도 실패[/bold red] {channel.name}: {log_retry_exc}"
                )

        status_icon = "✅" if not result.error else "❌"
        products_count = save_outcome.products_count if not result.error else 0
        console.print(
            f"[dim]{status_icon} 완료:[/dim] {channel.name}"
            f" — {products_count}개 (신규 {save_outcome.new_count}, 세일 {save_outcome.sale_count})"
            + (f" [red]{result.error[:60]}[/red]" if result.error else "")
        )

        return {
            "channel_name": channel.name,
            "country": channel.country or "-",
            "products_count": products_count,
            "sale_count": save_outcome.sale_count,
            "new_count": save_outcome.new_count,
            "error": result.error,
            "post_commit_work": save_outcome.post_commit_work,
        }
@app.command()
def main(
    limit: int = typer.Option(0, help="크롤링할 채널 수 (0=전체)"),
    channel_type: str = typer.Option(
        "", help="채널 타입 필터 (edit-shop / brand-store / 빈 문자열=전체)"
    ),
    country: str = typer.Option("", help="국가 코드 필터 (예: JP, KR, US)"),
    channel_id: int = typer.Option(0, help="특정 채널 ID만 크롤링 (0=비활성)"),
    channel_name: str = typer.Option("", help="특정 채널명만 크롤링 (부분 일치)"),
    fast_poll: bool = typer.Option(False, "--fast-poll", help="poll_priority=1 채널만 빠르게 순회"),
    new_only: bool = typer.Option(False, "--new-only", help="Shopify /products/new.json 1회 조회만 수행"),
    dry_run: bool = typer.Option(False, "--dry-run", help="대상 채널만 출력하고 종료"),
    no_alerts: bool = typer.Option(False, "--no-alerts", help="Discord 알림 비활성화"),
    skip_catalog: bool = typer.Option(False, "--skip-catalog", help="크롤 완료 후 catalog 증분 빌드 생략"),
    no_intel: bool = typer.Option(False, "--no-intel", help="크롤 완료 후 intel ingest 자동 실행 비활성화"),
    no_watch: bool = typer.Option(False, "--no-watch", help="크롤 완료 후 activity_feed 감지 비활성화"),
    concurrency: int = typer.Option(
        2, help="동시 처리 채널 수 (기본 2, Shopify rate-limit 방지)"
    ),
):
    asyncio.run(
        run(
            limit,
            channel_type or None,
            country.strip().upper() or None,
            channel_id if channel_id > 0 else None,
            channel_name.strip() or None,
            fast_poll,
            new_only,
            dry_run,
            no_alerts,
            skip_catalog,
            no_intel,
            no_watch,
            concurrency,
        )
    )


async def run(
    limit: int,
    channel_type: str | None,
    country: str | None,
    channel_id: int | None,
    channel_name: str | None,
    fast_poll: bool,
    new_only: bool,
    dry_run: bool,
    no_alerts: bool,
    skip_catalog: bool,
    no_intel: bool,
    no_watch: bool,
    concurrency: int = 5,
) -> None:
    console.print("[bold blue]Fashion Data Engine — 제품 가격 크롤링[/bold blue]\n")
    if fast_poll:
        console.print("[cyan]fast poll 모드: poll_priority=1 채널 우선[/cyan]")
    if new_only:
        console.print("[cyan]new-only 모드: Shopify /products/new.json 1회 조회[/cyan]")
    if settings.discord_webhook_url and not no_alerts:
        console.print("[green]Discord 알림 활성화[/green]")
    elif not no_alerts:
        console.print("[yellow]DISCORD_WEBHOOK_URL 미설정 — 알림 비활성화[/yellow]")

    console.print(f"[cyan]동시 처리 채널 수: {concurrency}[/cyan]")

    await init_db()

    sale_counts: dict[int, int] = {}
    async with AsyncSessionLocal() as db:
        query = select(Channel).where(Channel.is_active == True)  # noqa: E712
        if channel_id:
            query = query.filter(Channel.id == channel_id)
        if channel_name:
            query = query.filter(Channel.name.ilike(f"%{channel_name}%"))
        if channel_type:
            query = query.filter(Channel.channel_type == channel_type)
        if country:
            query = query.filter(Channel.country == country)
        if fast_poll:
            query = query.filter(Channel.poll_priority == 1)
        if new_only:
            query = query.filter(Channel.platform == "shopify")
        channels = list((await db.execute(query)).scalars().all())
        if fast_poll:
            sale_counts = await _load_fast_poll_sale_counts(db, [c.id for c in channels])

    channels = [c for c in channels if c.channel_type not in SKIP_TYPES]

    if fast_poll:
        channels.sort(
            key=lambda c: (
                -sale_counts.get(c.id, 0),
                c.poll_priority,
                _CHANNEL_PRIORITY.get(c.channel_type, 2),
                c.name.lower(),
            )
        )
        if not limit:
            limit = 50
    else:
        # brand-store 먼저, 그 다음 edit-shop 순으로 우선순위 정렬
        channels.sort(key=lambda c: (_CHANNEL_PRIORITY.get(c.channel_type, 2), c.name.lower()))

    if limit:
        channels = channels[:limit]

    if dry_run:
        console.print(f"[bold]dry-run[/bold] 대상 채널 {len(channels)}개")
        _render_target_channels(channels, sale_counts if fast_poll else None)
        return

    console.print(f"대상 채널: {len(channels)}개\n")

    # CrawlRun 생성
    async with AsyncSessionLocal() as db:
        await _apply_crawl_db_timeouts(db)
        crawl_run = CrawlRun(total_channels=len(channels), status="running")
        db.add(crawl_run)
        await db.commit()
        await db.refresh(crawl_run)
        run_id = crawl_run.id
        run_started_at = crawl_run.started_at

    console.print(f"[bold]CrawlRun #{run_id} 시작[/bold]\n")

    threshold = settings.alert_price_drop_threshold  # 기본 0.10

    # ── 병렬 크롤링 ──────────────────────────────────────────────────────────
    sem = asyncio.Semaphore(concurrency)
    run_lock = asyncio.Lock()

    tasks = [
        _crawl_one_channel(ch, run_id, no_alerts, no_intel, new_only, threshold, sem, run_lock)
        for ch in channels
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    # ── 결과 테이블 출력 ─────────────────────────────────────────────────────
    results_table = Table(title=f"크롤링 결과 (Run #{run_id})", show_lines=True)
    results_table.add_column("채널", style="cyan")
    results_table.add_column("국가", style="dim")
    results_table.add_column("제품 수", justify="right", style="green")
    results_table.add_column("세일", justify="right", style="yellow")
    results_table.add_column("신제품", justify="right", style="blue")
    results_table.add_column("오류", style="red")

    for ch, raw in zip(channels, raw_results):
        if isinstance(raw, Exception):
            results_table.add_row(
                ch.name, ch.country or "-", "-", "-", "-", str(raw)[:80]
            )
        else:
            r: dict = raw
            results_table.add_row(
                r["channel_name"],
                r["country"],
                str(r["products_count"]),
                str(r["sale_count"]) if r["products_count"] else "-",
                str(r["new_count"]) if r["products_count"] else "-",
                r["error"] or "",
            )

    for ch, raw in zip(channels, raw_results):
        if isinstance(raw, Exception):
            continue
        work = raw.get("post_commit_work")
        if work and (work.derived_events or work.alert_jobs):
            await run_channel_post_commit_pipeline(channel=ch, work=work)
        if not no_watch and not raw.get("error"):
            await run_channel_watch_pipeline(channel=ch, run_id=run_id)

    # CrawlRun 완료 처리
    total_upserted = 0
    async with AsyncSessionLocal() as db:
        await _apply_crawl_db_timeouts(db)
        run_obj = await db.get(CrawlRun, run_id)
        if run_obj:
            run_obj.status = "done"
            run_obj.finished_at = datetime.utcnow()
            total_upserted = int(run_obj.new_products or 0) + int(run_obj.updated_products or 0)
            await db.commit()

    console.print(results_table)
    console.print(f"\n[bold green]CrawlRun #{run_id} 완료[/bold green]")
    await run_post_commit_pipeline(
        run_started_at=run_started_at,
        skip_catalog=skip_catalog,
        no_intel=no_intel,
        total_upserted=total_upserted,
    )


if __name__ == "__main__":
    app()
