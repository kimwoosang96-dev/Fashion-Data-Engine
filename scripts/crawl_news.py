"""
패션 뉴스 RSS 수집 스크립트.

사용법:
  uv run python scripts/crawl_news.py
  uv run python scripts/crawl_news.py --per-feed 20
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import typer
from rich.console import Console
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.brand import Brand  # noqa: E402
from fashion_engine.models.channel import Channel  # noqa: E402
from fashion_engine.models.fashion_news import FashionNews  # noqa: E402

app = typer.Typer()
console = Console()

RSS_FEEDS = [
    "https://hypebeast.com/feed",
    "https://www.highsnobiety.com/feed/",
    "https://sneakernews.com/feed/",
    "https://www.complex.com/style/rss",
]


def _published_dt(entry: dict) -> datetime | None:
    for key in ("published", "updated"):
        raw = entry.get(key)
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except Exception:
                continue
    return None


def _source_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower().replace("www.", "")
    return host[:50] if host else "rss"


@app.command()
def main(
    per_feed: int = typer.Option(30, min=1, max=100, help="피드당 최대 수집 개수"),
):
    asyncio.run(run(per_feed=per_feed))


async def run(per_feed: int = 30) -> None:
    await init_db()
    inserted = 0
    scanned = 0

    async with AsyncSessionLocal() as db:
        brands = list((await db.execute(select(Brand.id, Brand.name, Brand.slug))).all())
        channels = list((await db.execute(select(Channel.id, Channel.name))).all())

        brand_keywords = sorted(
            [(bid, (name or "").lower()) for bid, name, _ in brands if name],
            key=lambda x: len(x[1]),
            reverse=True,
        )
        channel_keywords = sorted(
            [(cid, (name or "").lower()) for cid, name in channels if name],
            key=lambda x: len(x[1]),
            reverse=True,
        )

        for feed_url in RSS_FEEDS:
            parsed = feedparser.parse(feed_url)
            entries = parsed.entries[:per_feed]
            for entry in entries:
                scanned += 1
                title = (entry.get("title") or "").strip()
                link = (entry.get("link") or "").strip()
                summary = (entry.get("summary") or "").strip() or None
                if not title or not link:
                    continue

                text_basis = f"{title} {summary or ''}".lower()
                entity_type = None
                entity_id = None

                for bid, kw in brand_keywords:
                    if kw and kw in text_basis:
                        entity_type = "brand"
                        entity_id = bid
                        break

                if entity_type is None:
                    for cid, kw in channel_keywords:
                        if kw and kw in text_basis:
                            entity_type = "channel"
                            entity_id = cid
                            break

                if entity_type is None or entity_id is None:
                    continue

                exists = (
                    await db.execute(select(FashionNews.id).where(FashionNews.url == link))
                ).scalar_one_or_none()
                if exists:
                    continue

                news = FashionNews(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    title=title[:500],
                    url=link[:1000],
                    summary=(summary[:4000] if summary else None),
                    published_at=_published_dt(entry),
                    source=_source_from_url(link),
                    crawled_at=datetime.utcnow(),
                )
                db.add(news)
                inserted += 1

        await db.commit()

    console.print(
        f"[bold green]뉴스 수집 완료[/bold green] scanned={scanned}, inserted={inserted}, feeds={len(RSS_FEEDS)}"
    )


if __name__ == "__main__":
    main()
