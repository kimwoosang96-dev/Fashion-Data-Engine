"""Multi-provider LLM HTML parser.

목적: 어디서 살 수 있는지, 최저가, 재고 여부 파악.
Provider 우선순위: Groq (빠름/무료) → Gemini Flash-Lite (한/일어 우수) → OpenAI (레거시)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from fashion_engine.config import settings

logger = logging.getLogger(__name__)

_MAX_HTML_CHARS = {
    "groq": 12000,
    "gemini": 20000,
    "openai": 8000,
}

_PROMPT = """\
다음 쇼핑몰 페이지에서 현재 판매 중인 제품을 추출하라.
목적: 어디서 살 수 있는지, 최저가, 재고 여부 파악.

반드시 JSON으로만 응답:
{{"products":[{{"name":"제품명","brand":"브랜드또는null","price":0,"currency":"KRW","original_price":null,"is_sale":false,"url":"https://직접링크","image_url":null,"in_stock":true,"sizes":[{{"size":"M","in_stock":true}}]}}]}}

규칙:
- 품절(Sold Out / Out of Stock / 품절 / 在庫なし) 제품은 in_stock=false
- 사이즈별 재고가 보이면 sizes 배열에 포함
- 가격 없는 제품 제외
- url은 반드시 해당 제품 페이지 직접 링크
- is_sale: 할인 중이면 true, original_price와 price 차이가 있으면 true

URL: {url}
HTML:
{html}"""


@dataclass
class GPTParseResult:
    products: list[dict] = field(default_factory=list)
    model: str = "none"
    provider: str = "none"
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


def clean_html(html: str, provider: str = "groq") -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    compact = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return compact[: _MAX_HTML_CHARS.get(provider, 8000)]


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


def _make_client(provider: str):
    from openai import AsyncOpenAI

    if provider == "groq":
        return AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.groq_api_key,
        )
    if provider == "gemini":
        return AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=settings.gemini_api_key,
        )
    # openai fallback
    return AsyncOpenAI(api_key=settings.openai_api_key)


_PROVIDER_MODELS = {
    "groq": "llama-3.1-8b-instant",
    "gemini": "gemini-2.5-flash-lite-preview-06-17",
    "openai": "gpt-4o-mini",
}


def _available_providers() -> list[str]:
    order = []
    if settings.groq_api_key:
        order.append("groq")
    if settings.gemini_api_key:
        order.append("gemini")
    if settings.openai_api_key:
        order.append("openai")
    return order


async def parse_products_from_html(
    url: str,
    html: str,
) -> GPTParseResult:
    providers = _available_providers()
    if not providers:
        logger.info("LLM parser: API 키 없음 — 스킵 url=%s", url)
        return GPTParseResult()

    for provider in providers:
        model = _PROVIDER_MODELS[provider]
        cleaned = clean_html(html, provider)
        if not cleaned:
            return GPTParseResult()

        prompt = _PROMPT.format(url=url, html=cleaned)
        try:
            client = _make_client(provider)
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0,
            )
            text = (response.choices[0].message.content or "").strip()
            products = _extract_products(text) if text else []
            usage = response.usage

            logger.info(
                "LLM parser 완료 provider=%s model=%s url=%s products=%s tokens=%s",
                provider,
                model,
                url,
                len(products),
                getattr(usage, "total_tokens", None),
            )

            if products:
                return GPTParseResult(
                    products=products,
                    model=model,
                    provider=provider,
                    prompt_tokens=getattr(usage, "prompt_tokens", None),
                    completion_tokens=getattr(usage, "completion_tokens", None),
                    total_tokens=getattr(usage, "total_tokens", None),
                )

            # 0개면 다음 provider 시도
            logger.info("LLM parser 0개 반환 — 다음 provider 시도 url=%s", url)

        except Exception as exc:
            logger.warning("LLM parser 오류 provider=%s url=%s: %s", provider, url, exc)

    return GPTParseResult()
