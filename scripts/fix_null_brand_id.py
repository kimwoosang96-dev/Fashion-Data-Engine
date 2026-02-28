"""
brand_id가 NULL인 products를 채널 기반으로 재매핑.

정책:
- channel_type='brand-store' 채널만 사용
- 채널명 정규화 == 브랜드 name/slug 정규화 일치 시 매핑
- 슬러그 매칭 보강: 채널명을 slug 형태로 변환 후 brands.slug 비교
- 기본 dry-run, --apply일 때 UPDATE 실행

사용법:
  uv run python scripts/fix_null_brand_id.py --dry-run
  uv run python scripts/fix_null_brand_id.py --apply
  DATABASE_URL=postgresql+asyncpg://... uv run python scripts/fix_null_brand_id.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sqlalchemy import text  # noqa: E402

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="brand_id NULL 제품 채널기반 재매핑")
    parser.add_argument("--apply", action="store_true", help="실제 업데이트 적용")
    parser.add_argument("--dry-run", action="store_true", help="미리보기 전용 (기본)")
    parser.add_argument("--limit", type=int, default=0, help="brand-store 채널 제한 (테스트용)")
    return parser.parse_args()


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9가-힣]+", "", value.lower()).strip()


def slugify_simple(value: str | None) -> str:
    if not value:
        return ""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug


async def run(apply: bool, limit: int) -> int:
    await init_db()

    async with AsyncSessionLocal() as db:
        brand_rows = (
            await db.execute(text("SELECT id, name, slug FROM brands"))
        ).all()

        brand_link_counts = {
            int(row[0]): int(row[1] or 0)
            for row in (
                await db.execute(text(
                    """
                    SELECT b.id, COUNT(cb.channel_id) AS link_count
                    FROM brands b
                    LEFT JOIN channel_brands cb ON cb.brand_id = b.id
                    GROUP BY b.id
                    """
                ))
            ).all()
        }

        name_index: dict[str, list[int]] = defaultdict(list)
        slug_index: dict[str, list[int]] = defaultdict(list)

        for brand_id, name, slug in brand_rows:
            brand_id = int(brand_id)
            name_key = normalize_name(name)
            if name_key:
                name_index[name_key].append(brand_id)

            slug_norm = normalize_name(slug)
            if slug_norm:
                name_index[slug_norm].append(brand_id)

            if slug:
                slug_index[str(slug).lower()].append(brand_id)

            slug_from_name = slugify_simple(name)
            if slug_from_name:
                slug_index[slug_from_name].append(brand_id)

        channel_sql = """
            SELECT id, name
            FROM channels
            WHERE is_active = true AND channel_type = 'brand-store'
            ORDER BY id
        """
        if limit > 0:
            channel_sql += " LIMIT :limit"
            channels = (await db.execute(text(channel_sql), {"limit": limit})).all()
        else:
            channels = (await db.execute(text(channel_sql))).all()

        channel_to_brand: dict[int, int] = {}
        channel_match_type: dict[int, str] = {}
        ambiguous_channels: list[tuple[int, str, list[int], str]] = []
        auto_resolved_ambiguous: list[tuple[int, str, int, str]] = []

        name_match_count = 0
        slug_match_count = 0

        for channel_id_raw, channel_name_raw in channels:
            channel_id = int(channel_id_raw)
            channel_name = str(channel_name_raw or "")

            name_key = normalize_name(channel_name)
            slug_key = slugify_simple(channel_name)

            name_candidates = sorted(set(name_index.get(name_key, []))) if name_key else []
            slug_candidates = sorted(set(slug_index.get(slug_key, []))) if slug_key else []

            if len(name_candidates) == 1:
                chosen = name_candidates[0]
                channel_to_brand[channel_id] = chosen
                channel_match_type[channel_id] = "name_match"
                name_match_count += 1
                continue

            if len(name_candidates) > 1:
                linked = [bid for bid in name_candidates if brand_link_counts.get(bid, 0) > 0]
                if len(linked) == 1:
                    chosen = linked[0]
                    channel_to_brand[channel_id] = chosen
                    channel_match_type[channel_id] = "name_match"
                    auto_resolved_ambiguous.append((channel_id, channel_name, chosen, "name_match"))
                    name_match_count += 1
                else:
                    ambiguous_channels.append((channel_id, channel_name, name_candidates, "name_match"))
                continue

            # name 매칭 실패 시 slug 매칭 시도
            if len(slug_candidates) == 1:
                chosen = slug_candidates[0]
                channel_to_brand[channel_id] = chosen
                channel_match_type[channel_id] = "slug_match"
                slug_match_count += 1
                continue

            if len(slug_candidates) > 1:
                linked = [bid for bid in slug_candidates if brand_link_counts.get(bid, 0) > 0]
                if len(linked) == 1:
                    chosen = linked[0]
                    channel_to_brand[channel_id] = chosen
                    channel_match_type[channel_id] = "slug_match"
                    auto_resolved_ambiguous.append((channel_id, channel_name, chosen, "slug_match"))
                    slug_match_count += 1
                else:
                    ambiguous_channels.append((channel_id, channel_name, slug_candidates, "slug_match"))

        null_rows = (
            await db.execute(text("SELECT id, channel_id FROM products WHERE brand_id IS NULL"))
        ).all()

        updates: list[tuple[int, int, str]] = []
        unmatched = 0
        for product_id_raw, channel_id_raw in null_rows:
            product_id = int(product_id_raw)
            channel_id = int(channel_id_raw)
            brand_id = channel_to_brand.get(channel_id)
            if brand_id:
                updates.append((brand_id, product_id, channel_match_type.get(channel_id, "unknown")))
            else:
                unmatched += 1

        print(
            f"mode={'apply' if apply else 'dry-run'} "
            f"brand_store_channels={len(channels)} matched_pairs={len(channel_to_brand)} "
            f"name_match={name_match_count} slug_match={slug_match_count} "
            f"ambiguous_channels={len(ambiguous_channels)} auto_resolved_ambiguous={len(auto_resolved_ambiguous)} "
            f"null_products={len(null_rows)} remap_candidates={len(updates)} unmatched={unmatched}"
        )

        if auto_resolved_ambiguous:
            print("\n[AUTO-RESOLVED AMBIGUOUS CHANNELS]")
            for channel_id, channel_name, chosen, match_type in auto_resolved_ambiguous[:30]:
                print(f"channel_id={channel_id} name={channel_name} -> brand_id={chosen} ({match_type})")

        if ambiguous_channels:
            print("\n[AMBIGUOUS CHANNELS]")
            for channel_id, channel_name, brand_ids, match_type in ambiguous_channels[:30]:
                print(f"channel_id={channel_id} name={channel_name} brand_ids={brand_ids} ({match_type})")

        if updates:
            print("\n[샘플 매핑 20건]")
            for brand_id, product_id, match_type in updates[:20]:
                print(f"product_id={product_id} -> brand_id={brand_id} ({match_type})")

        if apply and updates:
            batch_size = 500
            total = len(updates)
            updated = 0
            for i in range(0, total, batch_size):
                batch = updates[i : i + batch_size]
                for brand_id, product_id, _ in batch:
                    await db.execute(
                        text("UPDATE products SET brand_id=:bid, updated_at=CURRENT_TIMESTAMP WHERE id=:pid"),
                        {"bid": brand_id, "pid": product_id},
                    )
                await db.commit()
                updated += len(batch)
                print(f"  커밋 {updated}/{total}")
            print(f"\nupdated={updated}")
        elif apply:
            print("\nNothing to update.")

    return 0


if __name__ == "__main__":
    args = parse_args()
    apply_mode = bool(args.apply and not args.dry_run)
    raise SystemExit(asyncio.run(run(apply=apply_mode, limit=args.limit)))
