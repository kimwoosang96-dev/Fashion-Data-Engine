"""
채널별 브랜드 크롤링 및 DB 저장 스크립트

사용법:
    uv run python scripts/crawl_brands.py             # 전체 채널
    uv run python scripts/crawl_brands.py --limit 5   # 처음 5개만 (테스트용)
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import delete

from fashion_engine.database import init_db, AsyncSessionLocal
from fashion_engine.models.channel_brand import ChannelBrand
from fashion_engine.crawler.url_normalizer import extract_domain
from fashion_engine.services.channel_service import get_all_channels
from fashion_engine.services.brand_service import upsert_brand, link_brand_to_channel
from fashion_engine.crawler.brand_crawler import BrandCrawler

console = Console()
app = typer.Typer()


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9가-힣]+", "", value.lower()).strip()


def _extract_cate_no(url: str | None) -> str | None:
    if not url:
        return None
    m = re.search(r"cate_no=(\d+)", url)
    return m.group(1) if m else None


@app.command()
def main(
    limit: int = typer.Option(0, help="크롤링할 채널 수 (0=전체)"),
    channel_id: int = typer.Option(0, help="특정 채널 ID만 크롤링 (0=비활성)"),
):
    asyncio.run(run(limit, channel_id if channel_id > 0 else None))


async def run(limit: int, channel_id: int | None = None):
    console.print("[bold blue]Fashion Data Engine — 브랜드 크롤링[/bold blue]\n")
    await init_db()

    async with AsyncSessionLocal() as db:
        all_channels = await get_all_channels(db)

    # brand-store / department-store / secondhand-marketplace / non-fashion 은 크롤 불필요
    SKIP_TYPES = {"brand-store", "department-store", "secondhand-marketplace", "non-fashion"}
    skipped = [c for c in all_channels if c.channel_type in SKIP_TYPES]
    channels = [c for c in all_channels if c.channel_type not in SKIP_TYPES]

    if skipped:
        console.print(f"[dim]스킵 ({len(skipped)}개): " + ", ".join(c.name for c in skipped[:8])
                      + ("..." if len(skipped) > 8 else "") + "[/dim]\n")

    # 브랜드 자체 판매페이지(brand-store)가 존재하는 이름/도메인은 보존한다.
    own_brand_norms: set[str] = set()
    for c in all_channels:
        if c.channel_type != "brand-store":
            continue
        own_brand_norms.add(_normalize_name(c.name))
        own_brand_norms.add(_normalize_name(extract_domain(c.url)))

    if channel_id:
        channels = [c for c in channels if c.id == channel_id]
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
            dropped_mixed = 0
            preserved_own_brand = 0
            channel_collision_norms = {
                _normalize_name(channel.name),
                _normalize_name(extract_domain(channel.url)),
            }

            # 혼재 방지:
            # 현재 채널명/도메인과 동일한 브랜드만 후보로 보고,
            # brand-store로 존재하는 브랜드명/도메인은 보존한다.
            filtered_brands = []
            for brand_info in result.brands:
                norm_name = _normalize_name(brand_info.name)
                if norm_name in channel_collision_norms:
                    if norm_name in own_brand_norms:
                        preserved_own_brand += 1
                    else:
                        dropped_mixed += 1
                        continue
                filtered_brands.append(brand_info)
            result.brands = filtered_brands

            # DB 저장 (브랜드가 1개 이상 추출된 경우에만 기존 링크 교체)
            if result.brands and not result.error:
                async with AsyncSessionLocal() as db:
                    # 재크롤 성공 시 stale 링크 교체
                    await db.execute(
                        delete(ChannelBrand).where(ChannelBrand.channel_id == channel.id)
                    )
                    await db.commit()

                    for brand_info in result.brands:
                        brand = await upsert_brand(db, brand_info.name)
                        await link_brand_to_channel(
                            db,
                            brand.id,
                            channel.id,
                            cate_no=_extract_cate_no(brand_info.url),
                        )

            if dropped_mixed:
                console.print(
                    f"[yellow]필터링[/yellow] {channel.name}: 채널명 충돌 브랜드 {dropped_mixed}개 제거"
                )
            if preserved_own_brand:
                console.print(
                    f"[green]보존[/green] {channel.name}: 자체 판매페이지 보유 브랜드 {preserved_own_brand}개 유지"
                )

            results_table.add_row(
                channel.name,
                str(len(result.brands)),
                result.crawl_strategy,
                result.error or "",
            )

    console.print(results_table)


if __name__ == "__main__":
    app()
