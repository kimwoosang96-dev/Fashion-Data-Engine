"""
채널별 브랜드 크롤링 및 DB 저장 스크립트

사용법:
    uv run python scripts/crawl_brands.py             # 전체 채널
    uv run python scripts/crawl_brands.py --limit 5   # 처음 5개만 (테스트용)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import typer
from rich.console import Console
from rich.table import Table

from fashion_engine.database import init_db, AsyncSessionLocal
from fashion_engine.services.channel_service import get_all_channels
from fashion_engine.services.brand_service import upsert_brand, link_brand_to_channel
from fashion_engine.crawler.brand_crawler import BrandCrawler

console = Console()
app = typer.Typer()


@app.command()
def main(limit: int = typer.Option(0, help="크롤링할 채널 수 (0=전체)")):
    asyncio.run(run(limit))


async def run(limit: int):
    console.print("[bold blue]Fashion Data Engine — 브랜드 크롤링[/bold blue]\n")
    await init_db()

    async with AsyncSessionLocal() as db:
        channels = await get_all_channels(db)

    # brand-store / department-store / secondhand-marketplace / non-fashion 은 크롤 불필요
    SKIP_TYPES = {"brand-store", "department-store", "secondhand-marketplace", "non-fashion"}
    skipped = [c for c in channels if c.channel_type in SKIP_TYPES]
    channels = [c for c in channels if c.channel_type not in SKIP_TYPES]

    if skipped:
        console.print(f"[dim]스킵 ({len(skipped)}개): " + ", ".join(c.name for c in skipped[:8])
                      + ("..." if len(skipped) > 8 else "") + "[/dim]\n")

    if limit:
        channels = channels[:limit]

    console.print(f"대상 채널 (edit-shop): {len(channels)}개\n")

    results_table = Table(title="크롤링 결과", show_lines=True)
    results_table.add_column("채널", style="cyan")
    results_table.add_column("브랜드 수", justify="right", style="green")
    results_table.add_column("전략", style="yellow")
    results_table.add_column("오류", style="red")

    async with BrandCrawler() as crawler:
        for channel in channels:
            console.print(f"[dim]크롤링:[/dim] {channel.url}")
            result = await crawler.crawl_channel(channel.url)

            # DB 저장
            async with AsyncSessionLocal() as db:
                for brand_info in result.brands:
                    brand = await upsert_brand(db, brand_info.name)
                    await link_brand_to_channel(db, brand.id, channel.id)

            results_table.add_row(
                channel.name,
                str(len(result.brands)),
                result.crawl_strategy,
                result.error or "",
            )

    console.print(results_table)


if __name__ == "__main__":
    app()
