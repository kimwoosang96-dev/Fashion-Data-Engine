"""
brand_id NULL 제품을 위한 통합 백필 스크립트.

전략:
1. brand-store 채널 → 채널명으로 브랜드 생성(없으면) + 채널 내 모든 NULL 제품 매핑
2. edit-shop 채널 → product_key prefix(slug)로 브랜드 생성(없으면) + 각 제품 매핑
   단, prefix가 3회 이상 등장한 경우만 브랜드 생성 (노이즈 필터)

사용법:
    # dry-run (미리보기)
    uv run python scripts/backfill_brand_ids.py --dry-run

    # Railway 적용
    DATABASE_URL=postgresql+asyncpg://... uv run python scripts/backfill_brand_ids.py --apply
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

from sqlalchemy import text  # noqa: E402

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _title(slug: str) -> str:
    return slug.replace("-", " ").title()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="brand_id NULL 통합 백필")
    p.add_argument("--apply", action="store_true", help="실제 UPDATE/INSERT 실행")
    p.add_argument("--dry-run", action="store_true", help="미리보기 (기본)")
    p.add_argument("--min-count", type=int, default=3, help="edit-shop prefix 최소 등장 횟수 (기본 3)")
    return p.parse_args()


async def run(*, apply: bool, min_count: int) -> int:
    await init_db()

    async with AsyncSessionLocal() as db:
        # ── 0. 기존 brands slug 셋 ─────────────────────────────────────────
        existing_slugs: dict[str, int] = {
            row[0]: int(row[1])
            for row in (await db.execute(text("SELECT slug, id FROM brands"))).all()
        }
        print(f"기존 브랜드 수: {len(existing_slugs):,}")

        # ── 1. brand-store: 채널명 → 브랜드 생성 + 제품 매핑 ─────────────
        print("\n▶ [brand-store] 채널명 기반 브랜드 매핑")
        bs_channels = (await db.execute(text("""
            SELECT DISTINCT c.id, c.name
            FROM channels c
            JOIN products p ON p.channel_id = c.id
            WHERE c.channel_type = 'brand-store'
              AND p.brand_id IS NULL
            ORDER BY c.name
        """))).all()

        brand_store_pairs: list[tuple[int, str, int | None, bool]] = []
        # (channel_id, channel_name, brand_id, is_new_brand)

        for ch_id, ch_name in bs_channels:
            slug = _slugify(ch_name)
            if slug in existing_slugs:
                brand_id = existing_slugs[slug]
                brand_store_pairs.append((int(ch_id), ch_name, brand_id, False))
            else:
                brand_store_pairs.append((int(ch_id), ch_name, None, True))

        new_bs_brands = [(p[1], _slugify(p[1])) for p in brand_store_pairs if p[3]]
        print(f"  brand-store NULL 채널: {len(bs_channels)}개")
        print(f"  기존 브랜드 매칭: {sum(1 for p in brand_store_pairs if not p[3])}개")
        print(f"  신규 브랜드 생성 필요: {len(new_bs_brands)}개")
        if new_bs_brands[:10]:
            for name, slug in new_bs_brands[:10]:
                print(f"    → slug={slug} name={name}")

        # ── 2. edit-shop: product_key prefix 기반 ──────────────────────────
        print("\n▶ [edit-shop] product_key prefix 기반 브랜드 매핑")

        # 채널 슬러그 셋 (자기참조 필터용)
        channel_slugs: set[str] = {
            row[0] for row in (await db.execute(text(
                "SELECT lower(regexp_replace(name, '[^a-z0-9]+', '-', 'g')) FROM channels"
            ))).all()
        }

        es_rows = (await db.execute(text("""
            SELECT p.id, p.product_key
            FROM products p
            JOIN channels c ON c.id = p.channel_id
            WHERE c.channel_type = 'edit-shop'
              AND p.brand_id IS NULL
              AND p.product_key LIKE '%:%'
        """))).all()

        # 유효하지 않은 prefix 패턴 (시즌코드, 숫자, 채널명 자기참조 등)
        import re as _re
        _INVALID_PREFIX = _re.compile(
            r"^(\d{2,4}(ss|aw|fw|sp|su|fall|spring|summer|winter)?\d*$"  # 시즌/연도 코드
            r"|^\d+$"  # 순수 숫자
            r"|^[a-z]{1,2}$"  # 너무 짧은 슬러그
            r")"
        )

        # prefix 집계
        prefix_counter: Counter[str] = Counter()
        product_prefix: dict[int, str] = {}
        for pid, pkey in es_rows:
            prefix = pkey.split(":")[0].strip().lower()
            if not prefix:
                continue
            # 유효하지 않은 패턴 필터
            if _INVALID_PREFIX.match(prefix):
                continue
            # 채널 자기참조 필터 (채널 슬러그와 동일한 prefix 제외)
            if prefix in channel_slugs:
                continue
            prefix_counter[prefix] += 1
            product_prefix[int(pid)] = prefix

        # min_count 이상 prefix만 브랜드 생성
        valid_prefixes = {
            slug: cnt for slug, cnt in prefix_counter.items()
            if cnt >= min_count
        }
        print(f"  edit-shop NULL 제품: {len(es_rows):,}개")
        print(f"  prefix 종류: {len(prefix_counter):,}개")
        print(f"  ≥{min_count}회 prefix: {len(valid_prefixes):,}개")

        new_es_brands: list[tuple[str, str]] = []  # (name, slug)
        prefix_to_brand_id: dict[str, int] = {}

        for slug, cnt in sorted(valid_prefixes.items(), key=lambda x: -x[1]):
            if slug in existing_slugs:
                prefix_to_brand_id[slug] = existing_slugs[slug]
            else:
                new_es_brands.append((_title(slug), slug))

        print(f"  기존 브랜드 prefix 매칭: {len(prefix_to_brand_id):,}개")
        print(f"  신규 브랜드 생성 필요: {len(new_es_brands):,}개")
        if new_es_brands[:15]:
            for name, slug in new_es_brands[:15]:
                cnt = valid_prefixes[slug]
                print(f"    → slug={slug} name={name} ({cnt}개 제품)")

        # ── 3. 총계 ────────────────────────────────────────────────────────
        total_new_brands = len(new_bs_brands) + len(new_es_brands)
        print(f"\n총 신규 브랜드 생성: {total_new_brands}개")

        bs_product_count = (await db.execute(text("""
            SELECT COUNT(*) FROM products p JOIN channels c ON c.id=p.channel_id
            WHERE p.brand_id IS NULL AND c.channel_type = 'brand-store'
        """))).scalar()
        es_product_count = len([pid for pid, slug in product_prefix.items()
                                 if slug in valid_prefixes])
        print(f"brand_id 복원 예상: brand-store {bs_product_count:,}개 + edit-shop ~{es_product_count:,}개")

        if not apply:
            print("\n[DRY-RUN] --apply 플래그 없이는 실제 변경 없음")
            return 0

        # ── 4. 신규 브랜드 INSERT ──────────────────────────────────────────
        print("\n▶ 브랜드 INSERT 중...")
        all_new_brands = new_bs_brands + new_es_brands
        inserted_brands = 0
        for name, slug in all_new_brands:
            # 이미 있으면 스킵 (race condition 방지)
            exists = (await db.execute(
                text("SELECT id FROM brands WHERE slug = :s"), {"s": slug}
            )).first()
            if exists:
                existing_slugs[slug] = int(exists[0])
                continue
            result = await db.execute(
                text("""
                    INSERT INTO brands (name, slug, tier, created_at)
                    VALUES (:n, :s, 'unknown', NOW())
                    RETURNING id
                """),
                {"n": name, "s": slug},
            )
            new_id = result.scalar_one()
            existing_slugs[slug] = new_id
            inserted_brands += 1

        await db.commit()
        print(f"  브랜드 INSERT 완료: {inserted_brands}개")

        # prefix_to_brand_id 업데이트 (새로 생성된 브랜드 포함)
        for slug in valid_prefixes:
            if slug in existing_slugs:
                prefix_to_brand_id[slug] = existing_slugs[slug]

        # brand_store_pairs brand_id 업데이트
        brand_store_pairs_final: list[tuple[int, int]] = []  # (product_channel_id, brand_id)
        for ch_id, ch_name, old_brand_id, is_new in brand_store_pairs:
            slug = _slugify(ch_name)
            brand_id = existing_slugs.get(slug) or old_brand_id
            if brand_id:
                brand_store_pairs_final.append((ch_id, brand_id))

        # ── 5. brand-store 제품 UPDATE ─────────────────────────────────────
        print("\n▶ [brand-store] 제품 brand_id UPDATE 중...")
        bs_updated = 0
        for ch_id, brand_id in brand_store_pairs_final:
            result = await db.execute(
                text("""
                    UPDATE products SET brand_id = :bid, updated_at = NOW()
                    WHERE channel_id = :cid AND brand_id IS NULL
                """),
                {"bid": brand_id, "cid": ch_id},
            )
            bs_updated += result.rowcount
        await db.commit()
        print(f"  완료: {bs_updated:,}개 제품 업데이트")

        # ── 6. edit-shop 제품 UPDATE ───────────────────────────────────────
        print("\n▶ [edit-shop] 제품 brand_id UPDATE 중...")
        batch_size = 500
        es_pairs = [
            (prefix_to_brand_id[slug], pid)
            for pid, slug in product_prefix.items()
            if slug in prefix_to_brand_id
        ]
        es_updated = 0
        for i in range(0, len(es_pairs), batch_size):
            batch = es_pairs[i : i + batch_size]
            for brand_id, pid in batch:
                await db.execute(
                    text("UPDATE products SET brand_id = :bid, updated_at = NOW() WHERE id = :pid AND brand_id IS NULL"),
                    {"bid": brand_id, "pid": pid},
                )
            await db.commit()
            es_updated += len(batch)
            print(f"  {es_updated:,}/{len(es_pairs):,}", end="\r")

        print(f"\n  완료: {es_updated:,}개 제품 업데이트")

        # ── 7. 결과 요약 ───────────────────────────────────────────────────
        remaining = (await db.execute(
            text("SELECT COUNT(*) FROM products WHERE brand_id IS NULL")
        )).scalar()
        print(f"\n✅ 백필 완료!")
        print(f"   브랜드 신규 생성: {inserted_brands}개")
        print(f"   brand-store 복원: {bs_updated:,}개")
        print(f"   edit-shop 복원: {es_updated:,}개")
        print(f"   잔여 NULL brand_id: {remaining:,}개")

    return 0


if __name__ == "__main__":
    args = parse_args()
    apply = bool(args.apply and not args.dry_run)
    raise SystemExit(asyncio.run(run(apply=apply, min_count=args.min_count)))
