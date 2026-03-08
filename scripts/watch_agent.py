from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.activity_feed import ActivityFeed  # noqa: E402
from fashion_engine.models.brand import Brand  # noqa: E402
from fashion_engine.models.channel import Channel  # noqa: E402
from fashion_engine.models.crawl_run import CrawlRun  # noqa: E402
from fashion_engine.models.product import Product  # noqa: E402
from fashion_engine.services.push_service import send_push_for_feed_items  # noqa: E402
from fashion_engine.services.realtime_client import broadcast_feed_item  # noqa: E402


@dataclass
class FeedEventCandidate:
    event_type: str
    product_id: int
    channel_id: int
    brand_id: int | None
    product_name: str | None
    price_krw: int | None
    discount_rate: int | None
    source_url: str | None
    image_url: str | None
    detected_at: datetime
    metadata_json: dict | None = None


class WatchAgent:
    async def _event_exists(
        self,
        db: AsyncSession,
        *,
        event_type: str,
        product_id: int,
        channel_id: int,
        started_at: datetime,
    ) -> bool:
        existing = await db.execute(
            select(ActivityFeed.id).where(
                ActivityFeed.event_type == event_type,
                ActivityFeed.product_id == product_id,
                ActivityFeed.channel_id == channel_id,
                ActivityFeed.detected_at >= started_at,
            )
        )
        return existing.scalar_one_or_none() is not None

    async def _insert_candidates(
        self,
        db: AsyncSession,
        *,
        started_at: datetime,
        candidates: list[FeedEventCandidate],
    ) -> tuple[int, list[ActivityFeed]]:
        inserted = 0
        created_rows: list[ActivityFeed] = []
        for item in candidates:
            if await self._event_exists(
                db,
                event_type=item.event_type,
                product_id=item.product_id,
                channel_id=item.channel_id,
                started_at=started_at,
            ):
                continue
            row = ActivityFeed(
                event_type=item.event_type,
                product_id=item.product_id,
                channel_id=item.channel_id,
                brand_id=item.brand_id,
                product_name=item.product_name,
                price_krw=item.price_krw,
                discount_rate=item.discount_rate,
                source_url=item.source_url,
                metadata_json=item.metadata_json or ({"image_url": item.image_url} if item.image_url else None),
                detected_at=item.detected_at,
                notified=False,
            )
            db.add(row)
            created_rows.append(row)
            inserted += 1
        return inserted, created_rows

    async def detect_sale_start(
        self,
        db: AsyncSession,
        *,
        channel_id: int,
        started_at: datetime,
    ) -> list[FeedEventCandidate]:
        rows = (
            await db.execute(
                select(Product)
                .where(
                    Product.channel_id == channel_id,
                    Product.is_sale == True,  # noqa: E712
                    Product.sale_started_at.is_not(None),
                    Product.sale_started_at >= started_at,
                )
                .order_by(Product.sale_started_at.desc(), Product.id.desc())
            )
        ).scalars().all()
        return [
            FeedEventCandidate(
                event_type="sale_start",
                product_id=row.id,
                channel_id=channel_id,
                brand_id=row.brand_id,
                product_name=row.name,
                price_krw=row.price_krw,
                discount_rate=row.discount_rate,
                source_url=row.url,
                image_url=row.image_url,
                detected_at=row.sale_started_at or row.updated_at or started_at,
                metadata_json={"image_url": row.image_url} if row.image_url else None,
            )
            for row in rows
        ]

    async def detect_new_drops(
        self,
        db: AsyncSession,
        *,
        channel_id: int,
        started_at: datetime,
    ) -> list[FeedEventCandidate]:
        rows = (
            await db.execute(
                select(Product)
                .where(
                    Product.channel_id == channel_id,
                    Product.created_at >= started_at,
                )
                .order_by(Product.created_at.desc(), Product.id.desc())
            )
        ).scalars().all()
        return [
            FeedEventCandidate(
                event_type="new_drop",
                product_id=row.id,
                channel_id=channel_id,
                brand_id=row.brand_id,
                product_name=row.name,
                price_krw=row.price_krw,
                discount_rate=row.discount_rate,
                source_url=row.url,
                image_url=row.image_url,
                detected_at=row.created_at,
                metadata_json={"image_url": row.image_url} if row.image_url else None,
            )
            for row in rows
        ]

    async def run(self, db: AsyncSession, *, channel_id: int, crawl_run_id: int) -> tuple[int, list[ActivityFeed]]:
        crawl_run = await db.get(CrawlRun, crawl_run_id)
        if not crawl_run:
            return 0, []
        started_at = crawl_run.started_at

        candidates: list[FeedEventCandidate] = []
        candidates.extend(await self.detect_sale_start(db, channel_id=channel_id, started_at=started_at))
        candidates.extend(await self.detect_new_drops(db, channel_id=channel_id, started_at=started_at))
        inserted, created_rows = await self._insert_candidates(db, started_at=started_at, candidates=candidates)
        return inserted, created_rows


async def run_channel_watch(channel_id: int, crawl_run_id: int) -> int:
    await init_db()
    async with AsyncSessionLocal() as db:
        agent = WatchAgent()
        inserted, created_rows = await agent.run(db, channel_id=channel_id, crawl_run_id=crawl_run_id)
        await db.commit()
    if created_rows:
        async with AsyncSessionLocal() as push_db:
            await send_push_for_feed_items(push_db, created_rows)
        for row in created_rows:
            meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
            await broadcast_feed_item(
                {
                    "id": row.id,
                    "event_type": row.event_type,
                    "product_name": row.product_name,
                    "brand_name": None,
                    "channel_name": None,
                    "price_krw": row.price_krw,
                    "discount_rate": row.discount_rate,
                    "source_url": row.source_url,
                    "image_url": meta.get("image_url"),
                    "product_key": None,
                    "detected_at": row.detected_at.isoformat() if row.detected_at else None,
                }
            )
    return inserted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WatchAgent: 크롤 결과 기반 activity_feed 이벤트 생성")
    parser.add_argument("--channel-id", type=int, required=True)
    parser.add_argument("--crawl-run-id", type=int, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    inserted = asyncio.run(run_channel_watch(args.channel_id, args.crawl_run_id))
    print(f"activity_feed inserted={inserted}")
