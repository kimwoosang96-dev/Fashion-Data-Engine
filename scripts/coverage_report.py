from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.channel import Channel  # noqa: E402
from fashion_engine.models.crawl_run import CrawlChannelLog  # noqa: E402
from fashion_engine.services.alert_service import send_coverage_report_alert  # noqa: E402


@dataclass
class CoverageRow:
    report_type: str
    channel_name: str
    channel_url: str
    recent_count: int = 0
    previous_count: int = 0
    note: str = ""


@dataclass
class CoverageReport:
    generated_at: datetime
    dead_channels: list[CoverageRow]
    degraded_channels: list[CoverageRow]
    draft_channels: list[CoverageRow]
    output_path: str | None = None


async def build_report(*, days: int = 7) -> CoverageReport:
    await init_db()
    now = datetime.utcnow()
    recent_cutoff = now - timedelta(days=days)
    previous_cutoff = now - timedelta(days=days * 2)

    async with AsyncSessionLocal() as db:
        channels = (
            await db.execute(select(Channel).order_by(Channel.name.asc()))
        ).scalars().all()
        logs = (
            await db.execute(
                select(CrawlChannelLog).where(CrawlChannelLog.crawled_at >= previous_cutoff)
            )
        ).scalars().all()

    recent_counts: dict[int, int] = {}
    previous_counts: dict[int, int] = {}
    for log in logs:
        target = recent_counts if log.crawled_at >= recent_cutoff else previous_counts
        target[log.channel_id] = target.get(log.channel_id, 0) + int(log.products_found or 0)

    dead_channels: list[CoverageRow] = []
    degraded_channels: list[CoverageRow] = []
    draft_channels: list[CoverageRow] = []

    for channel in channels:
        recent = recent_counts.get(channel.id, 0)
        previous = previous_counts.get(channel.id, 0)
        if not channel.is_active:
            draft_channels.append(
                CoverageRow(
                    report_type="draft",
                    channel_name=channel.name,
                    channel_url=channel.url,
                    recent_count=recent,
                    previous_count=previous,
                    note="draft/inactive channel",
                )
            )
            continue
        if recent == 0:
            dead_channels.append(
                CoverageRow(
                    report_type="dead",
                    channel_name=channel.name,
                    channel_url=channel.url,
                    recent_count=recent,
                    previous_count=previous,
                    note=f"{days}일간 수집 0건",
                )
            )
            continue
        if previous > 0 and recent <= previous * 0.5:
            drop_ratio = 100 - int((recent / previous) * 100)
            degraded_channels.append(
                CoverageRow(
                    report_type="degraded",
                    channel_name=channel.name,
                    channel_url=channel.url,
                    recent_count=recent,
                    previous_count=previous,
                    note=f"직전 {days}일 대비 {drop_ratio}% 감소",
                )
            )

    return CoverageReport(
        generated_at=now,
        dead_channels=dead_channels,
        degraded_channels=degraded_channels,
        draft_channels=draft_channels,
    )


def write_csv_report(report: CoverageReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "report_type",
                "channel_name",
                "channel_url",
                "recent_count",
                "previous_count",
                "note",
            ],
        )
        writer.writeheader()
        for row in report.dead_channels + report.degraded_channels + report.draft_channels:
            writer.writerow(
                {
                    "report_type": row.report_type,
                    "channel_name": row.channel_name,
                    "channel_url": row.channel_url,
                    "recent_count": row.recent_count,
                    "previous_count": row.previous_count,
                    "note": row.note,
                }
            )


async def run(*, days: int = 7, output_path: str | None = None, send_discord: bool = True) -> CoverageReport:
    report = await build_report(days=days)
    if output_path:
        write_csv_report(report, Path(output_path))
        report.output_path = output_path
    if send_discord:
        await send_coverage_report_alert(report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate channel coverage report.")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument(
        "--output",
        default=f"reports/coverage_report_{datetime.utcnow().strftime('%Y-%m-%d')}.csv",
    )
    parser.add_argument("--no-discord", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = asyncio.run(
        run(days=args.days, output_path=args.output, send_discord=not args.no_discord)
    )
    print(
        f"coverage report generated dead={len(result.dead_channels)} "
        f"degraded={len(result.degraded_channels)} draft={len(result.draft_channels)} "
        f"output={result.output_path or '-'}"
    )
