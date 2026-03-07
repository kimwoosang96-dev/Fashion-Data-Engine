"""
DCinside 패션 커뮤니티 신호 수집기.

사용법:
  uv run python scripts/crawl_community.py --dry-run
  uv run python scripts/crawl_community.py --apply
  uv run python scripts/crawl_community.py --html-file /tmp/dcinside_sample.html --apply
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

import httpx
import typer
from bs4 import BeautifulSoup
from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.brand import Brand  # noqa: E402
from fashion_engine.models.fashion_news import FashionNews  # noqa: E402

app = typer.Typer()

DEFAULT_GALLERY_URL = "https://gall.dcinside.com/board/lists?id=streetfashion"


@dataclass
class CommunityHit:
    brand_id: int
    title: str
    url: str
    keyword: str


def _extract_posts(html: str, base_url: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    items: list[tuple[str, str]] = []
    for anchor in soup.select("a[href]"):
        title = anchor.get_text(" ", strip=True)
        href = (anchor.get("href") or "").strip()
        if len(title) < 4 or not href:
            continue
        if "board/view" not in href and "no=" not in href:
            continue
        full_url = urljoin(base_url, href)
        if full_url in seen:
            continue
        seen.add(full_url)
        items.append((title[:500], full_url[:1000]))
    return items


def _find_hits(posts: list[tuple[str, str]], brands: list[Brand]) -> list[CommunityHit]:
    keyword_rows: list[tuple[str, int]] = []
    for brand in brands:
        for raw in [brand.name, brand.name_ko, brand.slug]:
            text = (raw or "").strip().lower()
            if len(text) >= 3:
                keyword_rows.append((text, brand.id))
    keyword_rows.sort(key=lambda row: len(row[0]), reverse=True)

    hits: list[CommunityHit] = []
    for title, url in posts:
        text = title.lower()
        matched_brand_id = None
        matched_keyword = None
        for keyword, brand_id in keyword_rows:
            if keyword in text:
                matched_brand_id = brand_id
                matched_keyword = keyword
                break
        if matched_brand_id is None or matched_keyword is None:
            continue
        hits.append(
            CommunityHit(
                brand_id=matched_brand_id,
                title=title,
                url=url,
                keyword=matched_keyword,
            )
        )
    return hits


async def _load_html(*, gallery_url: str, html_file: Path | None) -> str:
    if html_file:
        return html_file.read_text(encoding="utf-8")
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        resp = await client.get(gallery_url)
        resp.raise_for_status()
        return resp.text


async def run(*, gallery_url: str, html_file: Path | None, apply: bool) -> int:
    await init_db()
    html = await _load_html(gallery_url=gallery_url, html_file=html_file)
    posts = _extract_posts(html, gallery_url)

    async with AsyncSessionLocal() as db:
        brands = list((await db.execute(select(Brand))).scalars().all())
        hits = _find_hits(posts, brands)

        inserted = 0
        for hit in hits:
            exists = (
                await db.execute(select(FashionNews.id).where(FashionNews.url == hit.url))
            ).scalar_one_or_none()
            if exists:
                continue
            db.add(
                FashionNews(
                    entity_type="brand",
                    entity_id=hit.brand_id,
                    title=hit.title,
                    url=hit.url,
                    summary=f"DCinside 언급 감지 keyword={hit.keyword}",
                    published_at=None,
                    source="dcinside",
                    crawled_at=datetime.now(UTC).replace(tzinfo=None),
                )
            )
            inserted += 1

        if apply:
            await db.commit()
        else:
            await db.rollback()

    print(
        f"community crawl done posts={len(posts)} hits={len(hits)} inserted={inserted} apply={apply}"
    )
    return inserted


@app.command()
def main(
    gallery_url: str = typer.Option(DEFAULT_GALLERY_URL, help="대상 갤러리 URL"),
    html_file: Path | None = typer.Option(None, help="테스트용 로컬 HTML 파일"),
    apply: bool = typer.Option(False, "--apply", help="실제 DB 반영"),
):
    asyncio.run(run(gallery_url=gallery_url, html_file=html_file, apply=apply))


if __name__ == "__main__":
    app()
