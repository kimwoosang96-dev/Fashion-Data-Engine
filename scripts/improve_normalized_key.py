from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from slugify import slugify
from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.crawler.product_crawler import ProductCrawler  # noqa: E402
from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.brand import Brand  # noqa: E402
from fashion_engine.models.product import Product  # noqa: E402
from fashion_engine.services.catalog_service import build_catalog_full  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Improve normalized_key quality.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
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
    scanned = 0
    updated = 0
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(Product, Brand.slug)
                .join(Brand, Brand.id == Product.brand_id, isouter=True)
                .where((Product.match_confidence.is_(None)) | (Product.match_confidence < 0.8))
                .order_by(Product.id.asc())
                .limit(limit or 1000000)
            )
        ).all()
        for product, brand_slug in rows:
            inferred_slug = brand_slug or (slugify(product.vendor) if product.vendor else None)
            if not inferred_slug:
                continue
            normalized_key, confidence = ProductCrawler._build_normalized_key(
                brand_slug=inferred_slug,
                sku=product.sku,
                title=product.name,
                tags=_parse_tags(product.tags),
            )
            scanned += 1
            if not normalized_key:
                continue
            if apply:
                product.normalized_key = normalized_key
                product.match_confidence = confidence
            updated += 1
        if apply:
            await db.commit()
            await build_catalog_full(db)
    print(f"improve_normalized_key scanned={scanned} updated={updated} apply={apply}")
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(asyncio.run(run(apply=bool(args.apply), limit=args.limit)))
