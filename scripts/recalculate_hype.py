"""
brand_collaborations 전체 hype_score 재계산 스크립트.

사용법:
    .venv/bin/python scripts/recalculate_hype.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table
from sqlalchemy import func, select

from fashion_engine.database import AsyncSessionLocal, init_db
from fashion_engine.models.brand_collaboration import BrandCollaboration
from fashion_engine.models.channel_brand import ChannelBrand

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


async def main() -> None:
    console.print("[bold blue]Fashion Data Engine — hype_score 재계산[/bold blue]\n")
    await init_db()

    updated = 0
    unchanged = 0

    async with AsyncSessionLocal() as db:
        collabs = (
            await db.execute(select(BrandCollaboration).order_by(BrandCollaboration.id))
        ).scalars().all()

        for collab in collabs:
            new_score = await calculate_hype_score(db, collab.brand_a_id, collab.brand_b_id)
            if collab.hype_score != new_score:
                collab.hype_score = new_score
                updated += 1
            else:
                unchanged += 1

        await db.commit()

    table = Table(title="재계산 결과")
    table.add_column("항목", style="cyan")
    table.add_column("값", justify="right", style="green")
    table.add_row("업데이트", str(updated))
    table.add_row("변경 없음", str(unchanged))
    console.print(table)


if __name__ == "__main__":
    asyncio.run(main())
