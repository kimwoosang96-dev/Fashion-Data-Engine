"""
브랜드 테이블의 가짜 항목 정리 스크립트.

패턴:
- 한국어 카테고리명
- 영문 카테고리명
- 新入荷/신입고 계열 중복
- 할인율/season off 접미사
- 제품명 형태

특수 처리:
- brand_id=1199(Archive) 포함 시 products.brand_id=NULL 처리 후 삭제

사용법:
  uv run python scripts/purge_fake_brands.py --dry-run
  uv run python scripts/purge_fake_brands.py --apply
"""
from __future__ import annotations

import argparse
import re
import sqlite3
from collections import Counter
from pathlib import Path

DB_PATH = Path("data/fashion.db")

KO_CATEGORY = {
    "상의", "하의", "아우터", "신발", "가방", "모자", "주얼리", "벨트",
    "악세사리", "액세서리", "신상품", "온라인샵", "라이프스타일", "슈케어",
    "개인결제창", "세일",
}
EN_CATEGORY = {
    "top", "tops", "bottom", "bottoms", "outer", "outerwear",
    "shoes", "shoe", "bag", "bags", "hat", "hats",
    "accessory", "accessories", "sale", "new", "archive",
}
NEW_IN_RE = re.compile(r"(新入荷|xin\s*ru\s*he|new\s*arrival)", re.I)
DISCOUNT_RE = re.compile(r"(?i)(?:[-\s]?\d{1,3}%|season\s*off|sale)$")
PRODUCT_RE = re.compile(r"(?i)\b(t-?shirt|tee|pants|jacket|hoodie|sweatshirt|long\s*sleeves?)\b")


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9가-힣]+", "", (text or "").lower()).strip()


def classify_fake(brand_id: int, name: str, slug: str) -> str | None:
    if brand_id == 1199:
        return "english_category_archive"

    n_name = normalize(name)
    n_slug = normalize(slug)
    joined = f"{name} {slug}".lower()

    if n_name in KO_CATEGORY or n_slug in KO_CATEGORY:
        return "korean_category"
    if n_name in EN_CATEGORY or n_slug in EN_CATEGORY:
        return "english_category"
    if NEW_IN_RE.search(name) or NEW_IN_RE.search(slug):
        return "new_arrival_duplicate"
    if DISCOUNT_RE.search(name) or DISCOUNT_RE.search(slug):
        return "discount_suffix"
    if PRODUCT_RE.search(joined) and len(name) >= 16:
        return "product_like"
    return None


def run(apply: bool) -> int:
    if not DB_PATH.exists():
        print(f"DB not found: {DB_PATH}")
        return 1

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    brands = cur.execute("SELECT id, name, slug FROM brands").fetchall()
    targets: list[tuple[int, str, str, str]] = []
    for brand_id, name, slug in brands:
        reason = classify_fake(brand_id, name, slug)
        if reason:
            targets.append((brand_id, name, slug, reason))

    by_reason = Counter(reason for _, _, _, reason in targets)
    print(f"mode={'apply' if apply else 'dry-run'} total_brands={len(brands)} fake_candidates={len(targets)}")
    for key, count in sorted(by_reason.items(), key=lambda x: x[0]):
        print(f"- {key}: {count}")

    for row in targets[:120]:
        print(f"id={row[0]} name={row[1]} slug={row[2]} reason={row[3]}")

    if not apply:
        conn.close()
        return 0

    ids = [row[0] for row in targets]
    if not ids:
        print("no-op: 삭제 대상 없음")
        conn.close()
        return 0

    marks = ",".join("?" for _ in ids)
    cur.execute(f"UPDATE products SET brand_id=NULL WHERE brand_id IN ({marks})", ids)
    products_null = cur.rowcount
    cur.execute(f"DELETE FROM channel_brands WHERE brand_id IN ({marks})", ids)
    links_deleted = cur.rowcount
    cur.execute(f"DELETE FROM brands WHERE id IN ({marks})", ids)
    brands_deleted = cur.rowcount
    conn.commit()
    conn.close()

    print(
        f"[APPLY] brands_deleted={brands_deleted} "
        f"channel_brands_deleted={links_deleted} products_brand_id_null={products_null}"
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    apply = bool(args.apply and not args.dry_run)
    raise SystemExit(run(apply=apply))
