"""
드롭(발매) 크롤러 스크립트.

Shopify 채널에서 신제품 및 예정 발매를 감지해 drops 테이블에 저장.
신규 드롭 발견 시 Discord 알림 전송.

사용법:
    uv run python scripts/crawl_drops.py              # 전체 brand-store 채널
    uv run python scripts/crawl_drops.py --limit 3    # 처음 3개 채널만 (테스트)
    uv run python scripts/crawl_drops.py --all-types  # edit-shop 포함 전체
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
from fashion_engine.models.brand import Brand
from fashion_engine.crawler.drop_crawler import DropCrawler
from fashion_engine.services.drop_service import upsert_drop, mark_notified
from fashion_engine.services.product_service import get_rate_to_krw
from fashion_engine.services.alert_service import (
    AlertPayload,
    new_product_alert,
)

console = Console()
app = typer.Typer()

SKIP_TYPES = {"secondhand-marketplace", "non-fashion"}


async def _get_brand_id(db, channel_id: int) -> int | None:
    """채널에 등록된 첫 번째 브랜드 id 반환 (brand-store 전용)."""
    from fashion_engine.models.channel_brand import ChannelBrand
    result = await db.execute(
        select(ChannelBrand.brand_id).where(ChannelBrand.channel_id == channel_id).limit(1)
    )
    row = result.first()
    return row[0] if row else None


@app.command()
def main(
    limit: int = typer.Option(0, help="크롤링할 채널 수 (0=전체)"),
    all_types: bool = typer.Option(False, "--all-types", help="brand-store 외 채널 포함"),
    no_alerts: bool = typer.Option(False, "--no-alerts", help="Discord 알림 비활성화"),
):
    asyncio.run(run(limit, all_types, no_alerts))


async def run(limit: int, all_types: bool, no_alerts: bool) -> None:
    console.print("[bold blue]Fashion Data Engine — 드롭 크롤링[/bold blue]\n")
    if settings.discord_webhook_url and not no_alerts:
        console.print("[green]Discord 알림 활성화[/green]")
    elif not no_alerts:
        console.print("[yellow]DISCORD_WEBHOOK_URL 미설정 — 알림 비활성화[/yellow]")

    await init_db()

    async with AsyncSessionLocal() as db:
        query = select(Channel).where(Channel.is_active == True)
        if not all_types:
            query = query.where(Channel.channel_type == "brand-store")
        channels = list((await db.execute(query)).scalars().all())

    channels = [c for c in channels if c.channel_type not in SKIP_TYPES]

    if limit:
        channels = channels[:limit]

    console.print(f"대상 채널: {len(channels)}개\n")

    results_table = Table(title="드롭 크롤링 결과", show_lines=True)
    results_table.add_column("채널", style="cyan")
    results_table.add_column("신제품", justify="right", style="green")
    results_table.add_column("예정 발매", justify="right", style="blue")
    results_table.add_column("오류", style="red")

    async with DropCrawler(request_delay=0.5) as crawler:
        for channel in channels:
            console.print(f"[dim]드롭 크롤:[/dim] {channel.url}")

            async with AsyncSessionLocal() as db:
                rate = await get_rate_to_krw(db, "USD")  # 글로벌 채널은 USD 기본
                brand_id = await _get_brand_id(db, channel.id)

            # 1) 신제품 (created-at-desc)
            new_result = await crawler.crawl_new_arrivals(
                channel.url, channel.name, rate_to_krw=rate
            )
            # 2) coming-soon 태그
            upcoming_result = await crawler.crawl_coming_soon(
                channel.url, channel.name, rate_to_krw=rate
            )

            new_count = 0
            upcoming_count = 0

            async with AsyncSessionLocal() as db:
                # 신제품 처리
                for candidate in new_result.candidates:
                    drop, is_new = await upsert_drop(
                        db,
                        product_name=candidate.product_name,
                        source_url=candidate.source_url,
                        product_key=candidate.product_key,
                        brand_id=brand_id,
                        image_url=candidate.image_url,
                        price_krw=candidate.price_krw,
                        status="released",
                    )
                    if is_new:
                        new_count += 1
                        if not no_alerts and settings.discord_webhook_url:
                            payload = AlertPayload(
                                product_name=candidate.product_name,
                                product_key=candidate.product_key,
                                channel_name=channel.name,
                                product_url=candidate.source_url,
                                image_url=candidate.image_url,
                                price_krw=candidate.price_krw or 0,
                            )
                            sent = await new_product_alert(payload)
                            if sent:
                                await mark_notified(db, drop.id)

                # upcoming 처리
                for candidate in upcoming_result.candidates:
                    drop, is_new = await upsert_drop(
                        db,
                        product_name=candidate.product_name,
                        source_url=candidate.source_url,
                        product_key=candidate.product_key,
                        brand_id=brand_id,
                        image_url=candidate.image_url,
                        price_krw=candidate.price_krw,
                        status="upcoming",
                    )
                    if is_new:
                        upcoming_count += 1

                await db.commit()

            error_msg = new_result.error or upcoming_result.error or ""
            results_table.add_row(
                channel.name,
                str(new_count),
                str(upcoming_count),
                error_msg,
            )

    console.print(results_table)


if __name__ == "__main__":
    app()
