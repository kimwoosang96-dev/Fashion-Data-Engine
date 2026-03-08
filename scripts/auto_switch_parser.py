from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.channel import Channel  # noqa: E402
from fashion_engine.models.channel_crawl_stat import ChannelCrawlStat  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-enable GPT parser on zero-yield channels.")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


async def run(*, apply: bool) -> int:
    await init_db()
    cutoff = datetime.utcnow() - timedelta(days=7)
    switched = 0

    async with AsyncSessionLocal() as db:
        channels = (
            await db.execute(
                select(Channel).where(Channel.is_active == True)  # noqa: E712
            )
        ).scalars().all()

        for channel in channels:
            stats = (
                await db.execute(
                    select(ChannelCrawlStat)
                    .where(
                        ChannelCrawlStat.channel_id == channel.id,
                        ChannelCrawlStat.crawled_at >= cutoff,
                    )
                    .order_by(ChannelCrawlStat.crawled_at.desc(), ChannelCrawlStat.id.desc())
                    .limit(3)
                )
            ).scalars().all()
            if len(stats) < 3:
                continue
            if any(int(stat.products_found or 0) > 0 for stat in stats):
                continue
            recent_positive = (
                await db.execute(
                    select(ChannelCrawlStat.id)
                    .where(
                        ChannelCrawlStat.channel_id == channel.id,
                        ChannelCrawlStat.crawled_at >= cutoff,
                        ChannelCrawlStat.products_found > 0,
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()
            if recent_positive is not None or channel.use_gpt_parser:
                continue
            if apply:
                channel.use_gpt_parser = True
            switched += 1

        if apply and switched:
            await db.commit()

    print(f"auto_switch_parser switched={switched} apply={apply}")
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(asyncio.run(run(apply=bool(args.apply))))
