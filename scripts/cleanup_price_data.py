"""
오염된 price_history 레코드 정리 스크립트.

기본은 dry-run이며, --apply 시 삭제를 수행한다.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from statistics import median
import sys
from pathlib import Path

from rich.console import Console
from sqlalchemy import bindparam, text

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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="price_history 오염 레코드 정리")
    p.add_argument("--apply", action="store_true", help="실제 삭제 수행")
    p.add_argument("--yes", action="store_true", help="대량 삭제 확인 프롬프트 자동 승인")
    p.add_argument("--limit", type=int, default=0, help="테스트용 삭제 상한(0=전체)")
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


def _detect_ids(rows: list[tuple]) -> list[int]:
    by_channel: dict[int, list[int]] = defaultdict(list)
    for r in rows:
        by_channel[int(r.channel_id)].append(int(r.price_krw))
    medians = {cid: float(median(vals)) if vals else 0.0 for cid, vals in by_channel.items()}

    ids: list[int] = []
    for r in rows:
        cid = int(r.channel_id)
        price = int(r.price_krw)
        cmin = _country_threshold(r.country)
        median_floor = int(medians[cid] * 0.01) if medians[cid] > 0 else 0
        if price < cmin or (median_floor > 0 and price < median_floor):
            ids.append(int(r.id))
    return sorted(set(ids))


async def _delete_ids(ids: list[int]) -> int:
    bp = bindparam("ids", expanding=True)
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("DELETE FROM price_history WHERE id IN :ids").bindparams(bp),
            {"ids": ids},
        )
        await db.commit()
    return len(ids)


async def run(apply: bool, yes: bool, limit: int) -> int:
    await init_db()
    rows = await _load_rows()
    ids = _detect_ids(rows)
    if limit > 0:
        ids = ids[:limit]
    console.print(f"삭제 후보 price_history: {len(ids):,}개")
    if not apply:
        console.print("[cyan]dry-run 완료[/cyan] --apply로 실제 삭제 수행")
        return 0

    if not ids:
        console.print("[green]삭제할 레코드가 없습니다.[/green]")
        return 0

    if len(ids) > 10_000 and not yes:
        ans = input(f"{len(ids):,}개를 삭제할까요? [y/N]: ").strip().lower()
        if ans not in {"y", "yes"}:
            console.print("취소되었습니다.")
            return 0

    deleted = await _delete_ids(ids)
    console.print(f"[bold green]삭제 완료[/bold green]: {deleted:,}개")
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(asyncio.run(run(apply=bool(args.apply), yes=bool(args.yes), limit=int(args.limit))))
