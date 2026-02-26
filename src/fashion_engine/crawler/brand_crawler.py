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
    "8division.com": {
        "brand_list_url": "https://www.8division.com/product/maker.html",
        "brand_selector": "ul.sub-menu.sub-menu-brands > li > a[href*='cate_no=']",
        "name_selector": None,
        "href_must_contain": ["cate_no="],
        "href_must_not_contain": ["product_no="],
    },
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
    "kasina.co.kr": {
        "brand_list_url": "https://www.kasina.co.kr/product/maker.html",
        "brand_selector": "a[href*='cate_no='], a[href*='/product/list.html']",
        "name_selector": None,
        "href_must_contain": ["cate_no="],
        "href_must_not_contain": ["product_no="],
    },
    "thexshop.co.kr": {
        "brand_list_url": "https://www.thexshop.co.kr/product/maker.html",
        "brand_selector": "a[href*='cate_no='], a[href*='/product/list.html']",
        "name_selector": None,
        "href_must_contain": ["cate_no="],
        "href_must_not_contain": ["product_no="],
    },
    "unipair.com": {
        "brand_list_url": "https://www.unipair.com/product/maker.html",
        "brand_selector": "a[href*='cate_no='], a[href*='/product/list.html']",
        "name_selector": None,
        "href_must_contain": ["cate_no="],
        "href_must_not_contain": ["product_no="],
    },
    "parlour.kr": {
        "brand_list_url": "https://www.parlour.kr/product/maker.html",
        "brand_selector": "a[href*='cate_no='], a[href*='/product/list.html']",
        "name_selector": None,
        "href_must_contain": ["cate_no="],
        "href_must_not_contain": ["product_no="],
    },
    "obscura-store.com": {
        "brand_list_url": "https://www.obscura-store.com/product/maker.html",
        "brand_selector": "a[href*='cate_no='], a[href*='/product/list.html']",
        "name_selector": None,
        "href_must_contain": ["cate_no="],
        "href_must_not_contain": ["product_no="],
    },
    "bizzare.co.kr": {
        "brand_list_url": "https://www.bizzare.co.kr/product/maker.html",
        "brand_selector": "a[href*='cate_no='], a[href*='/product/list.html']",
        "name_selector": None,
        "href_must_contain": ["cate_no="],
        "href_must_not_contain": ["product_no="],
    },
    "ecru.co.kr": {
        "brand_list_url": "https://www.ecru.co.kr/product/maker.html",
        "brand_selector": "a[href*='cate_no='], a[href*='/product/list.html']",
        "name_selector": None,
        "href_must_contain": ["cate_no="],
        "href_must_not_contain": ["product_no="],
    },
    "rinostore.co.kr": {
        "brand_list_url": "https://www.rinostore.co.kr/product/maker.html",
        "brand_selector": "a[href*='cate_no='], a[href*='/product/list.html']",
        "name_selector": None,
        "href_must_contain": ["cate_no="],
        "href_must_not_contain": ["product_no="],
    },
    "coevo.com": {
        "brand_list_url": "https://www.coevo.com/product/maker.html",
        "brand_selector": "a[href*='cate_no='], a[href*='/product/list.html']",
        "name_selector": None,
        "href_must_contain": ["cate_no="],
        "href_must_not_contain": ["product_no="],
    },
    "gooutstore.cafe24.com": {
        "brand_list_url": "https://gooutstore.cafe24.com/product/maker.html",
        "brand_selector": "a[href*='cate_no='], a[href*='/product/list.html']",
        "name_selector": None,
        "href_must_contain": ["cate_no="],
        "href_must_not_contain": ["product_no="],
    },
    "effortless-store.com": {
        "brand_list_url": "https://www.effortless-store.com/product/maker.html",
        "brand_selector": "a[href*='cate_no='], a[href*='/product/list.html']",
        "name_selector": None,
        "href_must_contain": ["cate_no="],
        "href_must_not_contain": ["product_no="],
    },
}

# DNS/SSL 이슈 채널 대체 URL 후보.
# 첫 URL이 실패하면 순차 시도한다.
CHANNEL_URL_FALLBACKS: dict[str, list[str]] = {
    "store.doverstreetmarket.com": [
        "https://shop-us.doverstreetmarket.com",
        "https://shop.doverstreetmarket.com",
    ],
    "kerouac.okinawa": [
        "http://www.kerouac.okinawa",
        "http://kerouac.okinawa",
    ],
    "tune.kr": [
        "http://www.tune.kr",
        "http://tune.kr",
    ],
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
        # Cafe24 카테고리 헤더 (의류·액세서리 분류 → 브랜드 아님)
        "신상품", "온라인샵", "라이프스타일", "슈케어", "개인결제창",
        "상의", "아우터", "하의", "벨트", "주얼리", "악세사리",
        "모자", "신발", "가방", "세일", "sale items",
    }
)

# 브랜드명 끝에 올 수 없는 한국어 접미사
_KO_NOT_BRAND_SUFFIX = ("바로가기", "더보기", "전체보기", "상품보기", "세일")

# 콜라보 서브카테고리 패턴: " by ", " x ", " X ", " × " 가 단어 경계로 포함된 긴 이름
# 예: "Adidas Originals by Wales Bonner", "Fred Perry X Raf Simons"
_COLLAB_RE = re.compile(r"(?i)\s+(?:by|x|×)\s+")


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

    # 콜라보 서브카테고리 차단: " by ", " x ", " X " 포함 + 길이 > 25자
    # 예: "Adidas Originals by Wales Bonner", "Fred Perry X Raf Simons"
    if len(name) > 40 and _COLLAB_RE.search(name):
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
        last_error: str | None = None

        for candidate_url in self._resolve_candidate_urls(channel_url):
            strategy = self._find_strategy(candidate_url)
            try:
                if strategy:
                    brands = await self._crawl_with_strategy(candidate_url, strategy)
                    crawl_strategy = "custom"
                else:
                    brands, crawl_strategy = await self._crawl_generic(candidate_url)

                # fallback URL에서 성공하면 즉시 확정
                result.brands = brands
                if candidate_url != channel_url:
                    result.crawl_strategy = f"{crawl_strategy}+fallback"
                    logger.info(
                        f"[{channel_url}] fallback 성공: {candidate_url} ({len(brands)}개)"
                    )
                else:
                    result.crawl_strategy = crawl_strategy

                logger.info(
                    f"[{channel_url}] {len(brands)}개 브랜드 추출 ({result.crawl_strategy})"
                )
                return result
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[{channel_url}] 후보 URL 실패: {candidate_url} ({e})")
                continue

        result.error = last_error
        logger.error(f"[{channel_url}] 크롤링 실패: {last_error}")

        return result

    def _find_strategy(self, channel_url: str) -> dict | None:
        for domain, strategy in CHANNEL_STRATEGIES.items():
            if domain in channel_url:
                return strategy
        return None

    def _resolve_candidate_urls(self, channel_url: str) -> list[str]:
        candidates = [channel_url]
        for domain, urls in CHANNEL_URL_FALLBACKS.items():
            if domain in channel_url:
                for alt in urls:
                    if alt not in candidates:
                        candidates.append(alt)
                break
        return candidates

    async def _crawl_with_strategy(
        self, channel_url: str, strategy: dict
    ) -> list[BrandInfo]:
        """커스텀 전략으로 브랜드 추출"""
        target_url = strategy.get("brand_list_url", channel_url)
        href_must_contain: list[str] = strategy.get("href_must_contain", [])
        href_must_not_contain: list[str] = strategy.get("href_must_not_contain", [])
        page = await self.fetch_page(target_url)
        try:
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            elements = soup.select(strategy["brand_selector"])
            brands = []
            for el in elements:
                name = el.get_text(strip=True)
                href = el.get("href", "")
                if href_must_contain and not any(token in href for token in href_must_contain):
                    continue
                if href_must_not_contain and any(token in href for token in href_must_not_contain):
                    continue
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
                    continue

                soup = BeautifulSoup(html, "html.parser")
                brands: list[BrandInfo] = []

                # depth1 nav만 탐색: Cafe24 표준 네비게이션 최상위 레벨
                # 없으면 전체 <a> 탐색으로 fallback
                nav_roots = soup.select(
                    "ul.xans-layout-navigation > li, "
                    "ul.depth1 > li, "
                    "ul.menuCategory > li, "
                    "nav > ul > li"
                )
                if nav_roots:
                    # 각 li의 직계 자식 <a>만 추출 (하위 ul 제외)
                    candidate_links = [
                        li.find("a", href=True, recursive=False)
                        for li in nav_roots
                        if li.find("a", href=True, recursive=False)
                    ]
                else:
                    # 브랜드 페이지 내 카테고리 링크만 제한적으로 탐색
                    candidate_links = soup.select(
                        "a[href*='cate_no=']:not([href*='product_no='])"
                    )

                seen_cate_nos: set[str] = set()
                for link in candidate_links:
                    href: str = link.get("href", "")
                    text = link.get_text(strip=True)

                    # 브랜드 카테고리 링크 조건:
                    #   - cate_no= 포함 (카테고리 페이지)
                    #   - product_no= 미포함 (상품 상세 제외)
                    is_category_link = (
                        "cate_no=" in href and "product_no=" not in href
                    )
                    if not is_category_link or not _is_valid_brand_name(text):
                        continue

                    # cate_no 기준 URL 중복 제거
                    # 동일 브랜드의 영문/한글 표기 + 세일 섹션 중복 방지
                    cate_match = re.search(r"cate_no=(\d+)", href)
                    if cate_match:
                        cate_no = cate_match.group(1)
                        if cate_no in seen_cate_nos:
                            continue
                        seen_cate_nos.add(cate_no)

                    brands.append(
                        BrandInfo(
                            name=self._clean_brand_name(text),
                            url=href,
                            source_channel_url=channel_url,
                        )
                    )

                brands = self._deduplicate_brands(brands)

                # 500개 초과 시 잡음 혼입으로 판단 → 스킵 (8DIVISION 등 대형 편집샵 400+ 허용)
                CAFE24_MAX = 500
                if len(brands) > CAFE24_MAX:
                    logger.warning(
                        f"Cafe24 결과 과다 ({len(brands)}개 > {CAFE24_MAX}), "
                        f"서브카테고리 혼입 의심 → fallback"
                    )
                    continue

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
            try:
                page = await self.fetch_page(api_url)
            except Exception:
                # Shopify API 접근 실패 시 범용 fallback으로 진행
                break
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
