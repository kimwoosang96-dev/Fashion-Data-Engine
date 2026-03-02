"""
크롤 불가 채널 자동 감지 + 비활성화 스크립트.

기본은 dry-run이며, --apply 시 is_active=False를 반영한다.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

import httpx
from rich.console import Console
from rich.table import Table
from sqlalchemy import bindparam, func, select, text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.channel import Channel  # noqa: E402
from fashion_engine.models.crawl_run import CrawlChannelLog  # noqa: E402
from fashion_engine.models.product import Product  # noqa: E402

console = Console()

EXCLUDE_CHANNEL_TYPES = {"brand-store"}
DEFAULT_CRITERIA = ("consecutive_failures", "null_platform_stale")
VALID_CRITERIA = {"consecutive_failures", "dead_http", "null_platform_stale"}


@dataclass
class DeadChannelCandidate:
    channel_id: int
    name: str
    url: str
    channel_type: str | None
    reason: str
    detail: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="크롤 불가 채널 비활성화 후보 탐지")
    p.add_argument("--dry-run", action="store_true", help="후보 조회만 수행 (기본)")
    p.add_argument("--apply", action="store_true", help="후보 채널을 is_active=False로 반영")
    p.add_argument("--probe-http", action="store_true", help="HTTP 404/410 탐색 기준 활성화")
    p.add_argument(
        "--criteria",
        default="all",
        help="적용 기준(comma): consecutive_failures,dead_http,null_platform_stale 또는 all",
    )
    p.add_argument("--min-failures", type=int, default=3, help="연속 실패 최소 횟수")
    p.add_argument("--age-days", type=int, default=30, help="NULL platform 노후 기준(일)")
    p.add_argument("--yes", action="store_true", help="apply 확인 프롬프트 자동 승인")
    return p.parse_args()


def _resolve_criteria(raw: str, probe_http: bool) -> set[str]:
    if raw.strip().lower() == "all":
        crit = set(DEFAULT_CRITERIA)
    else:
        crit = {v.strip() for v in raw.split(",") if v.strip()}
        invalid = crit - VALID_CRITERIA
        if invalid:
            raise ValueError(f"invalid criteria: {sorted(invalid)}")
    if probe_http:
        crit.add("dead_http")
    return crit


async def _find_consecutive_failure_channels(min_failures: int) -> list[DeadChannelCandidate]:
    stmt = text(
        """
        WITH ranked AS (
            SELECT
                ccl.channel_id,
                ccl.status,
                ROW_NUMBER() OVER (
                    PARTITION BY ccl.channel_id
                    ORDER BY ccl.crawled_at DESC, ccl.id DESC
                ) AS rn
            FROM crawl_channel_logs ccl
        ),
        recent AS (
            SELECT channel_id, status
            FROM ranked
            WHERE rn <= :min_failures
        )
        SELECT
            c.id AS channel_id,
            c.name AS name,
            c.url AS url,
            c.channel_type AS channel_type,
            COUNT(*) AS total_logs,
            SUM(CASE WHEN r.status = 'failed' THEN 1 ELSE 0 END) AS failed_logs
        FROM channels c
        JOIN recent r ON r.channel_id = c.id
        WHERE c.is_active = 1
          AND (c.channel_type IS NULL OR c.channel_type NOT IN ('brand-store'))
        GROUP BY c.id, c.name, c.url, c.channel_type
        HAVING COUNT(*) >= :min_failures
           AND SUM(CASE WHEN r.status = 'failed' THEN 1 ELSE 0 END) = COUNT(*)
        ORDER BY c.name ASC
        """
    )
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(stmt, {"min_failures": min_failures})).all()
    return [
        DeadChannelCandidate(
            channel_id=int(r.channel_id),
            name=str(r.name),
            url=str(r.url),
            channel_type=r.channel_type,
            reason="consecutive_failures",
            detail=f"최근 {int(r.total_logs)}회 모두 failed",
        )
        for r in rows
    ]


async def _find_null_platform_stale_channels(age_days: int) -> list[DeadChannelCandidate]:
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=age_days)
    async with AsyncSessionLocal() as db:
        stmt = (
            select(
                Channel.id,
                Channel.name,
                Channel.url,
                Channel.channel_type,
                func.count(Product.id).label("product_count"),
            )
            .outerjoin(Product, Product.channel_id == Channel.id)
            .where(Channel.is_active == True)  # noqa: E712
            .where(Channel.platform.is_(None))
            .where(Channel.created_at < cutoff)
            .where((Channel.channel_type.is_(None)) | (~Channel.channel_type.in_(EXCLUDE_CHANNEL_TYPES)))
            .group_by(Channel.id)
            .having(func.count(Product.id) == 0)
            .order_by(Channel.name.asc())
        )
        rows = (await db.execute(stmt)).all()
    return [
        DeadChannelCandidate(
            channel_id=int(r.id),
            name=str(r.name),
            url=str(r.url),
            channel_type=r.channel_type,
            reason="null_platform_stale",
            detail=f"platform=NULL + 제품=0 + 생성 {age_days}일 이상",
        )
        for r in rows
    ]


async def _probe_dead_http() -> list[DeadChannelCandidate]:
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(Channel.id, Channel.name, Channel.url, Channel.channel_type)
                .where(Channel.is_active == True)  # noqa: E712
                .where((Channel.channel_type.is_(None)) | (~Channel.channel_type.in_(EXCLUDE_CHANNEL_TYPES)))
                .order_by(Channel.name.asc())
            )
        ).all()

    sem = asyncio.Semaphore(10)
    async with httpx.AsyncClient(follow_redirects=True) as client:
        async def _check(row) -> DeadChannelCandidate | None:
            async with sem:
                try:
                    resp = await client.get(str(row.url), timeout=8)
                except Exception:
                    return None
                if resp.status_code in {404, 410}:
                    return DeadChannelCandidate(
                        channel_id=int(row.id),
                        name=str(row.name),
                        url=str(row.url),
                        channel_type=row.channel_type,
                        reason="dead_http",
                        detail=f"HTTP {resp.status_code}",
                    )
                return None

        probed = await asyncio.gather(*[_check(r) for r in rows])
    return [p for p in probed if p is not None]


def _dedup_candidates(items: list[DeadChannelCandidate]) -> list[DeadChannelCandidate]:
    merged: dict[int, DeadChannelCandidate] = {}
    for c in items:
        if c.channel_id not in merged:
            merged[c.channel_id] = c
        else:
            prev = merged[c.channel_id]
            merged[c.channel_id] = DeadChannelCandidate(
                channel_id=c.channel_id,
                name=c.name,
                url=c.url,
                channel_type=c.channel_type,
                reason=f"{prev.reason},{c.reason}",
                detail=f"{prev.detail} | {c.detail}",
            )
    return sorted(merged.values(), key=lambda x: x.name.lower())


def _print_candidates(candidates: list[DeadChannelCandidate]) -> None:
    table = Table(title=f"비활성화 후보: {len(candidates)}개", show_lines=True)
    table.add_column("ID", justify="right")
    table.add_column("채널")
    table.add_column("타입")
    table.add_column("이유")
    table.add_column("상세")
    for c in candidates:
        table.add_row(
            str(c.channel_id),
            c.name,
            c.channel_type or "-",
            c.reason,
            c.detail,
        )
    console.print(table)


async def _apply_deactivation(candidates: list[DeadChannelCandidate]) -> int:
    ids = [c.channel_id for c in candidates]
    if len(ids) < 2:
        console.print("[yellow]안전장치: 후보가 2개 미만이라 apply를 중단합니다.[/yellow]")
        return 0
    bp = bindparam("ids", expanding=True)
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("UPDATE channels SET is_active=0 WHERE id IN :ids").bindparams(bp),
            {"ids": ids},
        )
        await db.commit()
    return len(ids)


async def run(args: argparse.Namespace) -> int:
    await init_db()
    criteria = _resolve_criteria(args.criteria, args.probe_http)
    candidates: list[DeadChannelCandidate] = []

    if "consecutive_failures" in criteria:
        candidates.extend(await _find_consecutive_failure_channels(args.min_failures))
    if "null_platform_stale" in criteria:
        candidates.extend(await _find_null_platform_stale_channels(args.age_days))
    if "dead_http" in criteria:
        candidates.extend(await _probe_dead_http())

    deduped = _dedup_candidates(candidates)
    _print_candidates(deduped)

    if not args.apply:
        console.print("[cyan]dry-run 완료[/cyan]: --apply로 비활성화 반영 가능")
        return 0

    if not deduped:
        console.print("[green]적용할 후보가 없습니다.[/green]")
        return 0

    if not args.yes:
        ans = input(f"후보 {len(deduped)}개를 비활성화(is_active=0)할까요? [y/N]: ").strip().lower()
        if ans not in {"y", "yes"}:
            console.print("취소되었습니다.")
            return 0

    applied = await _apply_deactivation(deduped)
    console.print(f"[bold green]비활성화 완료[/bold green]: {applied}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parse_args())))
