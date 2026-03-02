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
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import select, text

from fashion_engine.config import settings
from fashion_engine.database import init_db, AsyncSessionLocal
from fashion_engine.models.channel import Channel
from fashion_engine.models.channel_brand import ChannelBrand
from fashion_engine.models.brand import Brand
from fashion_engine.models.price_history import PriceHistory
from fashion_engine.models.product import Product
from fashion_engine.models.crawl_run import CrawlRun, CrawlChannelLog
from fashion_engine.crawler.product_crawler import ProductCrawler, ChannelProductResult
from fashion_engine.services.product_service import (
    get_rate_to_krw,
    find_brand_by_vendor,
    upsert_product,
    record_price,
)
from fashion_engine.services.channel_service import update_platform
from fashion_engine.services.catalog_service import build_catalog_incremental
from fashion_engine.services.alert_service import (
    AlertPayload,
    new_product_alert,
    sale_alert,
    price_drop_alert,
)
from fashion_engine.services.watchlist_service import should_alert

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


async def _get_prev_price_krw(db, product_id: int) -> int | None:
    """직전 크롤의 KRW 가격 조회."""
    result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id)
        .where(PriceHistory.currency == "KRW")
        .order_by(PriceHistory.crawled_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return int(row.price) if row else None


async def _crawl_one_channel(
    channel: Channel,
    run_id: int,
    no_alerts: bool,
    threshold: float,
    sem: asyncio.Semaphore,
    run_lock: asyncio.Lock,
) -> dict:
    """단일 채널 크롤 — 독립적인 ProductCrawler + DB 세션 사용."""
    async with sem:
        console.print(f"[dim]▶ 시작:[/dim] {channel.name}")
        t_start = time.time()

        # ── 1. Cafe24 카테고리 로드 (편집샵만) ───────────────────────────
        cafe24_categories: list[tuple[str, str]] = []
        if channel.channel_type == "edit-shop":
            async with AsyncSessionLocal() as db:
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

        # ── 2. 크롤 (채널별 독립 크롤러 인스턴스) ───────────────────────
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
                    ),
                    timeout=chan_timeout,
                )
            except asyncio.TimeoutError:
                console.print(
                    f"[red]⏱ timeout:[/red] {channel.name} ({chan_timeout}s 초과)"
                )
                result = ChannelProductResult(
                    channel_url=channel.url,
                    products=[],
                    error=f"Channel timeout after {chan_timeout}s",
                    error_type="timeout",
                )

        duration_ms = int((time.time() - t_start) * 1000)
        sale_count = 0
        new_count = 0
        updated_count = 0

        # ── 3. DB 저장 ───────────────────────────────────────────────────
        if result.products and not result.error:
            try:
                async with AsyncSessionLocal() as db:
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
                        new_count = 0
                        updated_count = 0
                        sale_count = 0
                    else:
                        for info in result.products:
                            brand = await find_brand_by_vendor(db, info.vendor)
                            brand_id = brand.id if brand else None

                            existing_row = (
                                await db.execute(
                                    select(Product).where(Product.url == info.product_url)
                                )
                            ).scalar_one_or_none()
                            prev_price_krw = None
                            if existing_row:
                                prev_price_krw = await _get_prev_price_krw(db, existing_row.id)

                            product, is_new, sale_just_started = await upsert_product(
                                db, channel.id, info, brand_id=brand_id
                            )
                            await record_price(db, product.id, info, rate_to_krw=rate)

                            is_sale = (
                                info.compare_at_price is not None
                                and info.compare_at_price > info.price
                            )
                            if is_sale:
                                sale_count += 1
                            if is_new:
                                new_count += 1
                            else:
                                updated_count += 1

                            # ── 알림 트리거 ───────────────────────────────────────
                            brand_slug = brand.slug if brand else None
                            if not no_alerts and settings.discord_webhook_url and await should_alert(
                                db,
                                brand_slug=brand_slug,
                                channel_url=channel.url,
                                product_key=info.product_key,
                            ):
                                current_krw = int(info.price * rate)
                                discount_rate: int | None = None
                                if is_sale and info.compare_at_price:
                                    discount_rate = round(
                                        (1 - info.price / info.compare_at_price) * 100
                                    )
                                original_krw = (
                                    int(info.compare_at_price * rate)
                                    if info.compare_at_price
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
                                    await new_product_alert(payload)
                                elif sale_just_started:
                                    await sale_alert(payload)
                                elif (
                                    prev_price_krw
                                    and prev_price_krw > 0
                                    and current_krw < prev_price_krw * (1 - threshold)
                                ):
                                    await price_drop_alert(payload)

                    await db.commit()
            except Exception as save_exc:
                result.error = f"save_error: {str(save_exc)[:180]}"
                result.error_type = "internal_error"
                result.products = []

        # ── 4. CrawlChannelLog + CrawlRun 업데이트 (Lock으로 동시성 보호) ──
        log_status = "success" if not result.error else "failed"
        if not result.products and not result.error:
            log_status = "skipped"

        try:
            async with run_lock:
                async with AsyncSessionLocal() as db:
                    db.add(
                        CrawlChannelLog(
                            run_id=run_id,
                            channel_id=channel.id,
                            status=log_status,
                            products_found=len(result.products),
                            products_new=new_count,
                            products_updated=updated_count,
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
                    # 원자적 카운터 업데이트 (READ-MODIFY-WRITE 경쟁 방지)
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
                            "new_p": new_count,
                            "upd_p": updated_count,
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
        console.print(
            f"[dim]{status_icon} 완료:[/dim] {channel.name}"
            f" — {len(result.products)}개 (신규 {new_count}, 세일 {sale_count})"
            + (f" [red]{result.error[:60]}[/red]" if result.error else "")
        )

        return {
            "channel_name": channel.name,
            "country": channel.country or "-",
            "products_count": len(result.products),
            "sale_count": sale_count,
            "new_count": new_count,
            "error": result.error,
        }


@app.command()
def main(
    limit: int = typer.Option(0, help="크롤링할 채널 수 (0=전체)"),
    channel_type: str = typer.Option(
        "", help="채널 타입 필터 (edit-shop / brand-store / 빈 문자열=전체)"
    ),
    channel_id: int = typer.Option(0, help="특정 채널 ID만 크롤링 (0=비활성)"),
    channel_name: str = typer.Option("", help="특정 채널명만 크롤링 (부분 일치)"),
    no_alerts: bool = typer.Option(False, "--no-alerts", help="Discord 알림 비활성화"),
    skip_catalog: bool = typer.Option(False, "--skip-catalog", help="크롤 완료 후 catalog 증분 빌드 생략"),
    concurrency: int = typer.Option(
        2, help="동시 처리 채널 수 (기본 2, Shopify rate-limit 방지)"
    ),
):
    asyncio.run(
        run(
            limit,
            channel_type or None,
            channel_id if channel_id > 0 else None,
            channel_name.strip() or None,
            no_alerts,
            skip_catalog,
            concurrency,
        )
    )


async def run(
    limit: int,
    channel_type: str | None,
    channel_id: int | None,
    channel_name: str | None,
    no_alerts: bool,
    skip_catalog: bool,
    concurrency: int = 5,
) -> None:
    console.print("[bold blue]Fashion Data Engine — 제품 가격 크롤링[/bold blue]\n")
    if settings.discord_webhook_url and not no_alerts:
        console.print("[green]Discord 알림 활성화[/green]")
    elif not no_alerts:
        console.print("[yellow]DISCORD_WEBHOOK_URL 미설정 — 알림 비활성화[/yellow]")

    console.print(f"[cyan]동시 처리 채널 수: {concurrency}[/cyan]")

    await init_db()

    async with AsyncSessionLocal() as db:
        query = select(Channel).where(Channel.is_active == True)  # noqa: E712
        if channel_id:
            query = query.filter(Channel.id == channel_id)
        if channel_name:
            query = query.filter(Channel.name.ilike(f"%{channel_name}%"))
        if channel_type:
            query = query.filter(Channel.channel_type == channel_type)
        channels = list((await db.execute(query)).scalars().all())

    channels = [c for c in channels if c.channel_type not in SKIP_TYPES]

    # brand-store 먼저, 그 다음 edit-shop 순으로 우선순위 정렬
    channels.sort(key=lambda c: _CHANNEL_PRIORITY.get(c.channel_type, 2))

    if limit:
        channels = channels[:limit]

    console.print(f"대상 채널: {len(channels)}개\n")

    # CrawlRun 생성
    async with AsyncSessionLocal() as db:
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
        _crawl_one_channel(ch, run_id, no_alerts, threshold, sem, run_lock)
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

    # CrawlRun 완료 처리
    async with AsyncSessionLocal() as db:
        run_obj = await db.get(CrawlRun, run_id)
        if run_obj:
            run_obj.status = "done"
            run_obj.finished_at = datetime.utcnow()
            await db.commit()

    console.print(results_table)
    console.print(f"\n[bold green]CrawlRun #{run_id} 완료[/bold green]")

    if not skip_catalog:
        console.print("[cyan]▶ ProductCatalog 증분 빌드 시작[/cyan]")
        updated = await build_catalog_incremental(since=run_started_at)
        console.print(f"[green]✅ ProductCatalog 증분 빌드 완료[/green] (updated={updated})")


if __name__ == "__main__":
    app()
