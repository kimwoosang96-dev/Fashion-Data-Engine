"""
ProductCatalog 빌드 스크립트.

기본은 dry-run이며, --apply 시 실제 upsert를 수행한다.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sqlalchemy import text  # noqa: E402

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.services.catalog_service import (  # noqa: E402
    build_catalog_full,
    build_catalog_incremental,
    get_last_done_crawl_finished_at,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="product_catalog 빌드")
    p.add_argument("--apply", action="store_true", help="실제 INSERT/UPDATE 수행")
    p.add_argument("--dry-run", action="store_true", help="미리보기만 수행")
    p.add_argument("--batch-size", type=int, default=1000, help="호환 옵션 (현재 내부 일괄 처리)")
    p.add_argument("--since", type=str, default="", help="증분 기준 시각 (ISO8601)")
    p.add_argument(
        "--since-last-crawl",
        action="store_true",
        help="마지막 완료 CrawlRun.finished_at 이후 변경분만 증분 빌드",
    )
    return p.parse_args()


def _parse_since(raw: str) -> datetime | None:
    if not raw.strip():
        return None
    return datetime.fromisoformat(raw.strip())


async def run(*, apply: bool, batch_size: int, since: datetime | None, since_last_crawl: bool) -> int:
    await init_db()

    async with AsyncSessionLocal() as db:
        current = int((await db.execute(text("SELECT COUNT(*) FROM product_catalog"))).scalar() or 0)
        print(f"현재 product_catalog: {current:,}개")

        if since_last_crawl and since is None:
            since = await get_last_done_crawl_finished_at(db)
            if since:
                print(f"증분 기준(last-crawl): {since.isoformat()}")
            else:
                print("완료된 CrawlRun이 없어 전체 빌드로 전환합니다.")

        if not apply:
            if since is None:
                total = int(
                    (
                        await db.execute(
                            text(
                                """
                                SELECT COUNT(*)
                                FROM (
                                  SELECT DISTINCT COALESCE(normalized_key, product_key) AS nkey
                                  FROM products
                                  WHERE COALESCE(normalized_key, product_key) IS NOT NULL
                                ) t
                                """
                            )
                        )
                    ).scalar()
                    or 0
                )
                print(f"[DRY-RUN] 전체 대상 key: {total:,}개")
            else:
                changed = int(
                    (
                        await db.execute(
                            text(
                                """
                                SELECT COUNT(*)
                                FROM (
                                  SELECT DISTINCT COALESCE(normalized_key, product_key) AS nkey
                                  FROM products
                                  WHERE updated_at > :since
                                    AND COALESCE(normalized_key, product_key) IS NOT NULL
                                ) t
                                """
                            ),
                            {"since": since},
                        )
                    ).scalar()
                    or 0
                )
                print(f"[DRY-RUN] 증분 대상 key: {changed:,}개 (since={since.isoformat()})")
            print("변경 없음. --apply를 추가하면 실제 반영합니다.")
            return 0

    if since is None:
        async with AsyncSessionLocal() as db:
            affected = await build_catalog_full(db, batch_size=batch_size)
    else:
        affected = await build_catalog_incremental(since=since, batch_size=batch_size)

    async with AsyncSessionLocal() as db:
        final = int((await db.execute(text("SELECT COUNT(*) FROM product_catalog"))).scalar() or 0)

    mode = "증분" if since is not None else "전체"
    print(f"✅ ProductCatalog {mode} 빌드 완료")
    print(f"   처리 key: {affected:,}개")
    print(f"   최종 catalog: {final:,}개")
    return 0


if __name__ == "__main__":
    args = parse_args()
    since_dt = _parse_since(args.since)
    apply = bool(args.apply and not args.dry_run)
    raise SystemExit(
        asyncio.run(
            run(
                apply=apply,
                batch_size=args.batch_size,
                since=since_dt,
                since_last_crawl=bool(args.since_last_crawl),
            )
        )
    )
