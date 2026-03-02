"""
NULL platform 채널에 대해 Cafe24 여부를 탐색한다.

신호:
1) header/cookie에 cafe24/echosting
2) HTML 메타/스크립트 신호
3) URL 패턴(cafe24.com/echosting)
4) /product/maker.html + cate_no 링크
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.channel import Channel  # noqa: E402
from fashion_engine.services.channel_service import update_platform  # noqa: E402

console = Console()
SEM = asyncio.Semaphore(8)


@dataclass
class Target:
    channel_id: int
    name: str
    url: str


@dataclass
class Cafe24Probe:
    channel_id: int
    name: str
    url: str
    home_status: int | None
    maker_status: int | None
    cate_links: int
    signal_url: bool
    signal_header: bool
    signal_html: bool
    signal_maker: bool
    confidence: str
    detected: bool
    note: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cafe24 채널 자동 감지")
    p.add_argument("--apply", action="store_true", help="감지 결과를 channels.platform='cafe24'로 반영")
    p.add_argument(
        "--output",
        default=f"reports/probe_cafe24_{datetime.now().strftime('%Y-%m-%d')}.csv",
        help="CSV 출력 경로",
    )
    return p.parse_args()


def _url_signal(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return ("cafe24" in host) or ("echosting" in host)


def _response_signals(resp: httpx.Response | None) -> tuple[bool, bool]:
    if resp is None:
        return False, False
    powered = resp.headers.get("x-powered-by", "").lower()
    cookies = " ".join(resp.headers.get_list("set-cookie")).lower()
    signal_header = ("cafe24" in powered) or ("echosting" in cookies)
    body = (resp.text or "")[:12000].lower()
    signal_html = (
        "meta name=\"generator\"" in body and "cafe24" in body
    ) or ("echosting" in body) or ("xans-layout" in body)
    return signal_header, signal_html


async def _fetch(client: httpx.AsyncClient, url: str) -> httpx.Response | None:
    try:
        return await client.get(url, timeout=10)
    except Exception:
        return None


async def _probe_one(client: httpx.AsyncClient, t: Target) -> Cafe24Probe:
    async with SEM:
        home = await _fetch(client, t.url)
        maker = await _fetch(client, f"{t.url.rstrip('/')}/product/maker.html")

        signal_url = _url_signal(t.url)
        signal_header, signal_html = _response_signals(home)

        signal_maker = False
        cate_links = 0
        if maker is not None and maker.status_code == 200:
            soup = BeautifulSoup(maker.text, "html.parser")
            for a in soup.select("a[href*='cate_no=']:not([href*='product_no='])"):
                href = a.get("href") or ""
                if re.search(r"cate_no=(\d+)", href):
                    cate_links += 1
            signal_maker = cate_links > 0

        score = sum([signal_url, signal_header, signal_html, signal_maker])
        detected = score >= 2 or signal_maker
        confidence = "high" if score >= 3 else ("medium" if score == 2 else "low")
        note = ""
        if not detected:
            note = "Cafe24 신호 부족"

        return Cafe24Probe(
            channel_id=t.channel_id,
            name=t.name,
            url=t.url,
            home_status=home.status_code if home is not None else None,
            maker_status=maker.status_code if maker is not None else None,
            cate_links=cate_links,
            signal_url=signal_url,
            signal_header=signal_header,
            signal_html=signal_html,
            signal_maker=signal_maker,
            confidence=confidence,
            detected=detected,
            note=note,
        )


async def _load_targets() -> list[Target]:
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(Channel.id, Channel.name, Channel.url)
                .where(Channel.is_active == True)  # noqa: E712
                .where(Channel.platform.is_(None))
                .order_by(Channel.name.asc())
            )
        ).all()
    return [Target(channel_id=int(r.id), name=str(r.name), url=str(r.url)) for r in rows]


def _print_table(rows: list[Cafe24Probe]) -> None:
    table = Table(title=f"Cafe24 탐색 결과 ({len(rows)}개)", show_lines=True)
    table.add_column("ID", justify="right")
    table.add_column("채널")
    table.add_column("HOME", justify="right")
    table.add_column("MAKER", justify="right")
    table.add_column("cate_no", justify="right")
    table.add_column("URL")
    table.add_column("HDR")
    table.add_column("HTML")
    table.add_column("MAKER")
    table.add_column("Detected")
    table.add_column("Conf")
    for r in rows:
        table.add_row(
            str(r.channel_id),
            r.name,
            str(r.home_status) if r.home_status is not None else "-",
            str(r.maker_status) if r.maker_status is not None else "-",
            str(r.cate_links),
            "Y" if r.signal_url else "-",
            "Y" if r.signal_header else "-",
            "Y" if r.signal_html else "-",
            "Y" if r.signal_maker else "-",
            "Y" if r.detected else "-",
            r.confidence,
        )
    console.print(table)


def _write_csv(rows: list[Cafe24Probe], output: str) -> Path:
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "channel_id", "name", "url", "home_status", "maker_status", "cate_links",
            "signal_url", "signal_header", "signal_html", "signal_maker",
            "detected", "confidence", "note",
        ])
        for r in rows:
            w.writerow([
                r.channel_id, r.name, r.url, r.home_status or "", r.maker_status or "", r.cate_links,
                r.signal_url, r.signal_header, r.signal_html, r.signal_maker,
                r.detected, r.confidence, r.note,
            ])
    return out


async def _apply(rows: list[Cafe24Probe]) -> int:
    updated = 0
    async with AsyncSessionLocal() as db:
        for r in rows:
            if not r.detected:
                continue
            changed = await update_platform(db, r.channel_id, "cafe24")
            if changed:
                updated += 1
        if updated:
            await db.commit()
    return updated


async def run(*, apply: bool, output: str) -> int:
    await init_db()
    targets = await _load_targets()
    console.print(f"[cyan]대상(NULL platform)[/cyan]: {len(targets)}개")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        rows = await asyncio.gather(*[_probe_one(client, t) for t in targets])

    rows = sorted(rows, key=lambda x: (not x.detected, x.name.lower()))
    _print_table(rows)

    detected_count = sum(1 for r in rows if r.detected)
    console.print(f"[green]Cafe24 감지[/green]: {detected_count}개")

    out = _write_csv(rows, output)
    console.print(f"[green]CSV 저장 완료[/green]: {out}")

    if apply:
        updated = await _apply(rows)
        console.print(f"[bold green]DB 업데이트[/bold green]: {updated}개")
    else:
        console.print("[yellow]dry-run: --apply로 platform 반영[/yellow]")
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(asyncio.run(run(apply=bool(args.apply), output=str(args.output))))
