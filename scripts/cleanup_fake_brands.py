"""
편집샵 이름과 동일한 브랜드(가짜 브랜드) 탐지 및 정리 스크립트.

사용법:
    uv run python scripts/cleanup_fake_brands.py            # DRY-RUN (목록만 출력)
    uv run python scripts/cleanup_fake_brands.py --execute  # 실제 삭제
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import select, delete

from fashion_engine.database import init_db, AsyncSessionLocal
from fashion_engine.models.brand import Brand
from fashion_engine.models.channel import Channel

console = Console()
app = typer.Typer()

# 편집샵 또는 복수 브랜드 취급 채널 타입
_MULTI_BRAND_TYPES = {"edit-shop", "multi-brand", "department"}


async def find_fake_brands() -> list[dict]:
    """편집샵 채널 이름과 동일한 브랜드를 탐지."""
    async with AsyncSessionLocal() as db:
        channels = list(
            (
                await db.execute(
                    select(Channel).where(Channel.channel_type.in_(_MULTI_BRAND_TYPES))
                )
            )
            .scalars()
            .all()
        )
        # 편집샵 이름 집합 (소문자 정규화)
        edit_shop_names_lower = {c.name.lower().strip() for c in channels}
        edit_shop_by_lower: dict[str, Channel] = {
            c.name.lower().strip(): c for c in channels
        }

        brands = list(
            (await db.execute(select(Brand))).scalars().all()
        )

        matches = []
        for brand in brands:
            brand_lower = brand.name.lower().strip()
            if brand_lower in edit_shop_names_lower:
                matched_channel = edit_shop_by_lower[brand_lower]
                matches.append(
                    {
                        "brand_id": brand.id,
                        "brand_name": brand.name,
                        "brand_slug": brand.slug,
                        "brand_tier": brand.tier,
                        "channel_id": matched_channel.id,
                        "channel_name": matched_channel.name,
                        "channel_type": matched_channel.channel_type,
                    }
                )
    return matches


async def delete_brands(brand_ids: list[int]) -> int:
    """브랜드 삭제 (연결된 channel_brand도 cascade 삭제됨)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            delete(Brand).where(Brand.id.in_(brand_ids))
        )
        await db.commit()
        return result.rowcount


@app.command()
def main(
    execute: bool = typer.Option(False, "--execute", help="실제 삭제 실행 (미설정 시 DRY-RUN)"),
) -> None:
    asyncio.run(run(execute))


async def run(execute: bool) -> None:
    await init_db()

    console.print("[bold blue]Fashion Data Engine — 가짜 브랜드 탐지[/bold blue]\n")
    matches = await find_fake_brands()

    if not matches:
        console.print("[green]탐지된 가짜 브랜드 없음 (편집샵 이름과 동일한 브랜드 없음)[/green]")
        return

    table = Table(title=f"탐지된 가짜 브랜드 {len(matches)}개", show_lines=True)
    table.add_column("Brand ID", style="dim")
    table.add_column("브랜드명", style="bold red")
    table.add_column("Slug")
    table.add_column("Tier")
    table.add_column("일치 채널")
    table.add_column("채널 타입")

    for m in matches:
        table.add_row(
            str(m["brand_id"]),
            m["brand_name"],
            m["brand_slug"],
            m["brand_tier"] or "-",
            m["channel_name"],
            m["channel_type"] or "-",
        )

    console.print(table)

    if not execute:
        console.print(
            "\n[yellow]DRY-RUN 모드: 실제 삭제가 수행되지 않았습니다.[/yellow]"
        )
        console.print("삭제하려면 [bold]--execute[/bold] 옵션을 추가하세요.")
        return

    brand_ids = [m["brand_id"] for m in matches]
    console.print(f"\n[bold red]브랜드 {len(brand_ids)}개 삭제 중...[/bold red]")
    deleted = await delete_brands(brand_ids)
    console.print(f"[green]삭제 완료: {deleted}개[/green]")


if __name__ == "__main__":
    app()
