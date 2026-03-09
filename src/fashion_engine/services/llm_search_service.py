"""
LLM 병렬 검색 서비스

GPT·Gemini·Claude를 asyncio.gather로 동시 호출하고,
결과를 취합·URL 중복 제거·가격순 정렬해서 반환한다.
"""
from __future__ import annotations

import asyncio
import json
import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

import httpx

# 트래킹 파라미터 목록 (제거 대상)
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "fbclid", "gclid", "msclkid", "affiliate", "aff", "partner",
    "irclickid", "ranMID", "ranEAID", "ranSiteID",
}


def normalize_url(url: str) -> str:
    """트래킹 파라미터 제거 + 경로 정규화."""
    try:
        p = urlparse(url)
        qs = parse_qs(p.query, keep_blank_values=False)
        cleaned = {k: v for k, v in qs.items() if k.lower() not in _TRACKING_PARAMS}
        clean_query = urlencode(cleaned, doseq=True)
        return urlunparse((p.scheme, p.netloc.lower(), p.path.rstrip("/"), "", clean_query, ""))
    except Exception:
        return url


def _extract_price(text: str) -> int | None:
    """텍스트에서 숫자 가격 추출 (첫 번째 매칭)."""
    m = re.search(r"[\d,]+", text.replace(",", ""))
    if m:
        try:
            return int(m.group().replace(",", ""))
        except ValueError:
            pass
    return None


# ---------------------------------------------------------------------------
# GPT
# ---------------------------------------------------------------------------

async def search_with_gpt(query: str, api_key: str) -> list[dict]:
    try:
        import openai
        client = openai.AsyncOpenAI(api_key=api_key)
        resp = await client.chat.completions.create(
            model="gpt-4o-search-preview",
            messages=[{
                "role": "user",
                "content": (
                    f"{query}\n\n"
                    "위 패션 제품의 판매 링크·가격·재고 정보를 찾아줘. "
                    "결과를 JSON 배열로 반환해. 각 항목: "
                    "{\"url\": \"...\", \"title\": \"...\", \"price\": \"...\", \"currency\": \"...\", \"in_stock\": true/false}"
                )
            }],
        )
        content = resp.choices[0].message.content or ""
        return _parse_json_results(content, source_ai="gpt")
    except Exception as e:
        return [{"error": str(e), "source_ai": "gpt"}]


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------

async def search_with_gemini(query: str, api_key: str) -> list[dict]:
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = await asyncio.to_thread(
            model.generate_content,
            (
                f"{query}\n\n"
                "위 패션 제품의 판매 링크·가격·재고 정보를 찾아줘. "
                "결과를 JSON 배열로 반환해. 각 항목: "
                "{\"url\": \"...\", \"title\": \"...\", \"price\": \"...\", \"currency\": \"...\", \"in_stock\": true/false}"
            ),
            tools=[genai.Tool.from_google_search_retrieval()],
        )
        content = response.text or ""
        return _parse_json_results(content, source_ai="gemini")
    except Exception as e:
        return [{"error": str(e), "source_ai": "gemini"}]


# ---------------------------------------------------------------------------
# Claude
# ---------------------------------------------------------------------------

async def search_with_claude(query: str, api_key: str) -> list[dict]:
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            tools=[{"type": "web_search", "name": "web_search"}],
            messages=[{
                "role": "user",
                "content": (
                    f"{query}\n\n"
                    "위 패션 제품의 판매 링크·가격·재고 정보를 찾아줘. "
                    "결과를 JSON 배열로 반환해. 각 항목: "
                    "{\"url\": \"...\", \"title\": \"...\", \"price\": \"...\", \"currency\": \"...\", \"in_stock\": true/false}"
                )
            }],
            extra_headers={"anthropic-beta": "web-search-20260209"},
        )
        content = ""
        for block in resp.content:
            if hasattr(block, "text"):
                content += block.text
        return _parse_json_results(content, source_ai="claude")
    except Exception as e:
        return [{"error": str(e), "source_ai": "claude"}]


# ---------------------------------------------------------------------------
# 결과 파싱 & 취합
# ---------------------------------------------------------------------------

def _parse_json_results(text: str, source_ai: str) -> list[dict]:
    """LLM 응답에서 JSON 배열 추출."""
    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if not match:
        return []
    try:
        items = json.loads(match.group())
        results = []
        for item in items:
            if not isinstance(item, dict) or "url" not in item:
                continue
            results.append({
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "price_raw": item.get("price", ""),
                "currency": item.get("currency", ""),
                "in_stock": item.get("in_stock", True),
                "source_ai": source_ai,
            })
        return results
    except (json.JSONDecodeError, ValueError):
        return []


def _deduplicate(results: list[dict]) -> list[dict]:
    """normalized URL 기준 중복 제거. 같은 URL이면 첫 번째만 유지."""
    seen: set[str] = set()
    unique = []
    for r in results:
        key = normalize_url(r.get("url", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        r["normalized_url"] = key
        unique.append(r)
    return unique


async def search_all(
    query: str,
    openai_key: str | None = None,
    gemini_key: str | None = None,
    claude_key: str | None = None,
) -> list[dict]:
    """
    활성화된 모든 AI에 동시 검색 → 취합 → 중복 제거.
    최소 1개 키가 있어야 결과를 반환.
    """
    tasks = []
    if openai_key:
        tasks.append(search_with_gpt(query, openai_key))
    if gemini_key:
        tasks.append(search_with_gemini(query, gemini_key))
    if claude_key:
        tasks.append(search_with_claude(query, claude_key))

    if not tasks:
        return []

    batches = await asyncio.gather(*tasks, return_exceptions=True)
    all_results: list[dict] = []
    errors: list[dict] = []

    for batch in batches:
        if isinstance(batch, Exception):
            errors.append({"error": str(batch)})
            continue
        for item in batch:
            if "error" in item:
                errors.append(item)
            else:
                all_results.append(item)

    unique = _deduplicate(all_results)
    return unique
