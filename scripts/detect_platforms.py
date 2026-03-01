"""
기존 채널 대상 플랫폼 소급 감지 스크립트.

규칙:
- {channel_url}/shop.json 200 + JSON(shop 필드) 응답이면 platform=shopify

기본은 dry-run이며, --apply 시 DB 업데이트를 수행한다.
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
import typer
from rich.console import Console
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db
from fashion_engine.models.channel import Channel
from fashion_engine.services.channel_service import update_platform

app = typer.Typer()
console = Console()


@dataclass
class DetectStats:
    scanned: int = 0
    detected_shopify: int = 0
    updated: int = 0
    failed: int = 0


async def _is_shopify(client: httpx.AsyncClient, base_url: str) -> bool:
    url = f"{base_url.rstrip('/')}/shop.json"
    try:
        resp = await client.get(url, timeout=8)
        if resp.status_code != 200:
            return False
        data = resp.json()
        return isinstance(data, dict) and isinstance(data.get("shop"), dict)
    except Exception:
        return False


async def run_detect(apply: bool, limit: int) -> DetectStats:
    stats = DetectStats()
    async with AsyncSessionLocal() as db:
        query = select(Channel.id, Channel.name, Channel.url, Channel.platform).where(Channel.is_active == True)
        if limit > 0:
            query = query.limit(limit)
        rows = (await db.execute(query.order_by(Channel.id.asc()))).all()

    async with httpx.AsyncClient(follow_redirects=True) as client:
        for row in rows:
            stats.scanned += 1
            is_shopify = await _is_shopify(client, row.url)
            if is_shopify:
                stats.detected_shopify += 1
                if apply:
                    async with AsyncSessionLocal() as db:
                        changed = await update_platform(db, row.id, "shopify")
                        if changed:
                            stats.updated += 1
                            await db.commit()
            else:
                stats.failed += 1

            if stats.scanned % 50 == 0:
                console.print(
                    f"[dim]progress[/dim] scanned={stats.scanned} detected_shopify={stats.detected_shopify} updated={stats.updated}"
                )

    return stats


@app.command()
def cli_main(
    apply: bool = typer.Option(False, "--apply", help="실제 DB 업데이트 실행"),
    limit: int = typer.Option(0, "--limit", min=0, help="감지 상한 (0=전체)"),
):
    asyncio.run(_main(apply=apply, limit=limit))


async def _main(apply: bool, limit: int) -> None:
    await init_db()
    stats = await run_detect(apply=apply, limit=limit)
    mode = "APPLY" if apply else "DRY-RUN"
    console.print(f"[bold blue]platform detect ({mode})[/bold blue]")
    console.print(f"scanned={stats.scanned}")
    console.print(f"detected_shopify={stats.detected_shopify}")
    console.print(f"updated={stats.updated}")
    console.print(f"non_shopify_or_failed={stats.failed}")
    if not apply:
        console.print("[yellow]dry-run 완료: --apply로 platform 저장 가능[/yellow]")


if __name__ == "__main__":
    app()
