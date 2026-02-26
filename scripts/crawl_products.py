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
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from fashion_engine.config import settings
from fashion_engine.database import init_db, AsyncSessionLocal
from fashion_engine.models.channel import Channel
from fashion_engine.models.price_history import PriceHistory
from fashion_engine.models.product import Product
from fashion_engine.crawler.product_crawler import ProductCrawler
from fashion_engine.services.product_service import (
    get_rate_to_krw,
    find_brand_by_vendor,
    upsert_product,
    record_price,
)
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


@app.command()
def main(
    limit: int = typer.Option(0, help="크롤링할 채널 수 (0=전체)"),
    channel_type: str = typer.Option("", help="채널 타입 필터 (edit-shop / brand-store / 빈 문자열=전체)"),
    no_alerts: bool = typer.Option(False, "--no-alerts", help="Discord 알림 비활성화"),
):
    asyncio.run(run(limit, channel_type or None, no_alerts))


async def run(limit: int, channel_type: str | None, no_alerts: bool) -> None:
    console.print("[bold blue]Fashion Data Engine — 제품 가격 크롤링[/bold blue]\n")
    if settings.discord_webhook_url and not no_alerts:
        console.print("[green]Discord 알림 활성화[/green]")
    elif not no_alerts:
        console.print("[yellow]DISCORD_WEBHOOK_URL 미설정 — 알림 비활성화[/yellow]")

    await init_db()

    async with AsyncSessionLocal() as db:
        query = select(Channel).where(Channel.is_active == True)
        if channel_type:
            query = query.filter(Channel.channel_type == channel_type)
        channels = list((await db.execute(query)).scalars().all())

    channels = [c for c in channels if c.channel_type not in SKIP_TYPES]

    if limit:
        channels = channels[:limit]

    console.print(f"대상 채널: {len(channels)}개\n")

    results_table = Table(title="크롤링 결과", show_lines=True)
    results_table.add_column("채널", style="cyan")
    results_table.add_column("국가", style="dim")
    results_table.add_column("제품 수", justify="right", style="green")
    results_table.add_column("세일", justify="right", style="yellow")
    results_table.add_column("신제품", justify="right", style="blue")
    results_table.add_column("오류", style="red")

    threshold = settings.alert_price_drop_threshold  # 기본 0.10

    async with ProductCrawler(request_delay=0.5) as crawler:
        for channel in channels:
            console.print(f"[dim]크롤링:[/dim] {channel.url}")
            result = await crawler.crawl_channel(channel.url, country=channel.country)

            sale_count = 0
            new_count = 0

            if result.products and not result.error:
                async with AsyncSessionLocal() as db:
                    currency = result.products[0].currency if result.products else "KRW"
                    rate = await get_rate_to_krw(db, currency)

                    for info in result.products:
                        brand = await find_brand_by_vendor(db, info.vendor)
                        brand_id = brand.id if brand else None

                        # upsert 전 이전 가격 조회 (가격 하락 감지용)
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

                        is_sale = info.compare_at_price is not None and info.compare_at_price > info.price
                        if is_sale:
                            sale_count += 1
                        if is_new:
                            new_count += 1

                        # ── 알림 트리거 (watchlist 매칭 시만) ────────────
                        brand_slug = brand.slug if brand else None
                        if not no_alerts and settings.discord_webhook_url and await should_alert(
                            db, brand_slug=brand_slug, channel_url=channel.url, product_key=info.product_key
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

            results_table.add_row(
                channel.name,
                channel.country or "-",
                str(len(result.products)),
                str(sale_count) if result.products else "-",
                str(new_count) if result.products else "-",
                result.error or "",
            )

    console.print(results_table)


if __name__ == "__main__":
    app()
