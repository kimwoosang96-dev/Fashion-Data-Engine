"""
채널별 브랜드 목록 크롤러.

각 판매채널을 방문하여 취급 브랜드를 추출합니다.
공통 패턴 + 채널별 커스텀 전략을 조합하여 사용합니다.
"""
import logging
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup
from playwright.async_api import Page

from fashion_engine.crawler.base import BaseCrawler

logger = logging.getLogger(__name__)


@dataclass
class BrandInfo:
    name: str
    url: str | None = None
    source_channel_url: str = ""


@dataclass
class ChannelCrawlResult:
    channel_url: str
    brands: list[BrandInfo] = field(default_factory=list)
    error: str | None = None
    crawl_strategy: str = "unknown"


# ── 채널별 커스텀 전략 ──────────────────────────────────────────────────

CHANNEL_STRATEGIES: dict[str, dict] = {
    "musinsa.com": {
        "brand_list_url": "https://www.musinsa.com/brand",
        "brand_selector": "a.brand-item, .brand-list a, [class*='brand'] a",
        "name_selector": None,  # 링크 텍스트 사용
    },
    "29cm.co.kr": {
        "brand_list_url": "https://www.29cm.co.kr/brand",
        "brand_selector": ".brand-item a, [class*='brand'] a",
        "name_selector": None,
    },
    "wconcept.co.kr": {
        "brand_list_url": "https://www.wconcept.co.kr/Brand",
        "brand_selector": ".brand_list a, .brand-list a",
        "name_selector": None,
    },
    "lfmall.co.kr": {
        "brand_list_url": "https://www.lfmall.co.kr/brand.lf",
        "brand_selector": ".brand-list a, .brandList a",
        "name_selector": None,
    },
}


class BrandCrawler(BaseCrawler):
    """판매채널에서 브랜드 목록을 추출하는 크롤러"""

    async def crawl_channel(self, channel_url: str) -> ChannelCrawlResult:
        """채널 URL에서 브랜드 목록 추출"""
        result = ChannelCrawlResult(channel_url=channel_url)

        # 채널별 커스텀 전략 확인
        strategy = self._find_strategy(channel_url)

        try:
            if strategy:
                brands = await self._crawl_with_strategy(channel_url, strategy)
                result.crawl_strategy = "custom"
            else:
                brands = await self._crawl_generic(channel_url)
                result.crawl_strategy = "generic"

            result.brands = brands
            logger.info(f"[{channel_url}] {len(brands)}개 브랜드 추출 ({result.crawl_strategy})")

        except Exception as e:
            result.error = str(e)
            logger.error(f"[{channel_url}] 크롤링 실패: {e}")

        return result

    def _find_strategy(self, channel_url: str) -> dict | None:
        for domain, strategy in CHANNEL_STRATEGIES.items():
            if domain in channel_url:
                return strategy
        return None

    async def _crawl_with_strategy(self, channel_url: str, strategy: dict) -> list[BrandInfo]:
        """커스텀 전략으로 브랜드 추출"""
        target_url = strategy.get("brand_list_url", channel_url)
        page = await self.fetch_page(target_url)

        try:
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            selector = strategy["brand_selector"]
            elements = soup.select(selector)

            brands = []
            for el in elements:
                name = el.get_text(strip=True)
                href = el.get("href", "")
                if name and len(name) > 1:  # 단일 문자 필터링
                    brands.append(BrandInfo(
                        name=self._clean_brand_name(name),
                        url=href if href.startswith("http") else None,
                        source_channel_url=channel_url,
                    ))

            return self._deduplicate_brands(brands)
        finally:
            await page.close()

    async def _crawl_generic(self, channel_url: str) -> list[BrandInfo]:
        """
        범용 브랜드 추출 전략:
        1. /brand, /brands 경로 시도
        2. 네비게이션 메뉴에서 브랜드 링크 추출
        3. 반복적으로 나타나는 브랜드명 텍스트 추출
        """
        brand_paths = ["/brand", "/brands", "/brand-list", "/designer", "/designers"]

        for path in brand_paths:
            try:
                test_url = channel_url.rstrip("/") + path
                page = await self.fetch_page(test_url)
                brands = await self._extract_brands_from_page(page, channel_url)
                await page.close()

                if brands:
                    logger.info(f"브랜드 페이지 발견: {test_url}")
                    return brands
            except Exception:
                continue

        # 브랜드 전용 페이지 없으면 홈페이지 네비게이션 분석
        page = await self.fetch_page(channel_url)
        brands = await self._extract_brands_from_navigation(page, channel_url)
        await page.close()
        return brands

    async def _extract_brands_from_page(self, page: Page, source_url: str) -> list[BrandInfo]:
        """페이지 내 브랜드 링크 추출"""
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # 브랜드 관련 키워드가 포함된 컨테이너 탐색
        brand_containers = soup.select(
            "[class*='brand'], [id*='brand'], [class*='designer'], [id*='designer']"
        )

        brands = []
        for container in brand_containers:
            for link in container.find_all("a"):
                name = link.get_text(strip=True)
                if name and 1 < len(name) <= 60:
                    brands.append(BrandInfo(
                        name=self._clean_brand_name(name),
                        url=link.get("href"),
                        source_channel_url=source_url,
                    ))

        return self._deduplicate_brands(brands)

    async def _extract_brands_from_navigation(self, page: Page, source_url: str) -> list[BrandInfo]:
        """홈페이지 네비게이션에서 브랜드 섹션 탐색"""
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        nav_elements = soup.find_all(["nav", "header", "ul"], recursive=True)
        brands = []

        for nav in nav_elements:
            links = nav.find_all("a")
            for link in links:
                text = link.get_text(strip=True)
                href = link.get("href", "")
                # 브랜드 링크 패턴 (브랜드, brand 포함)
                if re.search(r"/brand|/designer", href, re.I) and text:
                    brands.append(BrandInfo(
                        name=self._clean_brand_name(text),
                        url=href,
                        source_channel_url=source_url,
                    ))

        return self._deduplicate_brands(brands)

    @staticmethod
    def _clean_brand_name(name: str) -> str:
        """브랜드명 정규화"""
        name = re.sub(r"\s+", " ", name).strip()
        # 괄호 안 부가정보 제거 (예: "Nike (나이키)" → "Nike")
        name = re.sub(r"\s*\([^)]*\)\s*", "", name).strip()
        return name

    @staticmethod
    def _deduplicate_brands(brands: list[BrandInfo]) -> list[BrandInfo]:
        """이름 기준 중복 제거"""
        seen = set()
        result = []
        for b in brands:
            key = b.name.lower()
            if key and key not in seen:
                seen.add(key)
                result.append(b)
        return result
