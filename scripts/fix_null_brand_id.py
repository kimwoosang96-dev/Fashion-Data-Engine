"""
brand_id가 NULL인 products를 채널 기반으로 재매핑.

정책:
- channel_type='brand-store' 채널만 사용
- 채널명 정규화 == 브랜드 name/slug 정규화 일치 시 매핑
- 기본 dry-run, --apply일 때 UPDATE 실행

사용법:
  .venv/bin/python scripts/fix_null_brand_id.py
  .venv/bin/python scripts/fix_null_brand_id.py --dry-run
  .venv/bin/python scripts/fix_null_brand_id.py --apply
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

DB_PATH = Path("data/fashion.db")


def normalize(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9가-힣]+", "", value.lower()).strip()


def build_brand_index(cur: sqlite3.Cursor) -> dict[str, list[int]]:
    rows = cur.execute("SELECT id, name, slug FROM brands").fetchall()
    index: dict[str, list[int]] = defaultdict(list)
    for brand_id, name, slug in rows:
        for key in (normalize(name), normalize(slug)):
            if key:
                index[key].append(brand_id)
    return index


def run(apply: bool) -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"DB not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    brand_index = build_brand_index(cur)
    channels = cur.execute(
        """
        SELECT id, name
        FROM channels
        WHERE is_active = 1 AND channel_type = 'brand-store'
        """
    ).fetchall()

    channel_to_brand: dict[int, int] = {}
    ambiguous_channels: list[tuple[int, str, list[int]]] = []
    auto_resolved_ambiguous: list[tuple[int, str, int]] = []

    brand_link_counts = {
        brand_id: link_count
        for brand_id, link_count in cur.execute(
            """
            SELECT b.id, COUNT(cb.channel_id) AS link_count
            FROM brands b
            LEFT JOIN channel_brands cb ON cb.brand_id = b.id
            GROUP BY b.id
            """
        ).fetchall()
    }

    for channel_id, channel_name in channels:
        key = normalize(channel_name)
        brand_ids = sorted(set(brand_index.get(key, [])))
        if len(brand_ids) == 1:
            channel_to_brand[channel_id] = brand_ids[0]
        elif len(brand_ids) > 1:
            # 보수적 자동 해소:
            # channel_brands 링크가 있는 후보가 정확히 1개면 그 후보 채택
            linked_candidates = [bid for bid in brand_ids if brand_link_counts.get(bid, 0) > 0]
            if len(linked_candidates) == 1:
                chosen = linked_candidates[0]
                channel_to_brand[channel_id] = chosen
                auto_resolved_ambiguous.append((channel_id, channel_name, chosen))
            else:
                ambiguous_channels.append((channel_id, channel_name, brand_ids))

    null_rows = cur.execute(
        "SELECT id, channel_id FROM products WHERE brand_id IS NULL"
    ).fetchall()

    updates: list[tuple[int, int]] = []
    unmatched = 0
    for product_id, channel_id in null_rows:
        brand_id = channel_to_brand.get(channel_id)
        if brand_id:
            updates.append((brand_id, product_id))
        else:
            unmatched += 1

    print(
        f"mode={'apply' if apply else 'dry-run'} "
        f"brand_store_channels={len(channels)} matched_pairs={len(channel_to_brand)} "
        f"ambiguous_channels={len(ambiguous_channels)} auto_resolved_ambiguous={len(auto_resolved_ambiguous)} "
        f"null_products={len(null_rows)} remap_candidates={len(updates)} unmatched={unmatched}"
    )

    if auto_resolved_ambiguous:
        print("\n[AUTO-RESOLVED AMBIGUOUS CHANNELS]")
        for channel_id, channel_name, chosen in auto_resolved_ambiguous[:30]:
            print(f"channel_id={channel_id} name={channel_name} -> brand_id={chosen}")

    if ambiguous_channels:
        print("\n[AMBIGUOUS CHANNELS]")
        for channel_id, channel_name, brand_ids in ambiguous_channels[:30]:
            print(f"channel_id={channel_id} name={channel_name} brand_ids={brand_ids}")

    if updates:
        print("\n[샘플 매핑 20건]")
        for brand_id, product_id in updates[:20]:
            print(f"product_id={product_id} -> brand_id={brand_id}")

    if apply and updates:
        cur.executemany(
            "UPDATE products SET brand_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            updates,
        )
        conn.commit()
        print(f"\nupdated={len(updates)}")
    elif apply:
        print("\nNothing to update.")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="실제 업데이트 적용")
    parser.add_argument("--dry-run", action="store_true", help="미리보기 전용 (기본값)")
    args = parser.parse_args()
    run(apply=bool(args.apply))
