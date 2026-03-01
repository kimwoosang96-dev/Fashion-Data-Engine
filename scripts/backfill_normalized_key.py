"""
기존 products.normalized_key 백필 스크립트.

기본은 dry-run이며, --apply 시 실제 업데이트를 수행한다.
"""
from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console
from sqlalchemy import func, select
from sqlalchemy.orm import aliased

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db
from fashion_engine.models.brand import Brand
from fashion_engine.models.product import Product
from fashion_engine.crawler.product_crawler import ProductCrawler
from slugify import slugify

app = typer.Typer()
console = Console()


@dataclass
class BackfillStats:
    scanned: int = 0
    candidates: int = 0
    updated: int = 0
    skipped_no_brand: int = 0
    skipped_no_key: int = 0


def _infer_brand_slug(
    product_key: str | None,
    vendor: str | None,
    brand_slug: str | None,
) -> str | None:
    if brand_slug:
        return brand_slug
    if product_key and ":" in product_key:
        left = (product_key.split(":", 1)[0] or "").strip()
        if left and left != "unknown":
            return left
    if vendor:
        s = slugify(vendor)
        if s:
            return s
    return None


def _parse_tags(raw: str | None) -> list:
    if not raw:
        return []
    try:
        loaded = json.loads(raw)
        return loaded if isinstance(loaded, list) else []
    except Exception:
        return []


async def _count_not_null() -> int:
    async with AsyncSessionLocal() as db:
        return int(
            (
                await db.execute(
                    select(func.count(Product.id)).where(Product.normalized_key.is_not(None))
                )
            ).scalar_one()
            or 0
        )


async def _count_confidence_08() -> int:
    async with AsyncSessionLocal() as db:
        return int(
            (
                await db.execute(
                    select(func.count(Product.id)).where(Product.match_confidence == 0.8)
                )
            ).scalar_one()
            or 0
        )


async def run_backfill(apply: bool, limit: int, force: bool) -> BackfillStats:
    stats = BackfillStats()
    last_id = 0
    chunk_size = 1000
    remaining = limit if limit > 0 else None
    brand_alias = aliased(Brand)

    while True:
        fetch_size = chunk_size if remaining is None else min(chunk_size, remaining)
        if fetch_size <= 0:
            break

        async with AsyncSessionLocal() as db:
            rows = (
                await db.execute(
                    select(
                        Product.id,
                        Product.product_key,
                        Product.vendor,
                        Product.sku,
                        Product.name,
                        Product.normalized_key,
                        Product.tags,
                        brand_alias.slug.label("brand_slug"),
                    )
                    .outerjoin(brand_alias, Product.brand_id == brand_alias.id)
                    .where(Product.id > last_id)
                    .order_by(Product.id.asc())
                    .limit(fetch_size)
                )
            ).all()
            if not force:
                rows = [row for row in rows if row.normalized_key is None]

            if not rows:
                break

            for row in rows:
                stats.scanned += 1
                last_id = row.id
                if remaining is not None:
                    remaining -= 1

                inferred_slug = _infer_brand_slug(row.product_key, row.vendor, row.brand_slug)
                if not inferred_slug:
                    stats.skipped_no_brand += 1
                    continue

                normalized_key, confidence = ProductCrawler._build_normalized_key(
                    brand_slug=inferred_slug,
                    sku=row.sku,
                    title=row.name or "",
                    tags=_parse_tags(row.tags),
                )
                if not normalized_key:
                    stats.skipped_no_key += 1
                    continue

                stats.candidates += 1
                if apply:
                    product = await db.get(Product, row.id)
                    if product:
                        product.normalized_key = normalized_key
                        product.match_confidence = confidence
                        stats.updated += 1

                if stats.scanned % 100 == 0:
                    console.print(
                        f"[dim]progress[/dim] scanned={stats.scanned} candidates={stats.candidates} updated={stats.updated}"
                    )

            if apply and stats.updated > 0:
                await db.commit()

    return stats


@app.command()
def cli_main(
    apply: bool = typer.Option(False, "--apply", help="실제 DB 업데이트 실행"),
    limit: int = typer.Option(0, "--limit", min=0, help="처리 상한 (0=전체)"),
    force: bool = typer.Option(False, "--force", help="normalized_key 존재 제품도 강제 재계산"),
):
    asyncio.run(_main(apply=apply, limit=limit, force=force))


async def _main(apply: bool, limit: int, force: bool) -> None:
    await init_db()

    before_count = await _count_not_null()
    before_conf_08 = await _count_confidence_08()
    stats = await run_backfill(apply=apply, limit=limit, force=force)
    after_count = await _count_not_null() if apply else before_count + stats.candidates
    after_conf_08 = await _count_confidence_08() if apply else before_conf_08
    increased = max(0, after_count - before_count)
    increased_conf_08 = max(0, after_conf_08 - before_conf_08)

    mode = "APPLY" if apply else "DRY-RUN"
    console.print(f"[bold blue]normalized_key backfill ({mode})[/bold blue]")
    console.print(f"force={force}")
    console.print(f"scanned={stats.scanned}")
    console.print(f"candidates={stats.candidates}")
    console.print(f"updated={stats.updated}")
    console.print(f"skipped_no_brand={stats.skipped_no_brand}")
    console.print(f"skipped_no_key={stats.skipped_no_key}")
    console.print(f"normalized_key_not_null before={before_count} after={after_count} increased={increased}")
    console.print(
        f"confidence_0.8(tags) before={before_conf_08} after={after_conf_08} increased={increased_conf_08}"
    )
    if not apply:
        console.print("[yellow]dry-run 완료: --apply로 실제 반영하세요.[/yellow]")


if __name__ == "__main__":
    app()
