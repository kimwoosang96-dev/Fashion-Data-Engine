"""공통 크롤러 기반 클래스"""
import asyncio
import logging
from typing import Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from tenacity import retry, stop_after_attempt, wait_exponential

from fashion_engine.config import settings

logger = logging.getLogger(__name__)


class BaseCrawler:
    """Playwright 기반 크롤러 기반 클래스"""

    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def __aenter__(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=settings.crawler_headless,
        )
        self._context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
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
