"""
브랜드 데이터 MECE 정제 스크립트.

정책:
- dry-run이 기본이며, --apply일 때만 실제 정제 수행
- suspicion=high 항목을 출력
- apply는 안전 삭제 대상(mixed_conflict_safe_delete)에만 적용

사용법:
  .venv/bin/python scripts/fix_brand_mece.py
  .venv/bin/python scripts/fix_brand_mece.py --apply
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


def domain_norm(url: str | None) -> str:
    if not url:
        return ""
    host = re.sub(r"^https?://", "", url.strip().lower()).split("/")[0]
    host = host.removeprefix("www.")
    host = host.split(":")[0]
    return normalize(host)


def main(apply: bool) -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"DB not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    channels = cur.execute(
        """
        SELECT id, name, url, channel_type
        FROM channels
        WHERE is_active = 1
        """
    ).fetchall()
    brands = cur.execute(
        """
        SELECT id, name, slug, official_url
        FROM brands
        """
    ).fetchall()

    blocked = set()
    own_brand_markers = set()
    for _, name, url, channel_type in channels:
        n_name = normalize(name)
        n_domain = domain_norm(url)
        if channel_type == "edit-shop":
            blocked.add(n_name)
            blocked.add(n_domain)
        if channel_type in ("brand-store", "official"):
            own_brand_markers.add(n_name)
            own_brand_markers.add(n_domain)

    duplicate_by_key: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for brand_id, name, slug, _ in brands:
        key = normalize(slug)
        if key:
            duplicate_by_key[key].append((brand_id, name, slug))

    high_items: list[dict] = []
    safe_delete_ids: list[int] = []

    for brand_id, name, slug, official_url in brands:
        name_key = normalize(name)
        slug_key = normalize(slug)
        has_own_page = bool(official_url) or name_key in own_brand_markers or slug_key in own_brand_markers
        linked_channels = cur.execute(
            "SELECT COUNT(DISTINCT channel_id) FROM channel_brands WHERE brand_id=?",
            (brand_id,),
        ).fetchone()[0]
        product_refs = cur.execute(
            "SELECT COUNT(*) FROM products WHERE brand_id=?",
            (brand_id,),
        ).fetchone()[0]

        if (name_key in blocked or slug_key in blocked) and not has_own_page:
            reason = "edit-shop 채널명/도메인과 브랜드 식별자 충돌"
            item = {
                "brand_id": brand_id,
                "name": name,
                "slug": slug,
                "issue": "mixed_conflict",
                "suspicion": "high",
                "linked_channels": linked_channels,
                "product_refs": product_refs,
                "reason": reason,
            }
            if linked_channels <= 1 and product_refs == 0:
                item["issue"] = "mixed_conflict_safe_delete"
                safe_delete_ids.append(brand_id)
            high_items.append(item)

    for key, group in duplicate_by_key.items():
        if len(group) <= 1:
            continue
        # 완전 중복은 high로만 표시(자동 삭제는 위험하므로 미적용)
        for brand_id, name, slug in group:
            high_items.append(
                {
                    "brand_id": brand_id,
                    "name": name,
                    "slug": slug,
                    "issue": "duplicate_slug_key",
                    "suspicion": "high",
                    "linked_channels": None,
                    "product_refs": None,
                    "reason": f"slug 정규화 키 충돌: {key}",
                }
            )

    # 중복 출력 제거
    uniq = {}
    for item in high_items:
        uniq[(item["brand_id"], item["issue"])] = item
    high_items = sorted(uniq.values(), key=lambda x: (x["issue"], x["name"].lower()))

    print(
        f"mode={'apply' if apply else 'dry-run'} "
        f"suspicion_high={len(high_items)} safe_delete_candidates={len(set(safe_delete_ids))}"
    )
    print("\n[suspicion=high]")
    for item in high_items[:200]:
        print(
            f"id={item['brand_id']} name={item['name']} slug={item['slug']} "
            f"issue={item['issue']} reason={item['reason']}"
        )

    if apply:
        target_ids = sorted(set(safe_delete_ids))
        if target_ids:
            q = ",".join("?" for _ in target_ids)
            cur.execute(f"DELETE FROM channel_brands WHERE brand_id IN ({q})", target_ids)
            cur.execute(f"DELETE FROM brands WHERE id IN ({q})", target_ids)
            conn.commit()
            print(f"\n[applied] deleted_brands={len(target_ids)}")
        else:
            print("\n[applied] 삭제 대상 없음")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="실제 정제 적용")
    args = parser.parse_args()
    main(apply=args.apply)

