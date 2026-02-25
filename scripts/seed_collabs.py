"""
브랜드 협업 CSV를 읽어 brand_collaborations 시드 데이터를 생성.

사용법:
    .venv/bin/python scripts/seed_collabs.py data/brand_collabs.csv
"""
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import and_, func, select

from fashion_engine.database import AsyncSessionLocal, init_db
from fashion_engine.models.brand import Brand
from fashion_engine.models.brand_collaboration import BrandCollaboration
from fashion_engine.models.channel_brand import ChannelBrand

VALID_CATEGORIES = {"footwear", "apparel", "accessories", "lifestyle"}

app = typer.Typer()
console = Console()


async def calculate_hype_score(db, brand_a_id: int, brand_b_id: int) -> int:
    shared_channels = (
        select(ChannelBrand.channel_id)
        .where(ChannelBrand.brand_id.in_([brand_a_id, brand_b_id]))
        .group_by(ChannelBrand.channel_id)
        .having(func.count(func.distinct(ChannelBrand.brand_id)) == 2)
    ).subquery()

    shared_count = await db.scalar(select(func.count()).select_from(shared_channels))
    return min((shared_count or 0) * 10, 100)


@app.command()
def main(csv_path: str = typer.Argument(..., help="협업 시드 CSV 경로")) -> None:
    asyncio.run(run(Path(csv_path)))


async def run(csv_path: Path) -> None:
    console.print("[bold blue]Fashion Data Engine — 협업 시드 임포트[/bold blue]\n")

    if not csv_path.exists():
        console.print(f"[red]파일 없음:[/red] {csv_path}")
        raise typer.Exit(1)

    await init_db()

    created = 0
    skipped_missing_slug = 0
    skipped_duplicate = 0
    skipped_invalid = 0

    async with AsyncSessionLocal() as db:
        brand_rows = (await db.execute(select(Brand.id, Brand.slug))).all()
        slug_to_id = {slug: brand_id for brand_id, slug in brand_rows}

        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                a_slug = (row.get("brand_a_slug") or "").strip()
                b_slug = (row.get("brand_b_slug") or "").strip()
                collab_name = (row.get("collab_name") or "").strip()
                category = (row.get("collab_category") or "").strip() or None
                release_year_raw = (row.get("release_year") or "").strip()
                source_url = (row.get("source_url") or "").strip() or None
                notes = (row.get("notes") or "").strip() or None

                if not a_slug or not b_slug or not collab_name:
                    skipped_invalid += 1
                    console.print(f"[yellow]스킵[/yellow] line {row_num}: 필수 컬럼 누락")
                    continue

                if category and category not in VALID_CATEGORIES:
                    skipped_invalid += 1
                    console.print(
                        f"[yellow]스킵[/yellow] line {row_num}: collab_category 유효하지 않음 ({category})"
                    )
                    continue

                a_id = slug_to_id.get(a_slug)
                b_id = slug_to_id.get(b_slug)
                if not a_id or not b_id:
                    skipped_missing_slug += 1
                    console.print(
                        f"[yellow]스킵[/yellow] line {row_num}: slug 미존재 ({a_slug}, {b_slug})"
                    )
                    continue

                if a_id == b_id:
                    skipped_invalid += 1
                    console.print(f"[yellow]스킵[/yellow] line {row_num}: 같은 브랜드 pair")
                    continue

                brand_a_id, brand_b_id = sorted([a_id, b_id])
                release_year = int(release_year_raw) if release_year_raw else None
                hype_score = await calculate_hype_score(db, brand_a_id, brand_b_id)

                duplicate = (
                    await db.execute(
                        select(BrandCollaboration.id).where(
                            and_(
                                BrandCollaboration.brand_a_id == brand_a_id,
                                BrandCollaboration.brand_b_id == brand_b_id,
                                BrandCollaboration.collab_name == collab_name,
                            )
                        )
                    )
                ).scalar_one_or_none()
                if duplicate:
                    skipped_duplicate += 1
                    continue

                db.add(
                    BrandCollaboration(
                        brand_a_id=brand_a_id,
                        brand_b_id=brand_b_id,
                        collab_name=collab_name,
                        collab_category=category,
                        release_year=release_year,
                        hype_score=hype_score,
                        source_url=source_url,
                        notes=notes,
                    )
                )
                created += 1

        await db.commit()

    table = Table(title="시드 결과")
    table.add_column("항목", style="cyan")
    table.add_column("값", justify="right", style="green")
    table.add_row("생성", str(created))
    table.add_row("중복 스킵", str(skipped_duplicate))
    table.add_row("slug 미존재 스킵", str(skipped_missing_slug))
    table.add_row("유효성 스킵", str(skipped_invalid))
    console.print(table)


if __name__ == "__main__":
    app()
