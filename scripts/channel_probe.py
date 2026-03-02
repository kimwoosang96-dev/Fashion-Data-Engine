"""
제품 0개 채널(또는 전체 채널) 플랫폼 탐지/HTTP 상태 진단 스크립트.

기능:
- 메인 URL HTTP 상태 코드 확인
- Shopify 추정: /products.json?limit=1
- Cafe24 추정: /product/list.html?cate_no=1
- CSV 저장
- --apply 시 channels.platform 업데이트
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import httpx
from rich.console import Console
from rich.table import Table
from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.channel import Channel  # noqa: E402
from fashion_engine.models.product import Product  # noqa: E402
from fashion_engine.services.channel_service import update_platform  # noqa: E402

console = Console()
SEM = asyncio.Semaphore(10)


@dataclass
class ProbeTarget:
    channel_id: int
    name: str
    url: str
    platform: str | None


@dataclass
class ProbeResult:
    channel_id: int
    name: str
    url: str
    http_status: int | None
    shopify: bool
    cafe24: bool
    platform_detected: str | None
    note: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="제품 0개 채널 플랫폼 진단")
    p.add_argument("--all", action="store_true", help="전체 활성 채널 대상 (기본: 제품 0개 채널)")
    p.add_argument("--apply", action="store_true", help="감지된 platform를 DB에 반영")
    p.add_argument(
        "--output",
        default=f"reports/channel_probe_{datetime.now().strftime('%Y-%m-%d')}.csv",
        help="CSV 출력 경로",
    )
    return p.parse_args()


async def _check_home(client: httpx.AsyncClient, base_url: str) -> tuple[int | None, str]:
    try:
        resp = await client.get(base_url, timeout=8)
        return resp.status_code, ""
    except Exception as exc:
        return None, str(exc)[:180]


async def _check_shopify(client: httpx.AsyncClient, base_url: str) -> bool:
    url = f"{base_url.rstrip('/')}/products.json?limit=1"
    try:
        resp = await client.get(url, timeout=8)
        if resp.status_code != 200:
            return False
        data = resp.json()
        return isinstance(data, dict) and "products" in data
    except Exception:
        return False


async def _check_cafe24(client: httpx.AsyncClient, base_url: str) -> bool:
    url = f"{base_url.rstrip('/')}/product/list.html?cate_no=1"
    try:
        resp = await client.get(url, timeout=8)
        if resp.status_code != 200:
            return False
        body = resp.text.lower()
        return "cafe24" in body or "xans-product" in body
    except Exception:
        return False


def _detect_platform(shopify: bool, cafe24: bool) -> str | None:
    if shopify:
        return "shopify"
    if cafe24:
        return "cafe24"
    return None


async def _probe_one(client: httpx.AsyncClient, target: ProbeTarget) -> ProbeResult:
    async with SEM:
        http_status, note = await _check_home(client, target.url)
        shopify = await _check_shopify(client, target.url)
        cafe24 = await _check_cafe24(client, target.url)
        detected = _detect_platform(shopify, cafe24)
        if not detected and not note:
            note = "custom platform suspected"
        return ProbeResult(
            channel_id=target.channel_id,
            name=target.name,
            url=target.url,
            http_status=http_status,
            shopify=shopify,
            cafe24=cafe24,
            platform_detected=detected,
            note=note,
        )


async def _load_targets(*, include_all: bool) -> list[ProbeTarget]:
    async with AsyncSessionLocal() as db:
        stmt = (
            select(
                Channel.id,
                Channel.name,
                Channel.url,
                Channel.platform,
                func.count(Product.id).label("product_count"),
            )
            .outerjoin(Product, Product.channel_id == Channel.id)
            .where(Channel.is_active == True)  # noqa: E712
            .group_by(Channel.id)
            .order_by(Channel.name.asc())
        )
        if not include_all:
            stmt = stmt.having(func.count(Product.id) == 0)
        rows = (await db.execute(stmt)).all()
    return [
        ProbeTarget(
            channel_id=int(r.id),
            name=str(r.name),
            url=str(r.url),
            platform=str(r.platform) if r.platform else None,
        )
        for r in rows
    ]


def _print_table(results: Iterable[ProbeResult]) -> None:
    table = Table(title="채널 플랫폼 진단 결과", show_lines=True)
    table.add_column("ID", justify="right")
    table.add_column("채널")
    table.add_column("HTTP", justify="right")
    table.add_column("Shopify", justify="center")
    table.add_column("Cafe24", justify="center")
    table.add_column("Detected")
    table.add_column("Note")
    for r in results:
        table.add_row(
            str(r.channel_id),
            r.name,
            str(r.http_status) if r.http_status is not None else "-",
            "Y" if r.shopify else "-",
            "Y" if r.cafe24 else "-",
            r.platform_detected or "-",
            r.note or "",
        )
    console.print(table)


def _write_csv(results: list[ProbeResult], output_path: str) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "channel_id",
                "name",
                "url",
                "http_status",
                "shopify",
                "cafe24",
                "platform_detected",
                "note",
            ]
        )
        for r in results:
            w.writerow(
                [
                    r.channel_id,
                    r.name,
                    r.url,
                    r.http_status if r.http_status is not None else "",
                    r.shopify,
                    r.cafe24,
                    r.platform_detected or "",
                    r.note,
                ]
            )
    return out


async def _apply_platform(results: list[ProbeResult]) -> int:
    updated = 0
    async with AsyncSessionLocal() as db:
        for r in results:
            if not r.platform_detected:
                continue
            changed = await update_platform(db, r.channel_id, r.platform_detected)
            if changed:
                updated += 1
        if updated:
            await db.commit()
    return updated


async def run(*, include_all: bool, apply: bool, output: str) -> int:
    await init_db()
    targets = await _load_targets(include_all=include_all)
    console.print(f"[cyan]진단 대상 채널[/cyan]: {len(targets)}개")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [_probe_one(client, t) for t in targets]
        results = await asyncio.gather(*tasks)

    results = sorted(results, key=lambda r: (r.platform_detected is None, r.name.lower()))
    _print_table(results)
    csv_path = _write_csv(results, output)
    console.print(f"[green]CSV 저장 완료[/green]: {csv_path}")

    if apply:
        updated = await _apply_platform(results)
        console.print(f"[bold green]DB 업데이트[/bold green]: {updated}개")
    else:
        console.print("[yellow]dry-run: --apply로 platform 반영 가능[/yellow]")
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(
        asyncio.run(
            run(include_all=bool(args.all), apply=bool(args.apply), output=str(args.output))
        )
    )
