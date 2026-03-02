"""
Cafe24 브랜드 카테고리(cate_no)를 channel_brands에 사전 등록한다.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.table import Table
from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.channel import Channel  # noqa: E402
from fashion_engine.crawler.product_crawler import ProductCrawler  # noqa: E402
from fashion_engine.services.brand_service import upsert_brand, link_brand_to_channel  # noqa: E402

console = Console()


@dataclass
class SeedResult:
    channel_id: int
    channel_name: str
    discovered: int
    linked: int
    skipped: bool
    note: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cafe24 cate_no 사전 등록")
    p.add_argument("--channel-id", type=int, default=0, help="특정 채널 ID만 처리")
    p.add_argument("--apply", action="store_true", help="실제 DB 반영")
    return p.parse_args()


async def _load_targets(channel_id: int | None) -> list[Channel]:
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Channel)
            .where(Channel.is_active == True)  # noqa: E712
            .where(Channel.platform == "cafe24")
            .order_by(Channel.name.asc())
        )
        if channel_id:
            stmt = stmt.where(Channel.id == channel_id)
        return list((await db.execute(stmt)).scalars().all())


async def run(*, channel_id: int | None, apply: bool) -> int:
    await init_db()
    targets = await _load_targets(channel_id)
    console.print(f"[cyan]대상 Cafe24 채널[/cyan]: {len(targets)}개")

    results: list[SeedResult] = []

    async with ProductCrawler(request_delay=0.3) as crawler:
        for ch in targets:
            categories = await crawler._discover_cafe24_brand_categories(ch.url)  # noqa: SLF001
            if not categories:
                results.append(
                    SeedResult(
                        channel_id=ch.id,
                        channel_name=ch.name,
                        discovered=0,
                        linked=0,
                        skipped=True,
                        note="cate_no 미발견",
                    )
                )
                continue

            linked = 0
            if apply:
                async with AsyncSessionLocal() as db:
                    for brand_name, cate_no in categories:
                        brand = await upsert_brand(db, brand_name)
                        await link_brand_to_channel(
                            db,
                            brand_id=brand.id,
                            channel_id=ch.id,
                            cate_no=str(cate_no),
                        )
                        linked += 1

            results.append(
                SeedResult(
                    channel_id=ch.id,
                    channel_name=ch.name,
                    discovered=len(categories),
                    linked=linked,
                    skipped=False,
                    note="applied" if apply else "dry-run",
                )
            )

    table = Table(title="Cafe24 cate_no 시드 결과", show_lines=True)
    table.add_column("ID", justify="right")
    table.add_column("채널")
    table.add_column("발견", justify="right")
    table.add_column("반영", justify="right")
    table.add_column("상태")
    table.add_column("메모")

    for r in results:
        table.add_row(
            str(r.channel_id),
            r.channel_name,
            str(r.discovered),
            str(r.linked),
            "skipped" if r.skipped else "ok",
            r.note,
        )
    console.print(table)

    total_found = sum(r.discovered for r in results)
    total_linked = sum(r.linked for r in results)
    console.print(f"[green]총 발견 cate_no[/green]: {total_found}")
    if apply:
        console.print(f"[green]총 반영 링크[/green]: {total_linked}")
    else:
        console.print("[yellow]dry-run: --apply로 DB 반영[/yellow]")

    return 0


if __name__ == "__main__":
    args = parse_args()
    cid = int(args.channel_id) if int(args.channel_id) > 0 else None
    raise SystemExit(asyncio.run(run(channel_id=cid, apply=bool(args.apply))))
