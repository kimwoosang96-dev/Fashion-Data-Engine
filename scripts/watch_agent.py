from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.activity_feed import ActivityFeed  # noqa: E402
from fashion_engine.models.brand import Brand  # noqa: E402
from fashion_engine.models.channel import Channel  # noqa: E402
from fashion_engine.models.crawl_run import CrawlRun  # noqa: E402
from fashion_engine.models.price_history import PriceHistory  # noqa: E402
from fashion_engine.models.product import Product  # noqa: E402


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
    ) -> int:
        inserted = 0
        for item in candidates:
            if await self._event_exists(
                db,
                event_type=item.event_type,
                product_id=item.product_id,
                channel_id=item.channel_id,
                started_at=started_at,
            ):
                continue
            db.add(
                ActivityFeed(
                    event_type=item.event_type,
                    product_id=item.product_id,
                    channel_id=item.channel_id,
                    brand_id=item.brand_id,
                    product_name=item.product_name,
                    price_krw=item.price_krw,
                    discount_rate=item.discount_rate,
                    source_url=item.source_url,
                    metadata_json={"image_url": item.image_url} if item.image_url else None,
                    detected_at=item.detected_at,
                    notified=False,
                )
            )
            inserted += 1
        return inserted

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
            )
            for row in rows
        ]

    async def detect_price_cut(
        self,
        db: AsyncSession,
        *,
        channel_id: int,
        started_at: datetime,
    ) -> list[FeedEventCandidate]:
        ranked = (
            select(
                PriceHistory.product_id.label("product_id"),
                PriceHistory.price.label("price_krw"),
                PriceHistory.crawled_at.label("crawled_at"),
                func.row_number()
                .over(
                    partition_by=PriceHistory.product_id,
                    order_by=PriceHistory.crawled_at.desc(),
                )
                .label("rn"),
            )
            .join(Product, Product.id == PriceHistory.product_id)
            .where(
                Product.channel_id == channel_id,
                Product.price_updated_at.is_not(None),
                Product.price_updated_at >= started_at,
            )
            .subquery()
        )
        latest = aliased(ranked)
        prev = aliased(ranked)
        rows = (
            await db.execute(
                select(
                    Product.id,
                    Product.brand_id,
                    Product.name,
                    Product.url,
                    Product.image_url,
                    Product.discount_rate,
                    latest.c.price_krw.label("latest_price"),
                    prev.c.price_krw.label("prev_price"),
                    latest.c.crawled_at.label("detected_at"),
                )
                .join(latest, latest.c.product_id == Product.id)
                .join(prev, prev.c.product_id == Product.id)
                .where(
                    Product.channel_id == channel_id,
                    latest.c.rn == 1,
                    prev.c.rn == 2,
                    prev.c.price_krw.is_not(None),
                    latest.c.price_krw.is_not(None),
                    prev.c.price_krw > latest.c.price_krw,
                    ((prev.c.price_krw - latest.c.price_krw) * 100.0 / prev.c.price_krw) >= 10.0,
                )
                .order_by(latest.c.crawled_at.desc(), Product.id.desc())
            )
        ).all()
        return [
            FeedEventCandidate(
                event_type="price_cut",
                product_id=row.id,
                channel_id=channel_id,
                brand_id=row.brand_id,
                product_name=row.name,
                price_krw=int(row.latest_price) if row.latest_price is not None else None,
                discount_rate=row.discount_rate,
                source_url=row.url,
                image_url=row.image_url,
                detected_at=row.detected_at or started_at,
            )
            for row in rows
        ]

    async def run(self, db: AsyncSession, *, channel_id: int, crawl_run_id: int) -> int:
        crawl_run = await db.get(CrawlRun, crawl_run_id)
        if not crawl_run:
            return 0
        started_at = crawl_run.started_at

        candidates: list[FeedEventCandidate] = []
        candidates.extend(await self.detect_sale_start(db, channel_id=channel_id, started_at=started_at))
        candidates.extend(await self.detect_new_drops(db, channel_id=channel_id, started_at=started_at))
        candidates.extend(await self.detect_price_cut(db, channel_id=channel_id, started_at=started_at))
        inserted = await self._insert_candidates(db, started_at=started_at, candidates=candidates)
        return inserted


async def run_channel_watch(channel_id: int, crawl_run_id: int) -> int:
    await init_db()
    async with AsyncSessionLocal() as db:
        agent = WatchAgent()
        inserted = await agent.run(db, channel_id=channel_id, crawl_run_id=crawl_run_id)
        await db.commit()
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
