"""
Fashion Data Engine CLI

사용법:
    fashion channels          # 전체 채널 목록
    fashion brands            # 전체 브랜드 목록
    fashion brand nike        # Nike 브랜드를 취급하는 채널 조회
    fashion search 아크테릭스  # 브랜드 검색
"""
import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from fashion_engine.database import init_db, AsyncSessionLocal
from fashion_engine.services import channel_service, brand_service

app = typer.Typer(name="fashion", help="Fashion Data Engine CLI")
console = Console()


def run_async(coro):
    return asyncio.run(coro)


@app.command()
def channels():
    """전체 판매채널 목록 조회"""
    async def _():
        await init_db()
        async with AsyncSessionLocal() as db:
            items = await channel_service.get_all_channels(db)

        table = Table(title=f"판매채널 ({len(items)}개)", show_lines=True)
        table.add_column("ID", style="dim", width=5)
        table.add_column("채널명", style="cyan")
        table.add_column("홈페이지 URL", style="green")
        table.add_column("타입", style="yellow")
        table.add_column("국가")

        for ch in items:
            table.add_row(
                str(ch.id),
                ch.name,
                ch.url,
                ch.channel_type or "-",
                ch.country or "-",
            )
        console.print(table)

    run_async(_())


@app.command()
def brands():
    """전체 브랜드 목록 조회"""
    async def _():
        await init_db()
        async with AsyncSessionLocal() as db:
            items = await brand_service.get_all_brands(db)

        table = Table(title=f"브랜드 ({len(items)}개)", show_lines=True)
        table.add_column("ID", style="dim", width=5)
        table.add_column("브랜드명", style="cyan")
        table.add_column("한글명", style="yellow")
        table.add_column("Slug", style="dim")
        table.add_column("국가")

        for b in items:
            table.add_row(
                str(b.id),
                b.name,
                b.name_ko or "-",
                b.slug,
                b.origin_country or "-",
            )
        console.print(table)

    run_async(_())


@app.command()
def brand(slug: str = typer.Argument(..., help="브랜드 slug (예: nike, arc-teryx)")):
    """특정 브랜드를 취급하는 채널 목록"""
    async def _():
        await init_db()
        async with AsyncSessionLocal() as db:
            b = await brand_service.get_brand_by_slug(db, slug)
            if not b:
                console.print(f"[red]브랜드 '{slug}'를 찾을 수 없습니다.[/red]")
                console.print("fashion search <검색어> 로 브랜드를 먼저 찾아보세요.")
                raise typer.Exit(1)

            ch_list = await brand_service.get_channels_by_brand(db, b.id)

        console.print(f"\n[bold cyan]{b.name}[/bold cyan] 취급 채널 ({len(ch_list)}개)\n")

        table = Table(show_lines=True)
        table.add_column("채널명", style="cyan")
        table.add_column("홈페이지 URL", style="green")
        table.add_column("타입", style="yellow")

        for ch in ch_list:
            table.add_row(ch.name, ch.url, ch.channel_type or "-")

        console.print(table)

    run_async(_())


@app.command()
def search(query: str = typer.Argument(..., help="브랜드 검색어")):
    """브랜드 검색"""
    async def _():
        await init_db()
        async with AsyncSessionLocal() as db:
            items = await brand_service.search_brands(db, query)

        if not items:
            console.print(f"[yellow]'{query}'에 해당하는 브랜드가 없습니다.[/yellow]")
            return

        table = Table(title=f"'{query}' 검색 결과 ({len(items)}개)", show_lines=True)
        table.add_column("Slug", style="dim")
        table.add_column("브랜드명", style="cyan")
        table.add_column("한글명", style="yellow")

        for b in items:
            table.add_row(b.slug, b.name, b.name_ko or "-")

        console.print(table)
        console.print("\n[dim]채널 조회: fashion brand <slug>[/dim]")

    run_async(_())


if __name__ == "__main__":
    app()
