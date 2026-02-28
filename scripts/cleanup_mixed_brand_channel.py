"""
브랜드/판매채널 혼재 데이터 정리 스크립트.

기준:
- 브랜드명 정규화 값이 edit-shop 채널명/도메인 정규화 값과 동일
- 단, 브랜드 자체 판매페이지(brand-store/official_url)가 있으면 보존
- 안전 삭제 조건:
  - products에서 해당 brand_id 사용 0건
  - channel_brands 연결 채널 수 <= 1

적용 모드:
- --apply: 안전 삭제 조건 대상만 삭제
- --apply-with-products: 제품 참조가 있어도 아래 3단계로 강제 정리
  1) products.brand_id -> NULL
  2) channel_brands 삭제
  3) brands 삭제

사용법:
  .venv/bin/python scripts/cleanup_mixed_brand_channel.py                        # dry-run
  .venv/bin/python scripts/cleanup_mixed_brand_channel.py --apply                # 안전 삭제만
  .venv/bin/python scripts/cleanup_mixed_brand_channel.py --apply-with-products  # 제품 참조 포함 강제 정리
"""
import argparse
import re
import sqlite3
from pathlib import Path


DB_PATH = Path("data/fashion.db")


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9가-힣]+", "", value.lower()).strip()


def normalize_domain(url: str) -> str:
    host = re.sub(r"^https?://", "", url.strip().lower()).split("/")[0]
    host = host.removeprefix("www.")
    core = host.split(":")[0]
    return normalize_name(core)


def main(apply: bool, apply_with_products: bool) -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"DB not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    edit_shop_channels = cur.execute(
        """
        SELECT id, name, url
        FROM channels
        WHERE is_active = 1 AND channel_type = 'edit-shop'
        """
    ).fetchall()

    blocked = set()
    for _, name, url in edit_shop_channels:
        blocked.add(normalize_name(name))
        blocked.add(normalize_domain(url))

    brand_store_channels = cur.execute(
        """
        SELECT name, url
        FROM channels
        WHERE is_active = 1 AND channel_type = 'brand-store'
        """
    ).fetchall()
    own_brand_norms = set()
    for name, url in brand_store_channels:
        own_brand_norms.add(normalize_name(name))
        own_brand_norms.add(normalize_domain(url))

    brands = cur.execute("SELECT id, name, slug, official_url FROM brands").fetchall()

    suspects = []
    for brand_id, name, slug, official_url in brands:
        n_name = normalize_name(name)
        n_slug = normalize_name(slug)
        if n_name in blocked or n_slug in blocked:
            linked_channels = cur.execute(
                "SELECT COUNT(DISTINCT channel_id) FROM channel_brands WHERE brand_id=?",
                (brand_id,),
            ).fetchone()[0]
            product_refs = cur.execute(
                "SELECT COUNT(*) FROM products WHERE brand_id=?",
                (brand_id,),
            ).fetchone()[0]
            own_page = bool(official_url) or n_name in own_brand_norms or n_slug in own_brand_norms
            own_reason = ""
            if own_page:
                if official_url:
                    own_reason = "official_url"
                elif n_name in own_brand_norms:
                    own_reason = "brand-store-name"
                else:
                    own_reason = "brand-store-domain"
            suspects.append((brand_id, name, slug, linked_channels, product_refs, own_page, own_reason))

    keep = [row for row in suspects if row[5]]

    safe_to_delete = [
        row for row in suspects if not row[5] and row[3] <= 1 and row[4] == 0
    ]
    manual_review = [
        row for row in suspects if row not in safe_to_delete and row not in keep
    ]

    print(
        "suspects="
        f"{len(suspects)} keep={len(keep)} safe_to_delete={len(safe_to_delete)} manual_review={len(manual_review)}"
    )
    if keep:
        print("\n[KEEP: OWN SALES PAGE]")
        for row in keep[:80]:
            print(
                f"id={row[0]} name={row[1]} slug={row[2]} links={row[3]} products={row[4]} reason={row[6]}"
            )
    if safe_to_delete:
        print("\n[SAFE DELETE CANDIDATES]")
        for row in safe_to_delete:
            print(f"id={row[0]} name={row[1]} slug={row[2]} links={row[3]} products={row[4]}")
    if manual_review:
        print("\n[MANUAL REVIEW CANDIDATES]")
        for row in manual_review[:80]:
            print(f"id={row[0]} name={row[1]} slug={row[2]} links={row[3]} products={row[4]}")

    if apply_with_products:
        # keep 대상 제외 + blocked 충돌 전체를 정리 대상으로 사용
        force_delete = [row for row in suspects if not row[5]]
        ids = [row[0] for row in force_delete]
        if ids:
            q_marks = ",".join("?" for _ in ids)
            # 1) products.brand_id -> NULL
            cur.execute(f"UPDATE products SET brand_id=NULL WHERE brand_id IN ({q_marks})", ids)
            products_updated = cur.rowcount
            # 2) channel_brands 삭제
            cur.execute(f"DELETE FROM channel_brands WHERE brand_id IN ({q_marks})", ids)
            links_deleted = cur.rowcount
            # 3) brands 삭제
            cur.execute(f"DELETE FROM brands WHERE id IN ({q_marks})", ids)
            brands_deleted = cur.rowcount
            conn.commit()
            print(
                f"\nApplied with products: brands={brands_deleted} "
                f"channel_brands={links_deleted} products_brand_id_null={products_updated}"
            )
        else:
            print("\nNothing to delete (force mode).")
    elif apply and safe_to_delete:
        ids = [row[0] for row in safe_to_delete]
        q_marks = ",".join("?" for _ in ids)
        cur.execute(f"DELETE FROM channel_brands WHERE brand_id IN ({q_marks})", ids)
        cur.execute(f"DELETE FROM brands WHERE id IN ({q_marks})", ids)
        conn.commit()
        print(f"\nApplied deletion for {len(ids)} brands.")
    elif apply:
        print("\nNothing to delete.")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="실제 삭제 적용")
    parser.add_argument(
        "--apply-with-products",
        action="store_true",
        help="제품 참조가 있어도 products.brand_id NULL 처리 후 삭제 적용",
    )
    args = parser.parse_args()
    main(apply=args.apply, apply_with_products=args.apply_with_products)
