"""
브라우저 자동화 기반 AI 쇼퍼

Playwright로 claude.ai / chat.openai.com / gemini.google.com을 직접 제어해
사용자 구독 계정으로 쿼리하고 응답을 파싱한다. API 비용 0원.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

# 셀렉터 설정 로드
_SELECTORS_PATH = Path(__file__).parent.parent / "config" / "ai_selectors.json"
with open(_SELECTORS_PATH) as f:
    SELECTORS: dict[str, dict[str, str]] = json.load(f)

SHOPPER_PROMPT = """{query}

위 패션 제품의 현재 판매 링크와 가격을 찾아줘.
결과는 아래 형식으로 각 판매처마다 한 줄씩:
- URL: [구매링크]  쇼핑몰: [사이트명]  가격: [가격]  재고: [있음/없음]
"""

# 트래킹 파라미터 제거 대상
_TRACKING = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "fbclid", "gclid", "msclkid", "affiliate", "aff",
}


def _default_profile_dir() -> str:
    """macOS Chrome 기본 프로필 디렉터리."""
    home = Path.home()
    candidates = [
        home / "Library/Application Support/Google/Chrome",
        home / "Library/Application Support/Chromium",
        home / ".config/google-chrome",
        home / ".config/chromium",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    # 없으면 임시 디렉터리 (새 세션 — 로그인 필요)
    tmp = home / ".fashion-shopper-browser"
    tmp.mkdir(exist_ok=True)
    return str(tmp)


def normalize_url(url: str) -> str:
    try:
        p = urlparse(url)
        qs = parse_qs(p.query, keep_blank_values=False)
        cleaned = {k: v for k, v in qs.items() if k.lower() not in _TRACKING}
        return urlunparse((p.scheme, p.netloc.lower(), p.path.rstrip("/"), "", urlencode(cleaned, doseq=True), ""))
    except Exception:
        return url


def _extract_results(text: str, source_ai: str) -> list[dict]:
    """응답 텍스트에서 URL·가격·쇼핑몰 파싱."""
    url_re = re.compile(r"https?://[^\s\)\]\"'<>]+")
    price_re = re.compile(r"가격[:\s]*([₩￥$€£]?[\d,]+\s*(?:원|KRW|USD|JPY|GBP|EUR)?)")
    shop_re = re.compile(r"쇼핑몰[:\s]*([^\s\n,]+)")
    stock_re = re.compile(r"재고[:\s]*(있음|없음|in stock|out of stock)", re.IGNORECASE)

    results = []
    # 줄 단위로 파싱
    for line in text.splitlines():
        urls = url_re.findall(line)
        if not urls:
            continue
        price_m = price_re.search(line)
        shop_m = shop_re.search(line)
        stock_m = stock_re.search(line)
        for url in urls:
            results.append({
                "url": url,
                "normalized_url": normalize_url(url),
                "title": shop_m.group(1) if shop_m else "",
                "price_raw": price_m.group(1) if price_m else "",
                "currency": "",
                "in_stock": not bool(stock_m and "없" in stock_m.group(1).lower()),
                "source_ai": source_ai,
            })
    return results


async def _query_ai(service: str, query: str, profile_dir: str) -> list[dict]:
    """지정 AI 서비스에 쿼리 전송 → 결과 파싱."""
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout

    sel = SELECTORS[service]
    prompt = SHOPPER_PROMPT.format(query=query)

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,           # 사용자 세션 유지 + bot 감지 우회
            args=["--no-sandbox"],
            slow_mo=50,               # 자연스러운 타이핑 속도
        )
        page = await ctx.new_page()
        await page.goto(sel["url"], wait_until="domcontentloaded")

        # 로그인 확인
        try:
            await page.wait_for_selector(sel["login_check_selector"], timeout=8000)
        except PWTimeout:
            await ctx.close()
            return [{"error": f"{service}: 로그인 필요 — {sel['login_url']} 에서 로그인하세요.", "source_ai": service}]

        # 프롬프트 입력
        input_el = await page.query_selector(sel["input_selector"])
        if not input_el:
            await ctx.close()
            return [{"error": f"{service}: 입력창을 찾을 수 없습니다.", "source_ai": service}]

        await input_el.click()
        await input_el.fill(prompt)
        await page.keyboard.press("Enter")

        # 응답 완료 대기 (스트리밍 종료)
        # 스트리밍 인디케이터가 사라질 때까지 최대 60초 대기
        try:
            await page.wait_for_selector(sel["streaming_indicator"], timeout=5000)
            await page.wait_for_selector(
                sel["streaming_indicator"],
                state="hidden",
                timeout=60000,
            )
        except PWTimeout:
            pass  # 인디케이터가 없거나 이미 완료

        # 추가 안정화 대기
        await page.wait_for_timeout(1500)

        # 응답 텍스트 추출
        response_text = ""
        try:
            el = await page.query_selector(sel["response_selector"])
            if el:
                response_text = await el.inner_text()
        except Exception:
            pass

        await ctx.close()
        return _extract_results(response_text, source_ai=service)


async def query_all(
    query: str,
    enabled: list[str],
    profile_dir: str | None = None,
) -> list[dict]:
    """
    활성화된 AI 서비스에 동시 쿼리.

    Args:
        query: 검색 쿼리
        enabled: ["claude", "gpt", "gemini"] 중 활성화된 서비스 목록
        profile_dir: Chrome 프로필 디렉터리 (None이면 자동 감지)
    """
    pdir = profile_dir or _default_profile_dir()
    valid = [s for s in enabled if s in SELECTORS]
    if not valid:
        return []

    tasks = [_query_ai(service, query, pdir) for service in valid]
    batches = await asyncio.gather(*tasks, return_exceptions=True)

    all_results: list[dict] = []
    for batch in batches:
        if isinstance(batch, Exception):
            all_results.append({"error": str(batch)})
            continue
        all_results.extend(batch)

    # URL 중복 제거
    seen: set[str] = set()
    unique = []
    for r in all_results:
        if "error" in r:
            unique.append(r)
            continue
        key = r.get("normalized_url", r.get("url", ""))
        if key and key not in seen:
            seen.add(key)
            unique.append(r)

    return unique


async def check_login(service: str, profile_dir: str | None = None) -> dict:
    """해당 AI 서비스의 로그인 상태 확인."""
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout

    if service not in SELECTORS:
        return {"service": service, "logged_in": False, "error": "알 수 없는 서비스"}

    sel = SELECTORS[service]
    pdir = profile_dir or _default_profile_dir()

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=pdir, headless=True
        )
        page = await ctx.new_page()
        await page.goto(sel["url"], wait_until="domcontentloaded")
        try:
            await page.wait_for_selector(sel["login_check_selector"], timeout=6000)
            await ctx.close()
            return {"service": service, "logged_in": True}
        except PWTimeout:
            await ctx.close()
            return {"service": service, "logged_in": False, "login_url": sel["login_url"]}
