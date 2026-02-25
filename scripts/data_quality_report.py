"""
크롤 결과 데이터 품질 리포트 출력.

사용법:
    .venv/bin/python scripts/data_quality_report.py
"""
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()
DB_PATH = Path("data/fashion.db")


def canonical_slug(slug: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", slug.lower())


def main() -> None:
    if not DB_PATH.exists():
        console.print(f"[red]DB 파일 없음:[/red] {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    channel_rows = cur.execute(
        """
        SELECT c.id, c.name, c.channel_type, c.country, COUNT(cb.brand_id) AS brand_count
        FROM channels c
        LEFT JOIN channel_brands cb ON cb.channel_id = c.id
        WHERE c.is_active = 1
        GROUP BY c.id
        ORDER BY brand_count DESC, c.name ASC
        """
    ).fetchall()

    zero_edit_rows = [
        row for row in channel_rows if row[2] == "edit-shop" and row[4] == 0
    ]

    brands = cur.execute("SELECT slug, name FROM brands ORDER BY slug").fetchall()
    duplicate_candidates: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for slug, name in brands:
        duplicate_candidates[canonical_slug(slug)].append((slug, name))
    duplicate_groups = [v for v in duplicate_candidates.values() if len(v) > 1]

    summary = Table(title="데이터 품질 요약")
    summary.add_column("항목", style="cyan")
    summary.add_column("값", justify="right", style="green")
    summary.add_row("활성 채널", str(len(channel_rows)))
    summary.add_row("활성 edit-shop", str(sum(1 for r in channel_rows if r[2] == "edit-shop")))
    summary.add_row("edit-shop 0결과", str(len(zero_edit_rows)))
    summary.add_row("브랜드 수", str(len(brands)))
    summary.add_row("중복 의심 그룹", str(len(duplicate_groups)))
    console.print(summary)

    top_channels = Table(title="채널별 브랜드 수 Top 20")
    top_channels.add_column("채널", style="cyan")
    top_channels.add_column("타입", style="yellow")
    top_channels.add_column("국가")
    top_channels.add_column("브랜드 수", justify="right", style="green")
    for _, name, channel_type, country, brand_count in channel_rows[:20]:
        top_channels.add_row(name, channel_type or "-", country or "-", str(brand_count))
    console.print(top_channels)

    zero_table = Table(title="edit-shop 0결과 채널")
    zero_table.add_column("채널", style="cyan")
    zero_table.add_column("국가")
    zero_table.add_column("ID", justify="right", style="dim")
    for channel_id, name, _, country, _ in zero_edit_rows:
        zero_table.add_row(name, country or "-", str(channel_id))
    console.print(zero_table)

    dup_table = Table(title="중복 의심 브랜드 그룹 (최대 20)")
    dup_table.add_column("정규화 키", style="dim")
    dup_table.add_column("slug/name 묶음", style="magenta")
    for group in duplicate_groups[:20]:
        key = canonical_slug(group[0][0])
        joined = " | ".join([f"{slug} ({name})" for slug, name in group])
        dup_table.add_row(key, joined)
    console.print(dup_table)

    conn.close()


if __name__ == "__main__":
    main()
