"""공통 크롤러 기반 클래스"""
import asyncio
import logging
import random
from typing import Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from tenacity import retry, stop_after_attempt, wait_exponential

from fashion_engine.config import settings

logger = logging.getLogger(__name__)

try:
    from playwright_stealth import stealth_async
except Exception:  # pragma: no cover - optional dependency fallback
    stealth_async = None

USER_AGENTS = [
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.6099.109 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.2 Safari/605.1.15"
    ),
]


class BaseCrawler:
    """Playwright 기반 크롤러 기반 클래스"""

    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._ua_pool = USER_AGENTS

    async def __aenter__(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=settings.crawler_headless,
        )
        default_ua = random.choice(self._ua_pool)
        self._context = await self._browser.new_context(
            user_agent=default_ua,
            viewport={"width": 1440, "height": 900},
            locale="ko-KR",
        )
        return self

    async def __aexit__(self, *args):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def new_page(self) -> Page:
        return await self._context.new_page()

    @retry(
        stop=stop_after_attempt(settings.crawler_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def fetch_page(self, url: str) -> Page:
        """URL을 열고 렌더링 완료된 Page 반환"""
        page = await self.new_page()
        try:
            ua = random.choice(self._ua_pool)
            await page.set_extra_http_headers({"User-Agent": ua})
            if stealth_async:
                await stealth_async(page)
            await page.goto(
                url,
                timeout=settings.crawler_timeout_seconds * 1000,
                wait_until="domcontentloaded",
            )
            # 레이트 리밋: 요청 간 대기
            await asyncio.sleep(settings.crawler_delay_seconds)
            return page
        except Exception as e:
            await page.close()
            logger.warning(f"페이지 로드 실패 {url}: {e}")
            raise
