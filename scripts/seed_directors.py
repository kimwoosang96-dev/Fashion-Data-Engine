"""
브랜드 크리에이티브 디렉터 CSV 시드.

사용법:
  uv run python scripts/seed_directors.py --csv data/brand_directors.csv --dry-run
  uv run python scripts/seed_directors.py --csv data/brand_directors.csv --apply
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from pathlib import Path

from sqlalchemy import and_, select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.brand import Brand  # noqa: E402
from fashion_engine.models.brand_director import BrandDirector  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="브랜드 디렉터 CSV 시드")
    parser.add_argument("--csv", dest="csv_path", default="data/brand_directors.csv")
    parser.add_argument("--dry-run", action="store_true", help="쓰기 없이 검증만 수행")
    parser.add_argument("--apply", action="store_true", help="실제 INSERT 수행")
    return parser.parse_args()


def to_int_or_none(raw: str | None) -> int | None:
    value = (raw or "").strip()
    if not value:
        return None
    return int(value)


async def run(csv_path: Path, apply: bool) -> int:
    if not csv_path.exists():
        print(f"[ERROR] 파일이 없습니다: {csv_path}")
        return 1

    await init_db()

    created = 0
    duplicate = 0
    updated = 0
    missing_brand = 0
    invalid = 0
    total = 0

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Brand.id, Brand.slug))).all()
        slug_to_brand_id = {slug: brand_id for brand_id, slug in rows}

        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for line_no, row in enumerate(reader, start=2):
                total += 1
                brand_slug = (row.get("brand_slug") or "").strip()
                name = (row.get("name") or "").strip()
                role = (row.get("role") or "").strip() or "Creative Director"
                note = (row.get("note") or "").strip() or None
                source_url = (row.get("source_url") or "").strip() or None
                verified_at = (row.get("verified_at") or "").strip() or None

                try:
                    start_year = to_int_or_none(row.get("start_year"))
                    end_year = to_int_or_none(row.get("end_year"))
                except ValueError:
                    print(f"[SKIP] line {line_no}: start_year/end_year 숫자 형식 오류")
                    invalid += 1
                    continue

                if not brand_slug or not name:
                    print(f"[SKIP] line {line_no}: brand_slug/name 필수값 누락")
                    invalid += 1
                    continue

                brand_id = slug_to_brand_id.get(brand_slug)
                if not brand_id:
                    print(f"[SKIP] line {line_no}: 존재하지 않는 브랜드 slug ({brand_slug})")
                    missing_brand += 1
                    continue

                exists = (
                    await db.execute(
                        select(BrandDirector.id).where(
                            and_(
                                BrandDirector.brand_id == brand_id,
                                BrandDirector.name == name,
                                BrandDirector.role == role,
                                BrandDirector.start_year == start_year,
                                BrandDirector.end_year == end_year,
                            )
                        )
                    )
                ).scalar_one_or_none()
                if exists:
                    duplicate += 1
                    continue

                upsert_target = (
                    await db.execute(
                        select(BrandDirector).where(
                            and_(
                                BrandDirector.brand_id == brand_id,
                                BrandDirector.role == role,
                                BrandDirector.start_year == start_year,
                                BrandDirector.end_year == end_year,
                            )
                        )
                    )
                ).scalar_one_or_none()

                combined_note = note
                if source_url or verified_at:
                    meta_parts = []
                    if source_url:
                        meta_parts.append(f"source={source_url}")
                    if verified_at:
                        meta_parts.append(f"verified_at={verified_at}")
                    meta_str = " | ".join(meta_parts)
                    combined_note = f"{note} | {meta_str}" if note else meta_str

                if upsert_target:
                    updated += 1
                    if apply:
                        upsert_target.name = name
                        upsert_target.note = combined_note
                    continue

                created += 1
                if apply:
                    db.add(
                        BrandDirector(
                            brand_id=brand_id,
                            name=name,
                            role=role,
                            start_year=start_year,
                            end_year=end_year,
                            note=combined_note,
                        )
                    )

        if apply:
            await db.commit()

    mode = "APPLY" if apply else "DRY-RUN"
    print(
        f"[{mode}] total={total} created={created} updated={updated} "
        f"duplicate={duplicate} missing_brand={missing_brand} invalid={invalid}"
    )
    return 0


async def main() -> int:
    args = parse_args()
    apply = bool(args.apply and not args.dry_run)
    return await run(Path(args.csv_path), apply=apply)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
