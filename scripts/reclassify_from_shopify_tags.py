from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.crawler.product_classifier import classify_gender_and_subcategory  # noqa: E402
from fashion_engine.crawler.product_crawler import ProductCrawler  # noqa: E402
from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.product import Product  # noqa: E402
from fashion_engine.models.channel import Channel  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reclassify Shopify products from tags.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=1000)
    return parser.parse_args()


def _parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(item) for item in value]
    except Exception:
        return []
    return []


async def run(*, apply: bool, limit: int) -> int:
    await init_db()
    updated = 0
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(Product, Channel.platform)
                .join(Channel, Channel.id == Product.channel_id)
                .where(Channel.platform == "shopify")
                .limit(limit)
            )
        ).all()
        for product, _platform in rows:
            tags_list = _parse_tags(product.tags)
            gender, subcategory = classify_gender_and_subcategory(
                product_type=None,
                title=product.name,
                tags=", ".join(tags_list),
            )
            inferred_gender, inferred_subcategory, inferred_is_new = ProductCrawler._infer_shopify_metadata(
                title=product.name,
                product_type=None,
                tags=tags_list,
                collection_hints=[],
            )
            next_gender = gender or inferred_gender
            next_subcategory = subcategory or inferred_subcategory
            if not next_gender and not next_subcategory and not inferred_is_new:
                continue
            updated += 1
            if apply:
                if next_gender:
                    product.gender = next_gender
                if next_subcategory:
                    product.subcategory = next_subcategory
                if inferred_is_new:
                    product.is_new = True
        if apply:
            await db.commit()
    print(f"reclassify_from_shopify_tags updated={updated} apply={apply}")
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(asyncio.run(run(apply=bool(args.apply), limit=args.limit)))
