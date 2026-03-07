from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from bs4 import BeautifulSoup

from fashion_engine.config import settings

logger = logging.getLogger(__name__)

_MAX_HTML_CHARS = 8000


@dataclass
class GPTParseResult:
    products: list[dict]
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    compact = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return compact[:_MAX_HTML_CHARS]


def _extract_products(payload: str) -> list[dict]:
    raw = payload.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        if raw.endswith("```"):
            raw = raw[:-3]
    data = json.loads(raw)
    products = data.get("products", [])
    return products if isinstance(products, list) else []


async def parse_products_from_html(
    url: str,
    html: str,
    *,
    model: str = "gpt-4o-mini",
) -> GPTParseResult:
    if not settings.openai_api_key:
        logger.info("OPENAI_API_KEY 미설정으로 GPT parser 스킵: %s", url)
        return GPTParseResult(products=[], model=model)

    try:
        from openai import AsyncOpenAI
    except ImportError as exc:  # pragma: no cover - dependency/runtime concern
        raise RuntimeError("openai 패키지가 필요합니다. `uv sync` 후 다시 실행하세요.") from exc

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    cleaned_html = clean_html(html)
    if not cleaned_html:
        return GPTParseResult(products=[], model=model)

    response = await client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "다음 쇼핑몰 HTML에서 현재 판매 중인 제품만 추출하라.\n"
                            "반드시 JSON으로만 응답:\n"
                            '{"products":[{"name":"", "brand":"", "price":0, "currency":"USD", '
                            '"original_price":null, "url":"https://...", "image_url":null, "is_sale":false}]}\n'
                            f"URL: {url}\n"
                            f"HTML:\n{cleaned_html}"
                        ),
                    }
                ],
            }
        ],
    )
    text = getattr(response, "output_text", "").strip()
    products = _extract_products(text) if text else []
    usage = getattr(response, "usage", None)
    prompt_tokens = getattr(usage, "input_tokens", None)
    completion_tokens = getattr(usage, "output_tokens", None)
    total_tokens = getattr(usage, "total_tokens", None)

    logger.info(
        "GPT parser 완료 url=%s products=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s",
        url,
        len(products),
        prompt_tokens,
        completion_tokens,
        total_tokens,
    )
    return GPTParseResult(
        products=products,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
