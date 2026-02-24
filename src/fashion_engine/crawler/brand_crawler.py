"""
채널별 브랜드 목록 크롤러.

각 판매채널을 방문하여 취급 브랜드를 추출합니다.
우선순위:
  1. 채널별 커스텀 전략 (CHANNEL_STRATEGIES)
  2. Shopify /products.json API  ← vendor 필드로 정확한 브랜드 추출
  3. /brands 등 전용 페이지 HTML 파싱
  4. 홈페이지 네비게이션 분석 (fallback)
"""
import json
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
        "name_selector": None,
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


# ── 브랜드명 유효성 검사 ────────────────────────────────────────────────

# 한국어 조사·어미 패턴 → 브랜드명이 아닌 UI 텍스트
_KO_NOT_BRAND_RE = re.compile(
    r"(?:[을를이가은는의으로부터까지도만](?:\s|$))"  # 조사
    r"|(?:지다|하다|이다|되다|있다|없다|퍼지다)$"    # 동사 어미
    r"|(?:함|었|겠)$"                               # 명사화·과거형
)

# 언어 무관 공통 UI 단어 (완전 일치)
_UI_WORDS: frozenset[str] = frozenset(
    {
        "brands", "brand", "products", "product", "all", "new", "sale",
        "menu", "home", "shop", "store", "search", "cart", "account",
        "login", "logout", "register", "collections", "collection",
        "브랜드", "제품", "검색", "장바구니", "계정", "로그인", "목록",
        "보다", "상태", "이익", "원소", "존재함",
        # Cafe24 가격/정렬 옵션 (브랜드 아님)
        "낮은가격", "높은가격", "낮은가격순", "높은가격순",
        "추천순", "신상품순", "판매량순", "낮은순", "높은순",
    }
)

# 브랜드명 끝에 올 수 없는 한국어 접미사
_KO_NOT_BRAND_SUFFIX = ("바로가기", "더보기", "전체보기", "상품보기")


def _is_valid_brand_name(name: str) -> bool:
    """브랜드명으로 적합한지 검사"""
    if not name or len(name) < 2 or len(name) > 60:
        return False

    # 완전 일치 UI 단어 차단
    if name.lower() in _UI_WORDS or name in _UI_WORDS:
        return False

    # 내비게이션 접미사 차단 ("~ 바로가기" 등)
    if any(name.endswith(s) for s in _KO_NOT_BRAND_SUFFIX):
        return False

    # 한글 포함 여부
    ko_chars = sum(1 for c in name if "\uAC00" <= c <= "\uD7A3")
    if ko_chars >= 2:
        # 동사·조사 패턴 → UI 텍스트
        if _KO_NOT_BRAND_RE.search(name):
            return False
        # 공백 있는 긴 한글 → UI 문장
        if " " in name and ko_chars > 6:
            return False

    return True


class BrandCrawler(BaseCrawler):
    """판매채널에서 브랜드 목록을 추출하는 크롤러"""

    async def crawl_channel(self, channel_url: str) -> ChannelCrawlResult:
        """채널 URL에서 브랜드 목록 추출"""
        result = ChannelCrawlResult(channel_url=channel_url)
        strategy = self._find_strategy(channel_url)

        try:
            if strategy:
                brands = await self._crawl_with_strategy(channel_url, strategy)
                result.crawl_strategy = "custom"
            else:
                brands, strat_name = await self._crawl_generic(channel_url)
                result.crawl_strategy = strat_name

            result.brands = brands
            logger.info(
                f"[{channel_url}] {len(brands)}개 브랜드 추출 ({result.crawl_strategy})"
            )

        except Exception as e:
            result.error = str(e)
            logger.error(f"[{channel_url}] 크롤링 실패: {e}")

        return result

    def _find_strategy(self, channel_url: str) -> dict | None:
        for domain, strategy in CHANNEL_STRATEGIES.items():
            if domain in channel_url:
                return strategy
        return None

    async def _crawl_with_strategy(
        self, channel_url: str, strategy: dict
    ) -> list[BrandInfo]:
        """커스텀 전략으로 브랜드 추출"""
        target_url = strategy.get("brand_list_url", channel_url)
        page = await self.fetch_page(target_url)
        try:
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            elements = soup.select(strategy["brand_selector"])
            brands = []
            for el in elements:
                name = el.get_text(strip=True)
                href = el.get("href", "")
                if _is_valid_brand_name(name):
                    brands.append(
                        BrandInfo(
                            name=self._clean_brand_name(name),
                            url=href if href.startswith("http") else None,
                            source_channel_url=channel_url,
                        )
                    )
            return self._deduplicate_brands(brands)
        finally:
            await page.close()

    async def _crawl_generic(
        self, channel_url: str
    ) -> tuple[list[BrandInfo], str]:
        """
        범용 전략 (우선순위):
        1. Shopify /products.json API  — vendor 필드로 정확한 브랜드 추출
        2. Cafe24 카테고리 링크 분석  — cate_no 파라미터 필터링
        3. /brand, /brands 등 전용 페이지 HTML 파싱
        4. 홈페이지 네비게이션 분석 (최후 fallback)
        """
        # 1. Shopify API 시도
        brands = await self._try_shopify_api(channel_url)
        if brands:
            return brands, "shopify"

        # 2. Cafe24 전략 시도
        brands = await self._try_cafe24_brands(channel_url)
        if brands:
            return brands, "cafe24"

        # 3. 브랜드 전용 경로 시도
        # 200개 초과 시 제품 개별 링크까지 긁힌 것으로 판단 → 스킵
        BRAND_PAGE_MAX = 200
        for path in ["/brand", "/brands", "/brand-list", "/designer", "/designers"]:
            try:
                test_url = channel_url.rstrip("/") + path
                page = await self.fetch_page(test_url)
                brands = await self._extract_brands_from_page(page, channel_url)
                await page.close()
                if brands and len(brands) <= BRAND_PAGE_MAX:
                    logger.info(f"브랜드 페이지 발견: {test_url}")
                    return brands, "brand-page"
                if len(brands) > BRAND_PAGE_MAX:
                    logger.warning(
                        f"brand-page 결과 과다 ({len(brands)}개 > {BRAND_PAGE_MAX}), "
                        "제품 링크 혼입 의심 → navigation fallback"
                    )
            except Exception:
                continue

        # 4. 홈페이지 네비게이션 분석
        page = await self.fetch_page(channel_url)
        brands = await self._extract_brands_from_navigation(page, channel_url)
        await page.close()
        return brands, "navigation"

    async def _try_cafe24_brands(self, channel_url: str) -> list[BrandInfo]:
        """
        Cafe24 스토어의 브랜드 카테고리 링크 추출.

        Cafe24 브랜드 카테고리 링크: href에 cate_no= 포함, product_no= 미포함.
        제품 상세 링크: href에 product_no= 포함 → 필터링으로 제품 링크 배제.
        """
        for path in ["/brand", "/brands", "/brand/list.html"]:
            page = await self.fetch_page(channel_url.rstrip("/") + path)
            try:
                html = await page.content()

                # Cafe24 스토어 여부 확인 (JavaScript 변수 또는 도메인 참조)
                if "cafe24" not in html.lower() and "ec_front" not in html.lower():
                    return []

                soup = BeautifulSoup(html, "html.parser")
                brands: list[BrandInfo] = []

                for link in soup.find_all("a", href=True):
                    href: str = link.get("href", "")
                    text = link.get_text(strip=True)

                    # 브랜드 카테고리 링크 조건:
                    #   - cate_no= 포함 (카테고리 페이지)
                    #   - product_no= 미포함 (상품 상세 제외)
                    is_category_link = (
                        "cate_no=" in href and "product_no=" not in href
                    )
                    if is_category_link and _is_valid_brand_name(text):
                        brands.append(
                            BrandInfo(
                                name=self._clean_brand_name(text),
                                url=href,
                                source_channel_url=channel_url,
                            )
                        )

                brands = self._deduplicate_brands(brands)
                if brands:
                    logger.info(
                        f"Cafe24 브랜드 페이지 발견: {channel_url}{path} "
                        f"({len(brands)}개)"
                    )
                    return brands

            except Exception as e:
                logger.debug(f"Cafe24 전략 실패 ({path}): {e}")
            finally:
                await page.close()

        return []

    async def _try_shopify_api(self, channel_url: str) -> list[BrandInfo]:
        """
        Shopify /products.json API로 vendor(브랜드) 추출.
        모든 Shopify 스토어에서 사용 가능한 공개 엔드포인트.
        최대 8페이지(2000개 상품)를 순회하여 고유 vendor를 수집.
        """
        vendors: set[str] = set()
        page_num = 1
        max_pages = 8

        while page_num <= max_pages:
            api_url = (
                f"{channel_url.rstrip('/')}/products.json"
                f"?limit=250&page={page_num}"
            )
            page = await self.fetch_page(api_url)
            try:
                raw = await page.evaluate("document.body.innerText")
                data = json.loads(raw)
                products = data.get("products", [])
                if not products:
                    break
                for p in products:
                    v = p.get("vendor", "").strip()
                    if v:
                        vendors.add(v)
                if len(products) < 250:
                    break
                page_num += 1
            except (json.JSONDecodeError, KeyError):
                # Shopify 스토어가 아님 → 조용히 종료
                break
            finally:
                await page.close()

        return [
            BrandInfo(name=v, source_channel_url=channel_url)
            for v in sorted(vendors)
            if _is_valid_brand_name(v)
        ]

    async def _extract_brands_from_page(
        self, page: Page, source_url: str
    ) -> list[BrandInfo]:
        """페이지 내 브랜드 링크 추출"""
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        brand_containers = soup.select(
            "[class*='brand'], [id*='brand'], [class*='designer'], [id*='designer']"
        )
        brands = []
        for container in brand_containers:
            for link in container.find_all("a"):
                name = link.get_text(strip=True)
                if _is_valid_brand_name(name):
                    brands.append(
                        BrandInfo(
                            name=self._clean_brand_name(name),
                            url=link.get("href"),
                            source_channel_url=source_url,
                        )
                    )
        return self._deduplicate_brands(brands)

    async def _extract_brands_from_navigation(
        self, page: Page, source_url: str
    ) -> list[BrandInfo]:
        """홈페이지 네비게이션에서 브랜드 링크 탐색"""
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        nav_elements = soup.find_all(["nav", "header", "ul"], recursive=True)
        brands = []
        for nav in nav_elements:
            for link in nav.find_all("a"):
                text = link.get_text(strip=True)
                href = link.get("href", "")
                if re.search(r"/brand|/designer", href, re.I) and _is_valid_brand_name(text):
                    brands.append(
                        BrandInfo(
                            name=self._clean_brand_name(text),
                            url=href,
                            source_channel_url=source_url,
                        )
                    )
        return self._deduplicate_brands(brands)

    @staticmethod
    def _clean_brand_name(name: str) -> str:
        """브랜드명 정규화"""
        name = re.sub(r"\s+", " ", name).strip()
        # 괄호 안 부가정보 제거: "Nike (나이키)" → "Nike"
        name = re.sub(r"\s*\([^)]*\)\s*", "", name).strip()
        return name

    @staticmethod
    def _deduplicate_brands(brands: list[BrandInfo]) -> list[BrandInfo]:
        """이름 기준 중복 제거"""
        seen: set[str] = set()
        result = []
        for b in brands:
            key = b.name.lower()
            if key and key not in seen:
                seen.add(key)
                result.append(b)
        return result
