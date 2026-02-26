"""
채널별 제품·가격 크롤링 및 DB 저장 스크립트.

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

from fashion_engine.database import init_db, AsyncSessionLocal
from fashion_engine.models.channel import Channel
from fashion_engine.crawler.product_crawler import ProductCrawler
from fashion_engine.services.product_service import (
    get_rate_to_krw,
    find_brand_by_vendor,
    upsert_product,
    record_price,
)

console = Console()
app = typer.Typer()

# brand-store 등도 포함 (공식몰 가격이 비교 기준점이 됨)
SKIP_TYPES = {"secondhand-marketplace", "non-fashion"}


@app.command()
def main(
    limit: int = typer.Option(0, help="크롤링할 채널 수 (0=전체)"),
    channel_type: str = typer.Option("", help="채널 타입 필터 (edit-shop / brand-store / 빈 문자열=전체)"),
):
    asyncio.run(run(limit, channel_type or None))


async def run(limit: int, channel_type: str | None) -> None:
    console.print("[bold blue]Fashion Data Engine — 제품 가격 크롤링[/bold blue]\n")
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
    results_table.add_column("전략", style="blue")
    results_table.add_column("오류", style="red")

    async with ProductCrawler(request_delay=0.5) as crawler:
        for channel in channels:
            console.print(f"[dim]크롤링:[/dim] {channel.url}")
            result = await crawler.crawl_channel(channel.url, country=channel.country)

            sale_count = 0

            if result.products and not result.error:
                async with AsyncSessionLocal() as db:
                    # 환율 조회 (채널 국가 → 통화 → KRW)
                    currency = result.products[0].currency if result.products else "KRW"
                    rate = await get_rate_to_krw(db, currency)

                    for info in result.products:
                        # 브랜드 매핑
                        brand = await find_brand_by_vendor(db, info.vendor)
                        brand_id = brand.id if brand else None

                        # 제품 upsert
                        product = await upsert_product(db, channel.id, info, brand_id=brand_id)

                        # 가격 이력 기록
                        await record_price(db, product.id, info, rate_to_krw=rate)

                        if info.compare_at_price and info.compare_at_price > info.price:
                            sale_count += 1

                    await db.commit()

            results_table.add_row(
                channel.name,
                channel.country or "-",
                str(len(result.products)),
                str(sale_count) if result.products else "-",
                result.crawl_strategy,
                result.error or "",
            )

    console.print(results_table)


if __name__ == "__main__":
    app()
