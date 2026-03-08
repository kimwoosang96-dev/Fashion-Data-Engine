from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from channel_probe import probe_channel  # noqa: E402
from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.channel import Channel  # noqa: E402
from fashion_engine.services.alert_service import send_channel_reactivated_alert  # noqa: E402
from sqlalchemy import select  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reactivate inactive channels if probe succeeds.")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


async def run(*, limit: int, dry_run: bool) -> int:
    await init_db()
    cutoff = datetime.utcnow() - timedelta(days=7)
    reactivated = 0
    async with AsyncSessionLocal() as db:
        channels = (
            await db.execute(
                select(Channel)
                .where(
                    Channel.is_active == False,  # noqa: E712
                    ((Channel.last_probe_at.is_(None)) | (Channel.last_probe_at < cutoff)),
                )
                .order_by(Channel.updated_at.asc())
                .limit(limit)
            )
        ).scalars().all()

        for channel in channels:
            result = await probe_channel(channel.url, channel.name)
            channel.last_probe_at = datetime.utcnow()
            if result.http_status and result.http_status < 400 and result.platform_detected:
                reactivated += 1
                if not dry_run:
                    channel.is_active = True
                    if result.platform_detected:
                        channel.platform = result.platform_detected
        if not dry_run:
            await db.commit()

    if not dry_run and reactivated:
        await send_channel_reactivated_alert(count=reactivated)
    print(f"reactivate_channels checked={limit} reactivated={reactivated} dry_run={dry_run}")
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(asyncio.run(run(limit=args.limit, dry_run=bool(args.dry_run))))
