from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.database import AsyncSessionLocal


def _catalog_sql(since: datetime | None) -> tuple[str, dict]:
    params: dict = {"since": since}
    since_filter = "AND p.updated_at > :since" if since is not None else ""

    sql = f"""
        WITH changed_keys AS (
            SELECT DISTINCT COALESCE(p.normalized_key, p.product_key) AS nkey
            FROM products p
            WHERE COALESCE(p.normalized_key, p.product_key) IS NOT NULL
            {since_filter}
        ),
        keyed AS (
            SELECT
                COALESCE(p.normalized_key, p.product_key) AS nkey,
                p.id AS product_id,
                p.channel_id,
                p.brand_id,
                p.name,
                p.gender,
                p.subcategory,
                p.created_at
            FROM products p
            WHERE COALESCE(p.normalized_key, p.product_key) IS NOT NULL
              AND (
                :since IS NULL
                OR COALESCE(p.normalized_key, p.product_key) IN (SELECT nkey FROM changed_keys)
              )
        ),
        brand_freq AS (
            SELECT nkey, brand_id, COUNT(*) AS cnt
            FROM keyed
            WHERE brand_id IS NOT NULL
            GROUP BY nkey, brand_id
        ),
        brand_ranked AS (
            SELECT
                nkey,
                brand_id,
                ROW_NUMBER() OVER (PARTITION BY nkey ORDER BY cnt DESC, brand_id ASC) AS rn
            FROM brand_freq
        ),
        top_brand AS (
            SELECT nkey, brand_id
            FROM brand_ranked
            WHERE rn = 1
        ),
        agg AS (
            SELECT
                k.nkey,
                MAX(k.name) AS canonical_name,
                MAX(k.gender) AS gender,
                MAX(k.subcategory) AS subcategory,
                COUNT(DISTINCT k.channel_id) AS listing_count,
                MIN(k.created_at) AS first_seen_at
            FROM keyed k
            GROUP BY k.nkey
        ),
        latest_price AS (
            SELECT x.product_id, x.price, x.is_sale
            FROM (
                SELECT
                    ph.product_id,
                    ph.price,
                    ph.is_sale,
                    ph.currency,
                    ROW_NUMBER() OVER (
                        PARTITION BY ph.product_id
                        ORDER BY ph.crawled_at DESC, ph.id DESC
                    ) AS rn
                FROM price_history ph
            ) x
            WHERE x.rn = 1
              AND x.currency = 'KRW'
        ),
        price_agg AS (
            SELECT
                k.nkey,
                MIN(CAST(lp.price AS INTEGER)) AS min_price_krw,
                MAX(CAST(lp.price AS INTEGER)) AS max_price_krw,
                MAX(CASE WHEN lp.is_sale THEN 1 ELSE 0 END) AS is_sale_anywhere
            FROM keyed k
            LEFT JOIN latest_price lp ON lp.product_id = k.product_id
            GROUP BY k.nkey
        )
        INSERT INTO product_catalog (
            normalized_key,
            canonical_name,
            brand_id,
            gender,
            subcategory,
            listing_count,
            min_price_krw,
            max_price_krw,
            is_sale_anywhere,
            first_seen_at,
            updated_at
        )
        SELECT
            a.nkey,
            COALESCE(a.canonical_name, a.nkey),
            tb.brand_id,
            a.gender,
            a.subcategory,
            a.listing_count,
            pa.min_price_krw,
            pa.max_price_krw,
            CASE WHEN pa.is_sale_anywhere = 1 THEN 1 ELSE 0 END,
            a.first_seen_at,
            CURRENT_TIMESTAMP
        FROM agg a
        LEFT JOIN top_brand tb ON tb.nkey = a.nkey
        LEFT JOIN price_agg pa ON pa.nkey = a.nkey
        ON CONFLICT(normalized_key) DO UPDATE SET
            canonical_name = EXCLUDED.canonical_name,
            brand_id = EXCLUDED.brand_id,
            gender = EXCLUDED.gender,
            subcategory = EXCLUDED.subcategory,
            listing_count = EXCLUDED.listing_count,
            min_price_krw = EXCLUDED.min_price_krw,
            max_price_krw = EXCLUDED.max_price_krw,
            is_sale_anywhere = EXCLUDED.is_sale_anywhere,
            updated_at = CURRENT_TIMESTAMP
    """
    return sql, params


async def _count_keys(db: AsyncSession, since: datetime | None) -> int:
    if since is None:
        stmt = text(
            """
            SELECT COUNT(*)
            FROM (
                SELECT DISTINCT COALESCE(normalized_key, product_key) AS nkey
                FROM products
                WHERE COALESCE(normalized_key, product_key) IS NOT NULL
            ) t
            """
        )
        return int((await db.execute(stmt)).scalar() or 0)

    stmt = text(
        """
        SELECT COUNT(*)
        FROM (
            SELECT DISTINCT COALESCE(normalized_key, product_key) AS nkey
            FROM products
            WHERE updated_at > :since
              AND COALESCE(normalized_key, product_key) IS NOT NULL
        ) t
        """
    )
    return int((await db.execute(stmt, {"since": since})).scalar() or 0)


async def _build_catalog(db: AsyncSession, since: datetime | None) -> int:
    affected = await _count_keys(db, since)
    sql, params = _catalog_sql(since)
    await db.execute(text(sql), params)
    await db.commit()
    return affected


async def build_catalog_full(db: AsyncSession, batch_size: int = 1000) -> int:
    del batch_size
    return await _build_catalog(db, since=None)


async def build_catalog_incremental(since: datetime, batch_size: int = 1000) -> int:
    del batch_size
    async with AsyncSessionLocal() as db:
        return await _build_catalog(db, since=since)


async def get_last_done_crawl_finished_at(db: AsyncSession) -> datetime | None:
    row = (
        await db.execute(
            text(
                """
                SELECT finished_at
                FROM crawl_runs
                WHERE status = :status
                  AND finished_at IS NOT NULL
                ORDER BY finished_at DESC
                LIMIT 1
                """
            ),
            {"status": "done"},
        )
    ).first()
    return row[0] if row else None
