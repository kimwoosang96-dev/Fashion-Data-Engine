"""
기존 products 테이블의 gender/subcategory를 일괄 재분류.

기본은 dry-run이며, --apply 옵션으로 실제 UPDATE를 수행한다.

사용법:
  .venv/bin/python scripts/reclassify_products.py
  .venv/bin/python scripts/reclassify_products.py --dry-run
  .venv/bin/python scripts/reclassify_products.py --apply
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.crawler.product_classifier import classify_gender_and_subcategory


DB_PATH = ROOT / "data" / "fashion.db"


def reclassify(apply: bool) -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"DB not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT id, name, description, gender, subcategory
        FROM products
        ORDER BY id
        """
    ).fetchall()

    changed: list[tuple[str | None, str | None, int]] = []
    gender_changed = 0
    subcat_changed = 0

    for product_id, name, description, prev_gender, prev_subcategory in rows:
        next_gender, next_subcategory = classify_gender_and_subcategory(
            product_type=None,
            title=name or "",
            tags=description or "",
        )
        if next_gender != prev_gender or next_subcategory != prev_subcategory:
            changed.append((next_gender, next_subcategory, product_id))
            if next_gender != prev_gender:
                gender_changed += 1
            if next_subcategory != prev_subcategory:
                subcat_changed += 1

    print(
        f"products={len(rows)} changed={len(changed)} "
        f"gender_changed={gender_changed} subcategory_changed={subcat_changed} "
        f"mode={'apply' if apply else 'dry-run'}"
    )

    if changed:
        print("\n[샘플 변경 20건]")
        for next_gender, next_subcategory, product_id in changed[:20]:
            print(f"id={product_id} -> gender={next_gender} subcategory={next_subcategory}")

    if apply and changed:
        cur.executemany(
            """
            UPDATE products
            SET gender = ?, subcategory = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            changed,
        )
        conn.commit()
        print(f"\nupdated={len(changed)}")

    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="실제 업데이트 적용")
    parser.add_argument("--dry-run", action="store_true", help="미리보기만 수행 (기본값)")
    args = parser.parse_args()

    # 기본 동작은 dry-run
    apply = bool(args.apply)
    reclassify(apply=apply)


if __name__ == "__main__":
    main()

