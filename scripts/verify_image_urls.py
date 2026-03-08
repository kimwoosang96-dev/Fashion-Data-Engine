from __future__ import annotations

import argparse
import asyncio
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.product import Product  # noqa: E402

SEM = asyncio.Semaphore(50)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify product image URLs.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--refetch-broken", action="store_true")
    return parser.parse_args()


async def _check_url(client: httpx.AsyncClient, url: str) -> bool:
    async with SEM:
        try:
            response = await client.head(url, timeout=5)
            if response.status_code == 405:
                response = await client.get(url, timeout=5, follow_redirects=True)
            return response.status_code < 400
        except Exception:
            return False


async def run(*, apply: bool, limit: int, refetch_broken: bool) -> int:
    await init_db()
    cutoff = datetime.utcnow() - timedelta(days=30)
    async with AsyncSessionLocal() as db:
        products = (
            await db.execute(
                select(Product)
                .where(
                    Product.image_url.is_not(None),
                    ((Product.image_verified_at.is_(None)) | (Product.image_verified_at < cutoff)),
                )
                .order_by(Product.id.asc())
                .limit(limit)
            )
        ).scalars().all()

        broken_by_channel: dict[int, int] = defaultdict(int)
        async with httpx.AsyncClient(follow_redirects=True) as client:
            results = await asyncio.gather(*[_check_url(client, product.image_url) for product in products])

        broken = 0
        now = datetime.utcnow()
        for product, ok in zip(products, results, strict=False):
            if ok:
                if apply:
                    product.image_verified_at = now
                continue
            broken += 1
            broken_by_channel[product.channel_id] += 1
            if apply:
                product.image_url = None
                product.image_verified_at = now

        if apply:
            await db.commit()

    print(f"verify_image_urls scanned={len(products)} broken={broken} apply={apply}")
    if refetch_broken:
        targets = [channel_id for channel_id, count in broken_by_channel.items() if count >= 5]
        print(f"refetch_channel_ids={targets}")
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(
        asyncio.run(
            run(
                apply=bool(args.apply),
                limit=args.limit,
                refetch_broken=bool(args.refetch_broken),
            )
        )
    )
