"""
데이터 품질 감사 리포트 스크립트 (읽기 전용).

사용법:
  uv run python scripts/data_audit.py
  DATABASE_URL=postgresql+asyncpg://... uv run python scripts/data_audit.py
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.config import settings  # noqa: E402
from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402


console = Console()


@dataclass
class Finding:
    severity: str  # OK | WARNING | ERROR
    section: str
    message: str


@dataclass
class AuditResult:
    findings: list[Finding]
    warning_count: int
    error_count: int
    elapsed_sec: float
    observed: dict[str, Any]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DB 데이터 품질 감사 리포트")
    p.add_argument("--limit", type=int, default=20, help="표시 상위 개수 기본값")
    return p.parse_args()


def safe_db_target(url: str) -> str:
    if "://" not in url:
        return "unknown"
    scheme, rest = url.split("://", 1)
    if "@" in rest:
        rest = rest.split("@", 1)[1]
    return f"{scheme}://{rest.split('/', 1)[0]}/..."


async def fetch_all(db, sql: str, params: dict[str, Any] | None = None) -> list[tuple[Any, ...]]:
    rows = (await db.execute(text(sql), params or {})).all()
    return [tuple(r) for r in rows]


async def fetch_one(db, sql: str, params: dict[str, Any] | None = None) -> tuple[Any, ...] | None:
    return (await db.execute(text(sql), params or {})).one_or_none()


def print_kv_table(title: str, rows: list[tuple[str, Any]]) -> None:
    t = Table(title=title)
    t.add_column("항목", style="cyan")
    t.add_column("값", justify="right", style="green")
    for k, v in rows:
        t.add_row(str(k), str(v))
    console.print(t)


async def section_1_channels(db, findings: list[Finding], limit: int) -> dict[str, Any]:
    section = "[1] 채널 현황"
    console.rule(section)

    total_channels = (await fetch_one(db, "SELECT COUNT(*) FROM channels"))[0]
    active_channels = (await fetch_one(db, "SELECT COUNT(*) FROM channels WHERE is_active = true"))[0]

    print_kv_table(
        "채널 기본 통계",
        [
            ("전체 채널", total_channels),
            ("활성 채널", active_channels),
        ],
    )

    top_channels = await fetch_all(
        db,
        """
        SELECT c.name, COUNT(p.id) AS product_count
        FROM channels c
        LEFT JOIN products p ON p.channel_id = c.id
        GROUP BY c.id, c.name
        ORDER BY product_count DESC, c.name ASC
        LIMIT :limit
        """,
        {"limit": limit},
    )
    t1 = Table(title="채널별 제품 수 상위")
    t1.add_column("채널")
    t1.add_column("제품 수", justify="right")
    for name, cnt in top_channels:
        t1.add_row(str(name), str(cnt))
    console.print(t1)

    zero_channels = await fetch_all(
        db,
        """
        SELECT c.name, c.url
        FROM channels c
        LEFT JOIN products p ON p.channel_id = c.id
        GROUP BY c.id, c.name, c.url
        HAVING COUNT(p.id) = 0
        ORDER BY c.name ASC
        """,
    )
    t2 = Table(title="제품 0개 채널 목록")
    t2.add_column("채널")
    t2.add_column("URL")
    for name, url in zero_channels:
        t2.add_row(str(name), str(url))
    console.print(t2)

    last_crawl = await fetch_all(
        db,
        """
        SELECT c.name, MAX(p.created_at) AS last_crawled_at
        FROM channels c
        LEFT JOIN products p ON p.channel_id = c.id
        GROUP BY c.id, c.name
        ORDER BY last_crawled_at ASC
        """,
    )
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    stale_rows: list[tuple[str, str]] = []
    for name, dt in last_crawl:
        if dt is None:
            stale_rows.append((str(name), "never"))
            continue
        # DB driver 별 datetime/string 차이 흡수
        parsed = dt
        if isinstance(dt, str):
            try:
                parsed = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            except ValueError:
                parsed = None
        if isinstance(parsed, datetime):
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed < stale_cutoff:
                stale_rows.append((str(name), parsed.isoformat()))

    t3 = Table(title="7일 이상 미크롤 채널")
    t3.add_column("채널")
    t3.add_column("마지막 크롤")
    for name, dt in stale_rows:
        t3.add_row(name, dt)
    console.print(t3)

    if zero_channels:
        findings.append(Finding("WARNING", section, f"제품 0개 채널 {len(zero_channels)}개"))
    else:
        findings.append(Finding("OK", section, "제품 0개 채널 없음"))

    if stale_rows:
        findings.append(Finding("WARNING", section, f"7일 이상 미크롤 채널 {len(stale_rows)}개"))
    else:
        findings.append(Finding("OK", section, "7일 이상 미크롤 채널 없음"))

    return {
        "channels_total": total_channels,
    }


async def section_2_brand_mapping(db, findings: list[Finding]) -> dict[str, Any]:
    section = "[2] 브랜드 매핑 품질"
    console.rule(section)

    total_products = (await fetch_one(db, "SELECT COUNT(*) FROM products"))[0]
    null_brand = (await fetch_one(db, "SELECT COUNT(*) FROM products WHERE brand_id IS NULL"))[0]
    ratio = round((null_brand / total_products) * 100, 2) if total_products else 0.0
    print_kv_table("브랜드 매핑 요약", [("전체 제품", total_products), ("brand_id NULL", f"{null_brand} ({ratio}%)")])

    by_type = await fetch_all(
        db,
        """
        SELECT c.channel_type, COUNT(*)
        FROM products p
        JOIN channels c ON c.id = p.channel_id
        WHERE p.brand_id IS NULL
        GROUP BY c.channel_type
        ORDER BY COUNT(*) DESC
        """,
    )
    t = Table(title="channel_type별 brand_id NULL")
    t.add_column("channel_type")
    t.add_column("NULL 제품 수", justify="right")
    for channel_type, cnt in by_type:
        t.add_row(str(channel_type), str(cnt))
    console.print(t)

    top_null_channels = await fetch_all(
        db,
        """
        SELECT c.name, COUNT(*) AS cnt
        FROM products p
        JOIN channels c ON c.id = p.channel_id
        WHERE p.brand_id IS NULL
        GROUP BY c.id, c.name
        ORDER BY cnt DESC
        LIMIT 10
        """,
    )
    t2 = Table(title="brand_id NULL 상위 10개 채널")
    t2.add_column("채널")
    t2.add_column("NULL 제품 수", justify="right")
    for name, cnt in top_null_channels:
        t2.add_row(str(name), str(cnt))
    console.print(t2)

    ghost_brands = (await fetch_one(
        db,
        """
        SELECT COUNT(*)
        FROM brands b
        LEFT JOIN products p ON p.brand_id = b.id
        WHERE p.id IS NULL
        """,
    ))[0]
    print_kv_table("유령 브랜드", [("products 0개 브랜드", ghost_brands)])

    if ratio >= 20:
        findings.append(Finding("ERROR", section, f"brand_id NULL 비율 높음: {ratio}%"))
    elif ratio >= 5:
        findings.append(Finding("WARNING", section, f"brand_id NULL 비율 주의: {ratio}%"))
    else:
        findings.append(Finding("OK", section, f"brand_id NULL 비율 양호: {ratio}%"))

    if ghost_brands > 0:
        findings.append(Finding("WARNING", section, f"유령 브랜드 {ghost_brands}개"))
    else:
        findings.append(Finding("OK", section, "유령 브랜드 없음"))

    return {
        "products_total": total_products,
    }


async def section_3_price_quality(db, findings: list[Finding]) -> None:
    section = "[3] 가격 품질"
    console.rule(section)

    latest_price_cte = """
    WITH latest AS (
      SELECT ph.product_id, MAX(ph.crawled_at) AS latest_at
      FROM price_history ph
      GROUP BY ph.product_id
    ), lp AS (
      SELECT ph.product_id, ph.price, ph.original_price, ph.currency
      FROM price_history ph
      JOIN latest l ON l.product_id = ph.product_id AND l.latest_at = ph.crawled_at
    )
    """

    zero_or_null = (await fetch_one(db, latest_price_cte + "SELECT COUNT(*) FROM lp WHERE price IS NULL OR price = 0"))[0]
    high_outlier = (await fetch_one(db, latest_price_cte + "SELECT COUNT(*) FROM lp WHERE price > 50000000"))[0]

    print_kv_table("가격 이상치", [("price=0 또는 NULL", zero_or_null), ("price>50,000,000", high_outlier)])

    outlier_samples = await fetch_all(
        db,
        latest_price_cte
        + """
        SELECT p.id, p.name, p.url, lp.price
        FROM lp
        JOIN products p ON p.id = lp.product_id
        WHERE lp.price > 50000000
        ORDER BY lp.price DESC
        LIMIT 5
        """,
    )
    t = Table(title="고가 이상값 샘플")
    t.add_column("product_id")
    t.add_column("name")
    t.add_column("price")
    t.add_column("url")
    for pid, name, url, price in outlier_samples:
        t.add_row(str(pid), str(name), str(price), str(url))
    console.print(t)

    by_currency = await fetch_all(
        db,
        latest_price_cte
        + """
        SELECT lp.currency, COUNT(*)
        FROM lp
        GROUP BY lp.currency
        ORDER BY COUNT(*) DESC
        """,
    )
    t2 = Table(title="통화별 제품 수(최신 가격 기준)")
    t2.add_column("currency")
    t2.add_column("제품 수", justify="right")
    for c, cnt in by_currency:
        t2.add_row(str(c), str(cnt))
    console.print(t2)

    missing_rate_currency = await fetch_all(
        db,
        latest_price_cte
        + """
        SELECT lp.currency, COUNT(*)
        FROM lp
        LEFT JOIN exchange_rates er
          ON er.from_currency = lp.currency AND er.to_currency = 'KRW'
        WHERE lp.currency <> 'KRW' AND er.id IS NULL
        GROUP BY lp.currency
        ORDER BY COUNT(*) DESC
        """,
    )
    t3 = Table(title="환율 미등록 통화 사용 현황")
    t3.add_column("currency")
    t3.add_column("제품 수", justify="right")
    for c, cnt in missing_rate_currency:
        t3.add_row(str(c), str(cnt))
    console.print(t3)

    inverted = (await fetch_one(
        db,
        latest_price_cte + "SELECT COUNT(*) FROM lp WHERE original_price IS NOT NULL AND original_price < price",
    ))[0]
    print_kv_table("역전 이상값", [("original_price < price", inverted)])

    if high_outlier > 0:
        findings.append(Finding("WARNING", section, f"고가 이상값 {high_outlier}개"))
    else:
        findings.append(Finding("OK", section, "고가 이상값 없음"))

    if missing_rate_currency:
        findings.append(Finding("ERROR", section, f"환율 미등록 통화 {len(missing_rate_currency)}종"))
    else:
        findings.append(Finding("OK", section, "환율 미등록 통화 없음"))

    if inverted > 0:
        findings.append(Finding("WARNING", section, f"가격 역전 이상값 {inverted}개"))
    else:
        findings.append(Finding("OK", section, "가격 역전 이상값 없음"))


async def section_4_sale_new(db, findings: list[Finding]) -> None:
    section = "[4] 세일 / 신상품 현황"
    console.rule(section)

    total_products = (await fetch_one(db, "SELECT COUNT(*) FROM products"))[0]
    sale_count = (await fetch_one(db, "SELECT COUNT(*) FROM products WHERE is_sale = true"))[0]
    new_count = (await fetch_one(db, "SELECT COUNT(*) FROM products WHERE is_new = true"))[0]

    sale_ratio = round((sale_count / total_products) * 100, 2) if total_products else 0
    new_ratio = round((new_count / total_products) * 100, 2) if total_products else 0
    print_kv_table(
        "세일/신상품 요약",
        [
            ("is_sale=True", f"{sale_count} ({sale_ratio}%)"),
            ("is_new=True", f"{new_count} ({new_ratio}%)"),
        ],
    )

    discount_buckets = await fetch_all(
        db,
        """
        WITH latest AS (
          SELECT ph.product_id, MAX(ph.crawled_at) AS latest_at
          FROM price_history ph
          GROUP BY ph.product_id
        )
        SELECT
          CASE
            WHEN ph.discount_rate IS NULL THEN 'NULL'
            WHEN ph.discount_rate >= 40 THEN '40%+'
            WHEN ph.discount_rate >= 30 THEN '30%대'
            WHEN ph.discount_rate >= 20 THEN '20%대'
            WHEN ph.discount_rate >= 10 THEN '10%대'
            ELSE '<10%'
          END AS bucket,
          COUNT(*)
        FROM price_history ph
        JOIN latest l ON l.product_id = ph.product_id AND l.latest_at = ph.crawled_at
        JOIN products p ON p.id = ph.product_id
        WHERE p.is_sale = true
        GROUP BY bucket
        ORDER BY COUNT(*) DESC
        """,
    )
    t = Table(title="discount_rate 분포(is_sale=True 최신 기준)")
    t.add_column("구간")
    t.add_column("수", justify="right")
    for b, cnt in discount_buckets:
        t.add_row(str(b), str(cnt))
    console.print(t)

    sale_null_discount = (await fetch_one(
        db,
        """
        WITH latest AS (
          SELECT ph.product_id, MAX(ph.crawled_at) AS latest_at
          FROM price_history ph
          GROUP BY ph.product_id
        )
        SELECT COUNT(*)
        FROM products p
        JOIN latest l ON l.product_id = p.id
        JOIN price_history ph ON ph.product_id = p.id AND ph.crawled_at = l.latest_at
        WHERE p.is_sale = true AND ph.discount_rate IS NULL
        """,
    ))[0]
    print_kv_table("세일 데이터 불일치", [("is_sale=True && discount_rate=NULL", sale_null_discount)])

    if sale_null_discount > 0:
        findings.append(Finding("WARNING", section, f"세일 불일치 {sale_null_discount}건"))
    else:
        findings.append(Finding("OK", section, "세일 데이터 일치"))


async def section_5_active_archive(db, findings: list[Finding]) -> None:
    section = "[5] 활성/품절 현황"
    console.rule(section)

    active = (await fetch_one(db, "SELECT COUNT(*) FROM products WHERE is_active = true"))[0]
    inactive = (await fetch_one(db, "SELECT COUNT(*) FROM products WHERE is_active = false"))[0]
    archived = (await fetch_one(db, "SELECT COUNT(*) FROM products WHERE archived_at IS NOT NULL"))[0]
    missing_archived_ts = (await fetch_one(
        db,
        "SELECT COUNT(*) FROM products WHERE is_active = false AND archived_at IS NULL",
    ))[0]

    print_kv_table(
        "활성/품절 통계",
        [
            ("is_active=True", active),
            ("is_active=False", inactive),
            ("archived_at IS NOT NULL", archived),
            ("is_active=False && archived_at NULL", missing_archived_ts),
        ],
    )

    if missing_archived_ts > 0:
        findings.append(Finding("WARNING", section, f"품절 타임스탬프 누락 {missing_archived_ts}건"))
    else:
        findings.append(Finding("OK", section, "품절 타임스탬프 누락 없음"))


async def section_6_price_history_quality(db, findings: list[Finding]) -> None:
    section = "[6] PriceHistory 품질"
    console.rule(section)

    total_ph = (await fetch_one(db, "SELECT COUNT(*) FROM price_history"))[0]
    products_no_ph = (await fetch_one(
        db,
        """
        SELECT COUNT(*)
        FROM products p
        LEFT JOIN price_history ph ON ph.product_id = p.id
        WHERE ph.id IS NULL
        """,
    ))[0]
    total_products = (await fetch_one(db, "SELECT COUNT(*) FROM products"))[0]
    avg_per_product = round(total_ph / total_products, 3) if total_products else 0
    min_max = await fetch_one(db, "SELECT MIN(crawled_at), MAX(crawled_at) FROM price_history")

    print_kv_table(
        "PriceHistory 요약",
        [
            ("총 레코드", total_ph),
            ("PriceHistory 0건 제품", products_no_ph),
            ("제품당 평균 레코드", avg_per_product),
            ("가장 오래된 날짜", min_max[0] if min_max else None),
            ("최신 날짜", min_max[1] if min_max else None),
        ],
    )

    if products_no_ph > 0:
        findings.append(Finding("WARNING", section, f"PriceHistory 없는 제품 {products_no_ph}개"))
    else:
        findings.append(Finding("OK", section, "모든 제품에 PriceHistory 존재"))


async def section_7_exchange_rates(db, findings: list[Finding]) -> None:
    section = "[7] 환율 현황"
    console.rule(section)

    rates = await fetch_all(
        db,
        """
        SELECT from_currency, to_currency, rate, fetched_at
        FROM exchange_rates
        ORDER BY from_currency ASC
        """,
    )
    t = Table(title="exchange_rates 목록")
    t.add_column("from")
    t.add_column("to")
    t.add_column("rate", justify="right")
    t.add_column("fetched_at")
    for from_c, to_c, rate, fetched_at in rates:
        t.add_row(str(from_c), str(to_c), str(rate), str(fetched_at))
    console.print(t)

    missing_for_products = await fetch_all(
        db,
        """
        WITH latest AS (
          SELECT ph.product_id, MAX(ph.crawled_at) AS latest_at
          FROM price_history ph
          GROUP BY ph.product_id
        ), lp AS (
          SELECT ph.product_id, ph.currency
          FROM price_history ph
          JOIN latest l ON l.product_id = ph.product_id AND l.latest_at = ph.crawled_at
        )
        SELECT lp.currency, COUNT(*)
        FROM lp
        LEFT JOIN exchange_rates er
          ON er.from_currency = lp.currency AND er.to_currency = 'KRW'
        WHERE lp.currency <> 'KRW' AND er.id IS NULL
        GROUP BY lp.currency
        ORDER BY COUNT(*) DESC
        """,
    )
    t2 = Table(title="products(최신 가격) 기준 환율 미등록 통화")
    t2.add_column("currency")
    t2.add_column("제품 수", justify="right")
    for c, cnt in missing_for_products:
        t2.add_row(str(c), str(cnt))
    console.print(t2)

    if missing_for_products:
        findings.append(Finding("ERROR", section, f"환율 미등록 통화 {len(missing_for_products)}종"))
    else:
        findings.append(Finding("OK", section, "환율 미등록 통화 없음"))


def print_summary(
    findings: list[Finding], baseline: dict[str, int], observed: dict[str, Any], elapsed_sec: float
) -> tuple[int, int]:
    console.rule("[8] 전체 요약 (Summary)")

    t = Table(title="품질 결과")
    t.add_column("상태")
    t.add_column("섹션")
    t.add_column("메시지")
    for f in findings:
        style = "green" if f.severity == "OK" else ("yellow" if f.severity == "WARNING" else "red")
        t.add_row(f.severity, f.section, f.message, style=style)
    console.print(t)

    warn_count = sum(1 for f in findings if f.severity == "WARNING")
    err_count = sum(1 for f in findings if f.severity == "ERROR")
    ok_count = sum(1 for f in findings if f.severity == "OK")

    score_rows = [
        ("OK", ok_count),
        ("WARNING", warn_count),
        ("ERROR", err_count),
        ("총 점검 항목", len(findings)),
        ("실행 시간(초)", round(elapsed_sec, 2)),
    ]
    print_kv_table("요약 카운트", score_rows)

    compare_rows = []
    for key, base in baseline.items():
        actual = observed.get(key, "-")
        compare_rows.append((key, f"기준 {base} / 현재 {actual}"))
    print_kv_table("AGENTS 기준값 비교", compare_rows)

    if err_count > 0:
        console.print(f"[red][RESULT] ERROR {err_count}개, WARNING {warn_count}개[/red]")
    elif warn_count > 0:
        console.print(f"[yellow][RESULT] WARNING {warn_count}개[/yellow]")
    else:
        console.print("[green][RESULT] 모든 점검 OK[/green]")
    return warn_count, err_count


async def run_audit(limit: int = 20, print_report: bool = True) -> AuditResult:
    started = time.perf_counter()

    findings: list[Finding] = []
    observed: dict[str, Any] = {}

    if print_report:
        console.print("[bold blue]Fashion Data Audit[/bold blue]")
        console.print(f"DB Target: {safe_db_target(settings.database_url)}")
        console.print(f"Started At (UTC): {datetime.now(timezone.utc).isoformat()}\n")

    await init_db()

    async with AsyncSessionLocal() as db:
        sections = [
            ("1", section_1_channels, {"limit": limit}),
            ("2", section_2_brand_mapping, {}),
            ("3", section_3_price_quality, {}),
            ("4", section_4_sale_new, {}),
            ("5", section_5_active_archive, {}),
            ("6", section_6_price_history_quality, {}),
            ("7", section_7_exchange_rates, {}),
        ]

        for name, fn, kwargs in sections:
            try:
                result = await fn(db, findings, **kwargs)
                if isinstance(result, dict):
                    observed.update(result)
            except SQLAlchemyError as e:
                msg = f"섹션 {name} SQL 오류: {str(e).splitlines()[0]}"
                if print_report:
                    console.print(f"[red]{msg}[/red]")
                findings.append(Finding("ERROR", f"[{name}]", msg))
                await db.rollback()
            except Exception as e:  # noqa: BLE001
                msg = f"섹션 {name} 처리 오류: {e}"
                if print_report:
                    console.print(f"[red]{msg}[/red]")
                findings.append(Finding("ERROR", f"[{name}]", msg))
                await db.rollback()

        # baseline 비교용 추가 집계
        try:
            observed["brands_total"] = (await fetch_one(db, "SELECT COUNT(*) FROM brands"))[0]
            observed["products_total"] = observed.get("products_total") or (await fetch_one(db, "SELECT COUNT(*) FROM products"))[0]
            observed["directors_total"] = (await fetch_one(db, "SELECT COUNT(*) FROM brand_directors"))[0]
            observed["channels_total"] = observed.get("channels_total") or (await fetch_one(db, "SELECT COUNT(*) FROM channels"))[0]
        except Exception as e:  # noqa: BLE001
            findings.append(Finding("ERROR", "[baseline]", f"기준 비교 집계 실패: {e}"))
            await db.rollback()

    elapsed = time.perf_counter() - started
    if print_report:
        warn_count, err_count = print_summary(
            findings,
            baseline={
                "channels_total": 159,
                "brands_total": 2561,
                "products_total": 26000,
                "directors_total": 109,
            },
            observed=observed,
            elapsed_sec=elapsed,
        )
        console.print(f"\nWARNING 총 {warn_count}개 / ERROR 총 {err_count}개")
    else:
        warn_count = sum(1 for f in findings if f.severity == "WARNING")
        err_count = sum(1 for f in findings if f.severity == "ERROR")

    return AuditResult(
        findings=findings,
        warning_count=warn_count,
        error_count=err_count,
        elapsed_sec=elapsed,
        observed=observed,
    )


async def main(limit: int = 20, print_report: bool = True) -> AuditResult:
    return await run_audit(limit=limit, print_report=print_report)


async def cli_main() -> int:
    args = parse_args()
    _ = await main(limit=args.limit, print_report=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(cli_main()))
