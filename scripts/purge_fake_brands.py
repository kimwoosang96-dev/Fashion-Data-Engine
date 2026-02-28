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
import asyncio
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sqlalchemy import bindparam, text  # noqa: E402

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402

KO_CATEGORY_KEYWORDS = [
    "티셔츠", "셔츠", "자켓", "팬츠", "후디", "스니커즈", "양말",
    "아이웨어", "크로스백", "숄더백", "토트백", "파우치백", "백팩",
    "슬리브", "스웨트셔츠", "스웻셔츠",
]
KO_CATEGORY_EXACT = {
    "상의", "하의", "아우터", "신발", "가방", "모자", "주얼리", "벨트",
    "악세사리", "액세서리", "신상품", "온라인샵", "라이프스타일", "슈케어",
    "개인결제창", "세일", "셔츠", "후디",
}
EN_CATEGORY_EXACT = {
    "top", "tops", "bottom", "bottoms", "outer", "outerwear",
    "shoes", "shoe", "bag", "bags", "hat", "hats",
    "accessory", "accessories", "sale", "new", "archive",
    "jackets", "jacket", "pants", "shirt", "shirts", "sneakers",
    "t-shirt", "underwear", "hoodies & sweats", "cap & hats",
    "shirts & blouse", "long pants", "short pants", "home fragrance",
    "non-sale", "all sale",
}
NEW_IN_RE = re.compile(r"(新入荷|xin\s*ru\s*he|new\s*arrival)", re.I)
DISCOUNT_RE = re.compile(r"(?i)(?:[-\s]?\d{1,3}%|season\s*off|sale)$")
PRODUCT_RE = re.compile(r"(?i)\b(t-?shirt|tee|pants|jacket|hoodie|sweatshirt|long\s*sleeves?)\b")


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9가-힣]+", "", (text or "").lower()).strip()


def classify_fake(brand_id: int, name: str, slug: str) -> str | None:
    n_name = normalize(name)
    n_slug = normalize(slug)
    name_lower = name.lower().strip()
    joined = f"{name} {slug}".lower()

    # 한국어 카테고리 키워드 포함
    if any(kw in name for kw in KO_CATEGORY_KEYWORDS):
        return "korean_category"
    if n_name in KO_CATEGORY_EXACT or n_slug in KO_CATEGORY_EXACT:
        return "korean_category"

    # 영문 카테고리 exact
    if name_lower in EN_CATEGORY_EXACT or n_slug in EN_CATEGORY_EXACT:
        return "english_category"

    # 新入荷 접미사
    if NEW_IN_RE.search(name) or NEW_IN_RE.search(slug):
        return "new_arrival_duplicate"

    # 할인율 접미사
    if DISCOUNT_RE.search(name) or DISCOUNT_RE.search(slug):
        return "discount_suffix"

    # 특정 제품명 패턴
    if PRODUCT_RE.search(joined) and len(name) >= 16:
        return "product_like"

    return None


async def run(apply: bool) -> int:
    await init_db()

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(text("SELECT id, name, slug FROM brands"))).fetchall()

    targets: list[tuple[int, str, str, str]] = []
    for brand_id, name, slug in rows:
        reason = classify_fake(brand_id, name or "", slug or "")
        if reason:
            targets.append((brand_id, name, slug, reason))

    by_reason = Counter(reason for _, _, _, reason in targets)
    print(f"mode={'apply' if apply else 'dry-run'} total_brands={len(rows)} fake_candidates={len(targets)}")
    for key, count in sorted(by_reason.items()):
        print(f"  - {key}: {count}")

    for row in targets[:120]:
        print(f"    id={row[0]} name={row[1]} reason={row[3]}")

    if not apply:
        return 0

    ids = [row[0] for row in targets]
    if not ids:
        print("no-op: 삭제 대상 없음")
        return 0

    async with AsyncSessionLocal() as db:
        bp = bindparam("ids", expanding=True)

        result = await db.execute(
            text("UPDATE products SET brand_id=NULL WHERE brand_id IN :ids").bindparams(bp),
            {"ids": ids},
        )
        products_null = result.rowcount

        result2 = await db.execute(
            text("DELETE FROM channel_brands WHERE brand_id IN :ids").bindparams(bp),
            {"ids": ids},
        )
        links_deleted = result2.rowcount

        result3 = await db.execute(
            text("DELETE FROM brands WHERE id IN :ids").bindparams(bp),
            {"ids": ids},
        )
        brands_deleted = result3.rowcount

        await db.commit()

    print(
        f"[APPLY] brands_deleted={brands_deleted} "
        f"channel_brands_deleted={links_deleted} products_brand_id_null={products_null}"
    )
    return 0


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    apply = bool(args.apply and not args.dry_run)
    return await run(apply=apply)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
