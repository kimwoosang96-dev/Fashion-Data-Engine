"""
물리적으로 접근 불가능한 채널(DNS/SSL/리다이렉트 루프/404/410)을 비활성화한다.
"""
from __future__ import annotations

import argparse
import asyncio
import socket
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.channel import Channel  # noqa: E402

console = Console()
SEM = asyncio.Semaphore(10)


@dataclass
class Candidate:
    channel_id: int
    name: str
    url: str
    channel_type: str | None
    reason: str
    detail: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="접근 불가 채널 비활성화")
    p.add_argument("--apply", action="store_true", help="is_active=False 반영")
    p.add_argument("--yes", action="store_true", help="apply 확인 프롬프트 생략")
    p.add_argument("--include-brand-stores", action="store_true", help="brand-store도 포함")
    return p.parse_args()


def _classify_exception(exc: BaseException) -> tuple[str | None, str]:
    if isinstance(exc, httpx.TooManyRedirects):
        return "redirect_loop", "too_many_redirects"
    if isinstance(exc, httpx.ConnectError):
        txt = str(exc).lower()
        cause = getattr(exc, "__cause__", None)
        if isinstance(cause, socket.gaierror) or "name or service not known" in txt or "nodename nor servname" in txt:
            return "dns_error", str(exc)[:180]
        if "certificate" in txt or "ssl" in txt or "tls" in txt:
            return "ssl_error", str(exc)[:180]
        return None, str(exc)[:180]
    if isinstance(exc, httpx.RequestError):
        txt = str(exc).lower()
        if "certificate" in txt or "ssl" in txt or "tls" in txt:
            return "ssl_error", str(exc)[:180]
    return None, str(exc)[:180]


async def _probe_one(client: httpx.AsyncClient, ch: Channel) -> Candidate | None:
    async with SEM:
        try:
            resp = await client.get(ch.url, timeout=10)
        except Exception as exc:  # noqa: BLE001
            reason, detail = _classify_exception(exc)
            if reason:
                return Candidate(
                    channel_id=ch.id,
                    name=ch.name,
                    url=ch.url,
                    channel_type=ch.channel_type,
                    reason=reason,
                    detail=detail,
                )
            return None

        if resp.status_code in {404, 410}:
            return Candidate(
                channel_id=ch.id,
                name=ch.name,
                url=ch.url,
                channel_type=ch.channel_type,
                reason="not_found",
                detail=f"HTTP {resp.status_code}",
            )
        return None


async def _load_targets(include_brand_stores: bool) -> list[Channel]:
    async with AsyncSessionLocal() as db:
        stmt = select(Channel).where(Channel.is_active == True)  # noqa: E712
        if not include_brand_stores:
            stmt = stmt.where((Channel.channel_type.is_(None)) | (Channel.channel_type != "brand-store"))
        stmt = stmt.order_by(Channel.name.asc())
        return list((await db.execute(stmt)).scalars().all())


def _print_table(rows: list[Candidate]) -> None:
    table = Table(title=f"비활성화 후보 (접근 불가): {len(rows)}개", show_lines=True)
    table.add_column("ID", justify="right")
    table.add_column("채널")
    table.add_column("타입")
    table.add_column("사유")
    table.add_column("상세")
    for r in rows:
        table.add_row(str(r.channel_id), r.name, r.channel_type or "-", r.reason, r.detail)
    console.print(table)


async def _apply(rows: list[Candidate]) -> int:
    if not rows:
        return 0
    ids = [r.channel_id for r in rows]
    async with AsyncSessionLocal() as db:
        channels = list((await db.execute(select(Channel).where(Channel.id.in_(ids)))).scalars().all())
        for ch in channels:
            ch.is_active = False
        await db.commit()
    return len(channels)


async def run(*, apply: bool, yes: bool, include_brand_stores: bool) -> int:
    await init_db()
    targets = await _load_targets(include_brand_stores)
    console.print(f"[cyan]탐색 대상[/cyan]: {len(targets)}개")

    async with httpx.AsyncClient(follow_redirects=True, max_redirects=10) as client:
        found = await asyncio.gather(*[_probe_one(client, ch) for ch in targets])

    rows = sorted([r for r in found if r is not None], key=lambda x: (x.reason, x.name.lower()))
    _print_table(rows)

    if not apply:
        console.print("[yellow]dry-run: --apply로 반영 가능[/yellow]")
        return 0

    if rows and not yes:
        console.print("[yellow]apply 확인 필요: --yes를 추가해 주세요[/yellow]")
        return 0

    updated = await _apply(rows)
    console.print(f"[bold green]비활성화 완료[/bold green]: {updated}개")
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(
        asyncio.run(
            run(
                apply=bool(args.apply),
                yes=bool(args.yes),
                include_brand_stores=bool(args.include_brand_stores),
            )
        )
    )
