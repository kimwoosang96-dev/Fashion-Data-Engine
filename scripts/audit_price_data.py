"""
오염된 price_history 레코드 탐지 및 보고 스크립트.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from dataclasses import dataclass
from statistics import median
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from sqlalchemy import text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402

console = Console()

COUNTRY_MIN_KRW: dict[str, int] = {
    "US": 10_000,
    "UK": 10_000,
    "GB": 10_000,
    "EU": 10_000,
    "AU": 10_000,
    "CA": 10_000,
    "SG": 10_000,
    "HK": 10_000,
    "JP": 1_000,
    "KR": 100,
}


@dataclass
class SuspiciousRow:
    id: int
    channel_id: int
    channel_name: str
    country: str | None
    product_id: int
    price: int


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="price_history 오염 데이터 감사")
    p.add_argument("--verbose", action="store_true", help="채널별 샘플 상세 출력")
    return p.parse_args()


def _country_threshold(country: str | None) -> int:
    return COUNTRY_MIN_KRW.get((country or "").upper(), 1_000)


async def _load_rows() -> list[tuple]:
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT
                        ph.id,
                        p.channel_id,
                        c.name,
                        c.country,
                        ph.product_id,
                        CAST(ph.price AS INTEGER) AS price_krw
                    FROM price_history ph
                    JOIN products p ON p.id = ph.product_id
                    JOIN channels c ON c.id = p.channel_id
                    WHERE ph.currency = 'KRW'
                    """
                )
            )
        ).all()
    return list(rows)


async def _load_gap_over_300_count() -> int:
    async with AsyncSessionLocal() as db:
        cnt = (
            await db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM product_catalog
                    WHERE min_price_krw > 0
                      AND max_price_krw > 0
                      AND max_price_krw > min_price_krw * 3
                    """
                )
            )
        ).scalar()
    return int(cnt or 0)


def _detect(rows: list[tuple]) -> list[SuspiciousRow]:
    by_channel: dict[int, list[int]] = defaultdict(list)
    channel_meta: dict[int, tuple[str, str | None]] = {}
    for r in rows:
        by_channel[int(r.channel_id)].append(int(r.price_krw))
        channel_meta[int(r.channel_id)] = (str(r.name), r.country)

    medians: dict[int, float] = {}
    for cid, prices in by_channel.items():
        medians[cid] = float(median(prices)) if prices else 0.0

    suspicious: list[SuspiciousRow] = []
    for r in rows:
        cid = int(r.channel_id)
        price = int(r.price_krw)
        country = r.country
        cmin = _country_threshold(country)
        median_floor = int(medians[cid] * 0.01) if medians[cid] > 0 else 0
        if price < cmin or (median_floor > 0 and price < median_floor):
            suspicious.append(
                SuspiciousRow(
                    id=int(r.id),
                    channel_id=cid,
                    channel_name=str(r.name),
                    country=country,
                    product_id=int(r.product_id),
                    price=price,
                )
            )
    return suspicious


def _print_summary(rows: list[tuple], suspicious: list[SuspiciousRow], gap_over_300: int, verbose: bool) -> None:
    total = len(rows)
    suspicious_n = len(suspicious)
    console.print(f"전체 price_history(KRW): {total:,}")
    console.print(f"의심 레코드: {suspicious_n:,} ({(suspicious_n / total * 100) if total else 0:.2f}%)")
    console.print(f"Catalog 격차 300%+ 항목 수: {gap_over_300:,}")

    by_channel: dict[int, list[SuspiciousRow]] = defaultdict(list)
    for s in suspicious:
        by_channel[s.channel_id].append(s)

    table = Table(title="오염 의심 채널 분포 (상위 30)")
    table.add_column("채널")
    table.add_column("국가")
    table.add_column("의심 건수", justify="right")
    table.add_column("최저가", justify="right")
    for _, items in sorted(by_channel.items(), key=lambda kv: len(kv[1]), reverse=True)[:30]:
        table.add_row(
            items[0].channel_name,
            (items[0].country or "-"),
            str(len(items)),
            str(min(i.price for i in items)),
        )
    console.print(table)

    if verbose and suspicious:
        sample = Table(title="의심 샘플 (상위 50)")
        sample.add_column("id", justify="right")
        sample.add_column("채널")
        sample.add_column("국가")
        sample.add_column("product_id", justify="right")
        sample.add_column("price_krw", justify="right")
        for s in sorted(suspicious, key=lambda x: x.price)[:50]:
            sample.add_row(str(s.id), s.channel_name, s.country or "-", str(s.product_id), str(s.price))
        console.print(sample)


async def run(verbose: bool) -> int:
    await init_db()
    rows = await _load_rows()
    suspicious = _detect(rows)
    gap_over_300 = await _load_gap_over_300_count()
    _print_summary(rows, suspicious, gap_over_300, verbose)
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(asyncio.run(run(verbose=bool(args.verbose))))
