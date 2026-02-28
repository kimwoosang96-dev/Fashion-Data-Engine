"""
브랜드 인리치먼트 CSV를 기반으로 brands 테이블 업데이트.

사용법:
  uv run python scripts/enrich_brands.py --csv data/brand_enrichment.csv --dry-run
  uv run python scripts/enrich_brands.py --csv data/brand_enrichment.csv --apply
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.brand import Brand  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="브랜드 인리치먼트 적용")
    parser.add_argument("--csv", dest="csv_path", default="data/brand_enrichment.csv")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


async def run(csv_path: Path, apply: bool) -> int:
    if not csv_path.exists():
        print(f"[ERROR] 파일이 없습니다: {csv_path}")
        return 1

    await init_db()

    updated = 0
    missing = 0
    total = 0

    async with AsyncSessionLocal() as db:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for line_no, row in enumerate(reader, start=2):
                total += 1
                slug = clean(row.get("slug"))
                if not slug:
                    print(f"[SKIP] line {line_no}: slug 누락")
                    continue

                brand = (
                    await db.execute(select(Brand).where(Brand.slug == slug))
                ).scalar_one_or_none()
                if not brand:
                    missing += 1
                    print(f"[SKIP] line {line_no}: slug 미존재 ({slug})")
                    continue

                brand.origin_country = clean(row.get("origin_country"))
                brand.official_url = clean(row.get("official_url"))
                brand.instagram_url = clean(row.get("instagram_url"))
                brand.description_ko = clean(row.get("description_ko"))
                updated += 1

        if apply:
            await db.commit()
        else:
            await db.rollback()

    mode = "APPLY" if apply else "DRY-RUN"
    print(f"[{mode}] total={total} updated={updated} missing={missing}")
    return 0


async def main() -> int:
    args = parse_args()
    apply = bool(args.apply and not args.dry_run)
    return await run(Path(args.csv_path), apply=apply)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
