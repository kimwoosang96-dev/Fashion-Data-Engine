"""
브랜드 티어 CSV를 읽어 DB의 Brand.tier를 일괄 업데이트.

사용법:
    .venv/bin/python scripts/classify_brands.py data/brand_tiers.csv
"""
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from fashion_engine.database import AsyncSessionLocal, init_db
from fashion_engine.models.brand import Brand

VALID_TIERS = {"high-end", "premium", "street", "sports", "spa"}

app = typer.Typer()
console = Console()


@app.command()
def main(csv_path: str = typer.Argument(..., help="slug,tier CSV 경로")) -> None:
    asyncio.run(run(Path(csv_path)))


async def run(csv_path: Path) -> None:
    console.print("[bold blue]Fashion Data Engine — 브랜드 티어 분류 임포트[/bold blue]\n")

    if not csv_path.exists():
        console.print(f"[red]파일 없음:[/red] {csv_path}")
        raise typer.Exit(1)

    await init_db()

    updated = 0
    invalid_rows = 0
    missing_slugs: list[str] = []

    async with AsyncSessionLocal() as db:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                slug = (row.get("slug") or "").strip()
                tier = (row.get("tier") or "").strip()

                if not slug or tier not in VALID_TIERS:
                    invalid_rows += 1
                    console.print(
                        f"[yellow]스킵[/yellow] line {row_num}: slug/tier 값이 유효하지 않음 "
                        f"(slug={slug!r}, tier={tier!r})"
                    )
                    continue

                brand = (
                    await db.execute(select(Brand).where(Brand.slug == slug))
                ).scalar_one_or_none()
                if not brand:
                    missing_slugs.append(slug)
                    continue

                if brand.tier != tier:
                    brand.tier = tier
                    updated += 1

        await db.commit()

    table = Table(title="분류 결과")
    table.add_column("항목", style="cyan")
    table.add_column("값", justify="right", style="green")
    table.add_row("업데이트", str(updated))
    table.add_row("유효하지 않은 행", str(invalid_rows))
    table.add_row("미존재 slug", str(len(missing_slugs)))
    console.print(table)

    if missing_slugs:
        console.print("[yellow]DB에 없는 slug:[/yellow] " + ", ".join(sorted(set(missing_slugs))))


if __name__ == "__main__":
    app()
