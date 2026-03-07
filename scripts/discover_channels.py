from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.channel import Channel  # noqa: E402
from channel_probe import probe_channel  # noqa: E402


PROMPT_TEMPLATE = """패션 쇼핑몰 발굴 작업. 다음 조건에 맞는 실제 운영 중인 쇼핑몰 {count}개를 찾아라.

조건: {query}

결과를 JSON으로만 반환:
{{"channels": [{{
  "name": "쇼핑몰 이름",
  "url": "https://...",
  "country": "JP/US/KR/...",
  "description": "간단 설명",
  "estimated_platform": "shopify/woocommerce/cafe24/unknown"
}}]}}

중요:
- 실제 존재하는 URL만
- 리셀/마켓플레이스 제외
- 브랜드 공식몰 또는 편집샵만
- 중복 URL 금지
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI 채널 발굴 에이전트")
    parser.add_argument("--query", required=True, help="발굴 조건 (자연어)")
    parser.add_argument("--count", type=int, default=20, help="발굴 후보 수")
    return parser.parse_args()


def _normalize_host(url: str) -> str:
    return (urlparse(url).netloc or "").lower().removeprefix("www.")


async def discover_channels(query: str, count: int) -> list[dict]:
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError("openai 패키지가 필요합니다. `uv sync` 후 다시 실행하세요.") from exc

    client = AsyncOpenAI()
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": PROMPT_TEMPLATE.format(query=query, count=count),
            }
        ],
        response_format={"type": "json_object"},
    )
    text = (response.choices[0].message.content or "").strip()
    if not text:
        return []
    data = json.loads(text)
    channels = data.get("channels", [])
    return channels if isinstance(channels, list) else []


async def run(query: str, count: int) -> int:
    await init_db()
    candidates = await discover_channels(query, count)
    print(f"GPT 발굴 결과: {len(candidates)}개")
    if not candidates:
        return 0

    async with AsyncSessionLocal() as db:
        existing_rows = (await db.execute(select(Channel.url))).all()
        known_hosts = {_normalize_host(url) for (url,) in existing_rows if url}

        for candidate in candidates:
            url = str(candidate.get("url") or "").strip()
            name = str(candidate.get("name") or "").strip()
            if not url or not name:
                continue
            host = _normalize_host(url)
            if not host:
                print(f"  스킵: host 파싱 실패 {url}")
                continue
            if host in known_hosts:
                print(f"  이미 등록됨: {name} ({host})")
                continue

            result = await probe_channel(url, name=name)
            if result.http_status and 200 <= result.http_status < 400 and not result.blocked:
                channel = Channel(
                    name=name,
                    url=url,
                    original_url=url,
                    country=(str(candidate.get("country") or "").upper() or None),
                    description=str(candidate.get("description") or "").strip() or None,
                    platform=result.platform_detected or str(candidate.get("estimated_platform") or "").strip() or None,
                    is_active=False,
                )
                db.add(channel)
                known_hosts.add(host)
                print(f"  draft 등록: {name} ({url})")
            else:
                note = result.note or f"http_status={result.http_status}"
                print(f"  접근 불가: {name} ({note})")

        await db.commit()
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(asyncio.run(run(args.query, args.count)))
