"""
누락된 럭셔리 브랜드 기본 시드.

사용법:
  uv run python scripts/seed_brands_luxury.py --dry-run
  uv run python scripts/seed_brands_luxury.py --apply
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.brand import Brand  # noqa: E402


SEED_BRANDS = [
    {
        "slug": "dior",
        "name": "Dior",
        "name_ko": "디올",
        "origin_country": "France",
        "official_url": "https://www.dior.com",
        "instagram_url": "https://www.instagram.com/dior/",
    },
    {
        "slug": "celine",
        "name": "Celine",
        "name_ko": "셀린느",
        "origin_country": "France",
        "official_url": "https://www.celine.com",
        "instagram_url": "https://www.instagram.com/celine/",
    },
    {
        "slug": "burberry",
        "name": "Burberry",
        "name_ko": "버버리",
        "origin_country": "United Kingdom",
        "official_url": "https://www.burberry.com",
        "instagram_url": "https://www.instagram.com/burberry/",
    },
    {
        "slug": "off-white",
        "name": "Off-White",
        "name_ko": "오프화이트",
        "origin_country": "Italy",
        "official_url": "https://www.off---white.com",
        "instagram_url": "https://www.instagram.com/off____white/",
    },
    {
        "slug": "chanel",
        "name": "Chanel",
        "name_ko": "샤넬",
        "origin_country": "France",
        "official_url": "https://www.chanel.com",
        "instagram_url": "https://www.instagram.com/chanelofficial/",
    },
    {
        "slug": "saint-laurent",
        "name": "Saint Laurent",
        "name_ko": "생로랑",
        "origin_country": "France",
        "official_url": "https://www.ysl.com",
        "instagram_url": "https://www.instagram.com/ysl/",
    },
    {
        "slug": "fendi",
        "name": "Fendi",
        "name_ko": "펜디",
        "origin_country": "Italy",
        "official_url": "https://www.fendi.com",
        "instagram_url": "https://www.instagram.com/fendi/",
    },
    {
        "slug": "tom-ford",
        "name": "Tom Ford",
        "name_ko": "톰 포드",
        "origin_country": "United States",
        "official_url": "https://www.tomford.com",
        "instagram_url": "https://www.instagram.com/tomford/",
    },
    {
        "slug": "lanvin",
        "name": "Lanvin",
        "name_ko": "랑방",
        "origin_country": "France",
        "official_url": "https://www.lanvin.com",
        "instagram_url": "https://www.instagram.com/lanvin/",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="누락 럭셔리 브랜드 시드")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


async def run(apply: bool) -> int:
    await init_db()
    created = 0
    updated = 0

    async with AsyncSessionLocal() as db:
        for item in SEED_BRANDS:
            existing = (
                await db.execute(select(Brand).where(Brand.slug == item["slug"]))
            ).scalar_one_or_none()

            if existing:
                existing.name = item["name"]
                existing.name_ko = item["name_ko"]
                existing.origin_country = item["origin_country"]
                existing.official_url = item["official_url"]
                existing.instagram_url = item["instagram_url"]
                updated += 1
            else:
                db.add(
                    Brand(
                        name=item["name"],
                        slug=item["slug"],
                        name_ko=item["name_ko"],
                        origin_country=item["origin_country"],
                        official_url=item["official_url"],
                        instagram_url=item["instagram_url"],
                    )
                )
                created += 1

        if apply:
            await db.commit()
        else:
            await db.rollback()

    mode = "APPLY" if apply else "DRY-RUN"
    print(f"[{mode}] created={created} updated={updated} total={len(SEED_BRANDS)}")
    return 0


async def main() -> int:
    args = parse_args()
    apply = bool(args.apply and not args.dry_run)
    return await run(apply=apply)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
