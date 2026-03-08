"""
채널별 제품·가격 크롤러.

Shopify /products.json (공개 REST API) 기반으로 제품 목록과 가격을 수집.
Playwright 불필요 — httpx 직접 사용.
"""
import asyncio
import json
import logging
import random
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from slugify import slugify
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from fashion_engine.crawler.product_classifier import classify_gender_and_subcategory

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    """429/503은 재시도 대상; 일반 HTTPError도 재시도."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 503)
    return isinstance(exc, httpx.HTTPError)


# 국가 코드 → 통화 코드 매핑
COUNTRY_CURRENCY: dict[str, str] = {
    "KR": "KRW",
    "JP": "JPY",
    "US": "USD",
    "UK": "GBP",
    "GB": "GBP",
    "DE": "EUR",
    "FR": "EUR",
    "IT": "EUR",
    "ES": "EUR",
    "NL": "EUR",
    "DK": "DKK",
    "SE": "SEK",
    "HK": "HKD",
    "SG": "SGD",
    "CA": "CAD",
    "AU": "AUD",
    "TW": "TWD",
    "CN": "CNY",
}

# Shopify 제품 크롤 시 최대 페이지 수 (250개/페이지 × 16 = 최대 4000개)
SHOPIFY_MAX_PAGES = 40

_BROWSER_HEADERS: dict[str, str] = {
    "Accept": "application/json, text/html, */*;q=0.8",
    # Accept-Language 제거: 헤더 존재만으로 Shopify Markets가 KRW 로컬라이즈 가격을
    # 반환하는 버그 유발 (한국 IP + Accept-Language → markets/KRW 전환)
    # Accept-Encoding 제거: httpx가 자동으로 설정 + 자동 해제함
    # 수동 설정 시 httpx의 자동 압축 해제가 비활성화되어 gzip 파싱 실패
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

_SHOPIFY_GLOBAL_SEM: asyncio.Semaphore | None = None
_CAFE24_CATEGORY_SEM: asyncio.Semaphore | None = None

_URL_PLATFORM_MAP: dict[str, str] = {
    "shop-pro.jp": "makeshop",
    "buyshop.jp": "stores-jp",
    "theshop.jp": "stores-jp",
    "stores.jp": "stores-jp",
    "ocnk.net": "ochanoko",
    "cafe24.com": "cafe24",
    "echosting.com": "cafe24",
    "base.shop": "base-jp",
    "thebase.in": "base-jp",
}


def _get_shopify_sem() -> asyncio.Semaphore:
    global _SHOPIFY_GLOBAL_SEM
    if _SHOPIFY_GLOBAL_SEM is None:
        _SHOPIFY_GLOBAL_SEM = asyncio.Semaphore(2)
    return _SHOPIFY_GLOBAL_SEM


def _get_cafe24_category_sem() -> asyncio.Semaphore:
    global _CAFE24_CATEGORY_SEM
    if _CAFE24_CATEGORY_SEM is None:
        _CAFE24_CATEGORY_SEM = asyncio.Semaphore(5)
    return _CAFE24_CATEGORY_SEM

# ── 모델코드 추출용 정규식 ──────────────────────────────────────────────
# 3자리 이상 숫자 포함 (M2002R, DD9336, GZ6094, NMD_R1 등)
_MODEL_CODE_RE = re.compile(r'\b([A-Z]{1,3}[0-9]{3,}[A-Z0-9]{0,6})\b')
# 1~2자리 숫자 포함 (AJ1, AF1, AM90, AM95 등 짧은 코드)
_SHORT_CODE_RE = re.compile(r'\b([A-Z]{2,4}[0-9]{1,2})\b')
# 사이즈·시즌 코드 제외 (EU40, FW23 등 오탐 방지)
_EXCLUDE_PREFIXES = frozenset(["EU", "UK", "US", "JP", "CM", "FW", "SS", "AW", "SP"])

# ── 비패션 제품 거부 목록 ────────────────────────────────────────────────────
_VENDOR_DENYLIST: frozenset[str] = frozenset({
    "route",
    "routeins",
    "extend",
    "clyde",
    "seel",
})

_TITLE_KEYWORD_DENYLIST: frozenset[str] = frozenset({
    "shipping protection",
    "package protection",
    "gift card",
    "gift certificate",
    "e-gift card",
    "digital gift",
    "warranty protection",
    "product protection",
    "return assurance",
    "sold out",   # Cafe24 SOLD OUT 플레이스홀더 (예: THEXSHOP)
    "품절",       # 한국어 품절 플레이스홀더
})

_PRODUCT_TYPE_DENYLIST: frozenset[str] = frozenset({
    "gift cards",
    "gift card",
    "services",
    "insurance",
    "warranty",
})

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


@dataclass
class ProductInfo:
    title: str
    vendor: str          # 브랜드명 (Shopify vendor 필드)
    handle: str          # Shopify product slug
    product_type: str | None
    price: float         # 현재가 (세일가 포함)
    compare_at_price: float | None  # 정가 (세일 중일 때)
    currency: str        # 채널 통화 (국가 코드 기반 추론)
    sku: str | None
    image_url: str | None
    tags: str | None
    product_url: str     # 채널 내 제품 URL
    product_key: str     # "brand-slug:handle" 교차 채널 매칭용
    is_available: bool   # 재고/판매 가능 여부 (품절 표시용)
    gender: str | None = None
    subcategory: str | None = None
    normalized_key: str | None = None    # "brand-slug:model-code" 교차채널 매칭용
    match_confidence: float | None = None  # normalized_key 생성 신뢰도 (0.0~1.0)
    size_availability: list[dict] | None = None  # [{"size": "M", "in_stock": true}, ...]


@dataclass
class ChannelProductResult:
    channel_url: str
    products: list[ProductInfo] = field(default_factory=list)
    error: str | None = None
    error_type: str | None = None
    crawl_strategy: str = "unknown"


class ProductCrawler:
    """Shopify 채널 제품·가격 크롤러"""

    def __init__(self, request_delay: float = 1.0, timeout: float = 15.0):
        self._delay = request_delay
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "ProductCrawler":
        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "application/json",
            },
            follow_redirects=True,
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0),
        )
        return self

    async def __aexit__(self, *args) -> None:
        if self._client:
            await self._client.aclose()

    # ── 공개 인터페이스 ──────────────────────────────────────────────────

    async def _get_shopify_currency(self, base_url: str) -> str | None:
        """Shopify /shop.json에서 실제 통화 코드 조회."""
        try:
            resp = await self._fetch_with_retry(f"{base_url.rstrip('/')}/shop.json", timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("shop", {}).get("currency")
        except Exception:
            pass
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    async def _fetch_with_retry(self, url: str, timeout: float | None = None) -> httpx.Response:
        assert self._client is not None
        headers = {"User-Agent": random.choice(USER_AGENTS), **_BROWSER_HEADERS}
        response = await self._client.get(url, headers=headers, timeout=timeout)
        # 429 Rate Limit — Retry-After 헤더 준수
        if response.status_code == 429:
            retry_after = float(response.headers.get("Retry-After", "5"))
            logger.warning("Rate limited by %s — waiting %.1fs", url, retry_after)
            await asyncio.sleep(retry_after)
        response.raise_for_status()
        return response

    @staticmethod
    def _infer_currency(channel_url: str, country: str | None) -> str:
        """URL 서브도메인 + 국가 코드에서 통화 추론.
        Shopify 다국어 스토어는 kr., jp. 등의 서브도메인을 사용함.
        """
        host = urlparse(channel_url).netloc.lower()
        # 서브도메인 기반 통화 매핑
        SUBDOMAIN_CURRENCY = {
            "kr": "KRW", "jp": "JPY", "eu": "EUR",
            "de": "EUR", "fr": "EUR", "uk": "GBP",
            "us": "USD", "au": "AUD", "cn": "CNY",
            "hk": "HKD", "sg": "SGD", "ca": "CAD",
        }
        prefix = host.split(".")[0]
        if prefix in SUBDOMAIN_CURRENCY:
            return SUBDOMAIN_CURRENCY[prefix]
        country_code = (country or "").upper()
        inferred = COUNTRY_CURRENCY.get(country_code)
        if inferred:
            return inferred

        logger.warning(
            "알 수 없는 통화: url=%s country=%s -> USD fallback 적용",
            channel_url,
            country_code or "-",
        )
        return "USD"

    @staticmethod
    def _detect_platform_from_url(channel_url: str) -> str | None:
        host = urlparse(channel_url).netloc.lower()
        for pattern, platform in _URL_PLATFORM_MAP.items():
            if pattern in host:
                return platform
        return None

    async def crawl_channel(
        self,
        channel_url: str,
        country: str | None = None,
        cafe24_brand_categories: list[tuple[str, str]] | None = None,
        new_only: bool = False,
        channel_platform: str | None = None,
        use_gpt_parser: bool = False,
    ) -> ChannelProductResult:
        """채널 URL에서 전체 제품 목록 수집."""
        await asyncio.sleep(random.uniform(0, 3))
        currency = self._infer_currency(channel_url, country)
        result = ChannelProductResult(channel_url=channel_url)

        try:
            shopify_currency = await self._get_shopify_currency(channel_url)
            if shopify_currency:
                currency = shopify_currency.upper()
            if new_only:
                products = await self._try_shopify_new_products(channel_url, currency)
                if products:
                    result.products = products
                    result.crawl_strategy = "shopify-new-json"
                else:
                    result.error = "No products found via Shopify /products/new.json"
                    result.error_type = "zero_products"
                return result

            products = await self._try_shopify_products(channel_url, currency)
            if products:
                result.products = products
                result.crawl_strategy = "shopify-api"
            else:
                categories = list(cafe24_brand_categories or [])
                if not categories:
                    categories = await self._discover_cafe24_brand_categories(channel_url)
                cafe24_products: list[ProductInfo] = []
                if categories:
                    sem = _get_cafe24_category_sem()

                    async def _fetch_one(brand_name: str, cate_no: str) -> list[ProductInfo]:
                        async with sem:
                            return await self._try_cafe24_products(
                                channel_url=channel_url,
                                cate_no=cate_no,
                                brand_name=brand_name,
                                currency=currency,
                            )

                    gathered = await asyncio.gather(
                        *[_fetch_one(name, cate_no) for name, cate_no in categories],
                        return_exceptions=True,
                    )
                    for row in gathered:
                        if isinstance(row, list):
                            cafe24_products.extend(row)
                if cafe24_products:
                    dedup: dict[str, ProductInfo] = {}
                    for p in cafe24_products:
                        dedup[p.product_url] = p
                    result.products = list(dedup.values())
                    result.crawl_strategy = "cafe24-html"
                else:
                    detected_platform = self._detect_platform_from_url(channel_url)
                    platform_hint = channel_platform or detected_platform
                    single_brand_products = await self._try_cafe24_single_brand(
                        channel_url=channel_url,
                        currency=currency,
                    )
                    if single_brand_products:
                        result.products = single_brand_products
                        result.crawl_strategy = "cafe24-single-brand"
                        return result
                    if await self._try_woocommerce_detect(channel_url):
                        wc_products = await self._try_woocommerce_products(channel_url, currency)
                        if wc_products:
                            result.products = wc_products
                            result.crawl_strategy = "woocommerce-api"
                        else:
                            result.error = (
                                "No products found "
                                "(non-Shopify/Cafe24/WooCommerce/MakeShop/STORES.jp or empty store)"
                            )
                            result.error_type = "not_supported"
                    else:
                        extra_products: list[ProductInfo] = []
                        extra_strategy = "unknown"
                        if detected_platform == "makeshop":
                            extra_products = await self._try_makeshop_products(channel_url, currency)
                            extra_strategy = "makeshop-html"
                        elif detected_platform == "stores-jp":
                            extra_products = await self._try_stores_jp_products(channel_url, currency)
                            extra_strategy = "stores-jp-html"
                        elif detected_platform == "ochanoko":
                            extra_products = await self._try_ochanoko_products(channel_url, currency)
                            extra_strategy = "ochanoko-html"

                        if extra_products:
                            result.products = extra_products
                            result.crawl_strategy = extra_strategy
                        else:
                            should_try_gpt = bool(use_gpt_parser or platform_hint in (None, "", "unknown"))
                            if should_try_gpt:
                                gpt_products = await self._try_gpt_parser_products(channel_url, currency)
                                if gpt_products:
                                    result.products = gpt_products
                                    result.crawl_strategy = "gpt-parser"
                                else:
                                    result.error = (
                                        "No products found "
                                        "(non-Shopify/Cafe24/WooCommerce/MakeShop/STORES.jp or GPT fallback empty)"
                                    )
                                    result.error_type = "not_supported"
                            else:
                                result.error = (
                                    "No products found "
                                    "(non-Shopify/Cafe24/WooCommerce/MakeShop/STORES.jp or empty store)"
                                )
                                result.error_type = "not_supported"
        except Exception as e:
            result.error = str(e)[:200]
            http_status = e.response.status_code if isinstance(e, httpx.HTTPStatusError) else None
            result.error_type = self._classify_error(e, http_status)
            logger.warning(f"제품 크롤 실패 [{channel_url}]: {e}")

        return result

    # ── Shopify 전략 ─────────────────────────────────────────────────────

    async def _try_shopify_products(
        self, channel_url: str, currency: str
    ) -> list[ProductInfo]:
        """
        Shopify /products.json?limit=100&page=N 순회.
        최대 SHOPIFY_MAX_PAGES 페이지.
        """
        assert self._client is not None
        base = channel_url.rstrip("/")
        products: list[ProductInfo] = []
        shopify_sem = _get_shopify_sem()

        for page in range(1, SHOPIFY_MAX_PAGES + 1):
            url = f"{base}/products.json?limit=100&page={page}"
            try:
                async with shopify_sem:
                    resp = await self._fetch_with_retry(url)
                    data = resp.json()
            except Exception:
                break

            page_products = data.get("products", [])
            if not page_products:
                break

            for p in page_products:
                info = self._parse_product(p, base, currency)
                if info:
                    products.append(info)

            await asyncio.sleep(self._delay)

            if len(page_products) < 100:
                break

        return products

    async def _try_shopify_new_products(
        self,
        channel_url: str,
        currency: str,
    ) -> list[ProductInfo]:
        """Shopify 신규 상품 목록 전용 엔드포인트를 1회 조회한다."""
        assert self._client is not None
        base = channel_url.rstrip("/")
        url = f"{base}/products/new.json?limit=100&page=1"
        shopify_sem = _get_shopify_sem()

        try:
            async with shopify_sem:
                resp = await self._fetch_with_retry(url)
                data = resp.json()
        except Exception:
            return []

        page_products = data.get("products", [])
        products: list[ProductInfo] = []
        for p in page_products:
            info = self._parse_product(p, base, currency)
            if info:
                products.append(info)
        return products

    async def _discover_cafe24_brand_categories(
        self,
        channel_url: str,
    ) -> list[tuple[str, str]]:
        """Cafe24 브랜드 카테고리(cate_no) 자동 탐지."""
        assert self._client is not None
        base = channel_url.rstrip("/")
        candidates = [
            f"{base}/product/maker.html",
            f"{base}/product/brand.html",
            f"{base}/brands2.html",
            f"{base}/product/list-brand.html",
            f"{base}/product/list.html?cate_no=1",
            f"{base}/category/brand/42/",
        ]
        found_by_cate: dict[str, str] = {}
        for url in candidates:
            try:
                resp = await self._client.get(url, timeout=self._timeout)
                if resp.status_code != 200:
                    continue
            except Exception:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("a[href*='cate_no=']:not([href*='product_no='])"):
                href = a.get("href") or ""
                m = re.search(r"cate_no=(\d+)", href)
                if not m:
                    continue
                cate_no = m.group(1)
                name = a.get_text(" ", strip=True)
                if not name:
                    continue
                found_by_cate[cate_no] = name
        return [(name, cate_no) for cate_no, name in found_by_cate.items()]

    async def _try_cafe24_products(
        self,
        channel_url: str,
        cate_no: str,
        brand_name: str,
        currency: str,
    ) -> list[ProductInfo]:
        """Cafe24 카테고리 목록 페이지를 순회해 제품 정보를 파싱한다."""
        assert self._client is not None
        base = channel_url.rstrip("/")
        brand_slug = slugify(brand_name) if brand_name else "unknown"
        products: list[ProductInfo] = []
        seen: set[str] = set()

        for page in range(1, 80):
            list_url = f"{base}/product/list.html?cate_no={cate_no}&page={page}"
            try:
                resp: httpx.Response | None = None
                for attempt in range(3):
                    resp = await self._client.get(list_url, timeout=self._timeout)
                    if resp.status_code == 429:
                        retry_after = int(resp.headers.get("Retry-After", "10"))
                        logger.warning("Cafe24 429: %s, retry after %ss", list_url, retry_after)
                        await asyncio.sleep(retry_after)
                        continue
                    if resp.status_code == 503:
                        wait = 5 * (attempt + 1)
                        logger.warning("Cafe24 503: %s, retry after %ss", list_url, wait)
                        await asyncio.sleep(wait)
                        continue
                    break
                if resp is None or resp.status_code != 200:
                    break
            except Exception:
                break

            page_products = self._parse_cafe24_product_list(
                html=resp.text,
                channel_url=channel_url,
                currency=currency,
                brand_name=brand_name,
                seen_product_nos=seen,
            )
            page_count = len(page_products)
            if page_count:
                products.extend(page_products)

            if page_count == 0:
                break
            await asyncio.sleep(self._delay)

        return products

    def _parse_cafe24_product_list(
        self,
        *,
        html: str,
        channel_url: str,
        currency: str,
        brand_name: str | None,
        seen_product_nos: set[str] | None = None,
    ) -> list[ProductInfo]:
        """Cafe24 목록 페이지 HTML 공통 파서."""
        base = channel_url.rstrip("/")
        vendor = (brand_name or urlparse(channel_url).netloc.replace("www.", "")).strip() or "unknown"
        brand_slug = slugify(vendor) if vendor else "unknown"
        seen = seen_product_nos if seen_product_nos is not None else set()

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(
            "li[id^='anchorBoxId_'], ul.prdList > li, .xans-product-listnormal li, "
            ".xans-product-listitem li, .prdList.grid4 > li"
        )
        if not cards:
            return []

        out: list[ProductInfo] = []
        for card in cards:
            a = card.select_one(
                "a[href*='product_no='], .name a, .description .name a, p.name a"
            )
            if not a:
                continue
            href = (a.get("href") or "").strip()
            m = re.search(r"product_no=(\d+)", href)
            if not m:
                continue
            product_no = m.group(1)
            if product_no in seen:
                continue
            seen.add(product_no)

            title = a.get_text(" ", strip=True)
            if not title:
                continue

            price_node = card.select_one(
                ".price, .spec li span, li[class*='price'], strong[class*='price']"
            )
            price_text = price_node.get_text(" ", strip=True) if price_node else ""
            nums = re.findall(r"\d[\d,]*", price_text.replace(".", ""))
            if nums:
                try:
                    price = float(nums[0].replace(",", ""))
                except ValueError:
                    continue
                if price <= 0:
                    continue
            else:
                # 가격 없는 listing (룩북·문의 스타일) — 제품 존재는 기록, price=0
                price = 0.0

            # 원가(strike-through) 추출 → compare_at_price 설정으로 세일 감지
            compare_at_price: float | None = None
            orig_node = card.select_one(
                "del, s, .consumer-price, .org_price, .origin-price, "
                ".prd_org_price, .price_del, [class*='origin_price'], "
                "[class*='org-price'], [class*='originalPrice']"
            )
            if orig_node:
                orig_nums = re.findall(r"\d[\d,]*", orig_node.get_text(" ", strip=True).replace(".", ""))
                if orig_nums:
                    try:
                        orig_val = float(orig_nums[0].replace(",", ""))
                        if orig_val > price > 0:
                            compare_at_price = orig_val
                    except ValueError:
                        pass

            img = card.select_one("img")
            image_url = img.get("src") if img else None
            if image_url:
                image_url = urljoin(base + "/", image_url)

            product_url = urljoin(base + "/", href)
            sold_out_badge = card.select_one(
                ".icon-soldout, .soldout, [class*='soldout'], "
                ".sold-out-label, .btn-soldout, [class*='sold-out']"
            )
            if sold_out_badge:
                is_available = False
            else:
                title_lower = title.lower()
                is_available = not (
                    "품절" in title_lower
                    or "sold out" in title_lower
                    or "soldout" in title_lower
                )

            normalized_key, match_confidence = self._build_normalized_key(
                brand_slug=brand_slug,
                sku=None,
                title=title,
                tags=[],
            )
            gender, subcategory = classify_gender_and_subcategory(
                product_type=None,
                title=title,
                tags="",
            )

            out.append(
                ProductInfo(
                    title=title,
                    vendor=vendor,
                    handle=product_no,
                    product_type=None,
                    price=price,
                    compare_at_price=compare_at_price,
                    currency=currency,
                    sku=None,
                    image_url=image_url,
                    tags=None,
                    product_url=product_url,
                    product_key=f"{brand_slug}:{product_no}",
                    is_available=is_available,
                    gender=gender,
                    subcategory=subcategory,
                    normalized_key=normalized_key,
                    match_confidence=match_confidence,
                )
            )
        return out

    async def _try_cafe24_single_brand(
        self,
        channel_url: str,
        currency: str,
    ) -> list[ProductInfo]:
        """Cafe24 단일 브랜드 스토어 목록(/product/list.html) 전략."""
        assert self._client is not None
        base = channel_url.rstrip("/")
        candidates = [
            f"{base}/product/list.html?cate_no=all",
            f"{base}/product/list.html",
            f"{base}/category/main/",
        ]

        working_base: str | None = None
        for candidate in candidates:
            page1 = f"{candidate}&page=1" if "?" in candidate else f"{candidate}?page=1"
            try:
                resp = await self._client.get(page1, timeout=self._timeout)
            except Exception:
                continue
            if resp.status_code != 200:
                continue
            body = resp.text.lower()
            if "xans-product" in body or "cafe24" in body:
                working_base = candidate
                break
        if not working_base:
            return []

        seen: set[str] = set()
        products: list[ProductInfo] = []
        for page in range(1, 101):
            page_url = f"{working_base}&page={page}" if "?" in working_base else f"{working_base}?page={page}"
            try:
                resp = await self._client.get(page_url, timeout=self._timeout)
            except Exception:
                break
            if resp.status_code != 200:
                break
            page_products = self._parse_cafe24_product_list(
                html=resp.text,
                channel_url=channel_url,
                currency=currency,
                brand_name=None,
                seen_product_nos=seen,
            )
            if not page_products:
                break
            products.extend(page_products)
            await asyncio.sleep(self._delay)
        return products

    # ── WooCommerce 전략 ─────────────────────────────────────────────────

    async def _try_woocommerce_detect(self, base_url: str) -> bool:
        """WooCommerce REST API 엔드포인트 존재 확인."""
        assert self._client is not None
        url = f"{base_url.rstrip('/')}/wp-json/wc/v3/"
        try:
            resp = await self._client.get(url, timeout=8)
            return resp.status_code in (200, 401)
        except Exception:
            return False

    async def _try_woocommerce_products(
        self,
        channel_url: str,
        currency: str,
    ) -> list[ProductInfo]:
        """WooCommerce /wp-json/wc/v3/products 페이지네이션 수집."""
        assert self._client is not None
        base_url = channel_url.rstrip("/")
        api_base = f"{base_url}/wp-json/wc/v3/products"
        products: list[ProductInfo] = []
        page = 1
        per_page = 100
        while True:
            url = f"{api_base}?per_page={per_page}&page={page}&status=publish"
            try:
                resp = await self._client.get(url, timeout=self._timeout)
            except httpx.HTTPError:
                break

            if resp.status_code == 401:
                return []
            if resp.status_code != 200:
                break

            try:
                data = resp.json()
            except Exception:
                break
            if not isinstance(data, list) or not data:
                break

            for item in data:
                info = self._parse_woocommerce_product(item, channel_url, currency)
                if info:
                    products.append(info)

            try:
                total_pages = int(resp.headers.get("X-WP-TotalPages", "1"))
            except Exception:
                total_pages = 1
            if page >= total_pages:
                break
            page += 1
            await asyncio.sleep(self._delay)
        return products

    # ── MakeShop / STORES.jp / Ochanoko 전략 ─────────────────────────────

    @staticmethod
    def _extract_price_from_text(text: str) -> float | None:
        nums = re.findall(r"\d[\d,]*", text.replace(".", ""))
        if not nums:
            return None
        try:
            val = float(nums[0].replace(",", ""))
            return val if val > 0 else None
        except Exception:
            return None

    @staticmethod
    def _collect_jsonld_products(node: object, out: list[dict]) -> None:
        if isinstance(node, dict):
            ntype = str(node.get("@type") or "").lower()
            if ntype == "product":
                out.append(node)
            for v in node.values():
                ProductCrawler._collect_jsonld_products(v, out)
        elif isinstance(node, list):
            for v in node:
                ProductCrawler._collect_jsonld_products(v, out)

    async def _crawl_generic_product_cards(
        self,
        channel_url: str,
        currency: str,
        *,
        platform_prefix: str,
        item_selector: str,
        link_selector: str,
        title_selector: str,
        price_selector: str,
        entry_paths: list[str] | None = None,
        max_pages: int = 8,
    ) -> list[ProductInfo]:
        assert self._client is not None
        base = channel_url.rstrip("/")
        host_slug = urlparse(base).netloc.lower().replace("www.", "") or "unknown"
        products: list[ProductInfo] = []
        seen_urls: set[str] = set()

        paths = entry_paths or ["/"]
        for entry in paths:
            entry_url = urljoin(base + "/", entry.lstrip("/"))
            for page in range(1, max_pages + 1):
                page_url = f"{entry_url}?page={page}" if page > 1 else entry_url
                try:
                    resp = await self._client.get(page_url, timeout=self._timeout)
                except Exception:
                    break
                if resp.status_code != 200:
                    break
                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select(item_selector)
                if not cards:
                # 카드 구조가 없는 스킨은 JSON-LD Product 메타데이터를 사용한다.
                    jsonld_products: list[dict] = []
                    for script in soup.select("script[type='application/ld+json']"):
                        raw = (script.string or script.get_text() or "").strip()
                        if not raw:
                            continue
                        try:
                            parsed = json.loads(raw)
                        except Exception:
                            continue
                        self._collect_jsonld_products(parsed, jsonld_products)

                    if not jsonld_products:
                        break

                    page_count = 0
                    for obj in jsonld_products:
                        title = str(obj.get("name") or "").strip()
                        if not title or self._is_title_denied(title):
                            continue
                        offers = obj.get("offers") or {}
                        if isinstance(offers, list):
                            offers = offers[0] if offers else {}
                        price = self._extract_price_from_text(str(offers.get("price") or ""))
                        if price is None:
                            continue
                        raw_url = str(obj.get("url") or "").strip()
                        product_url = urljoin(base + "/", raw_url) if raw_url else page_url
                        if product_url in seen_urls:
                            continue
                        seen_urls.add(product_url)

                        image = obj.get("image")
                        image_url: str | None = None
                        if isinstance(image, list) and image:
                            image_url = str(image[0])
                        elif isinstance(image, str):
                            image_url = image
                        if image_url:
                            image_url = urljoin(base + "/", image_url)

                        fallback_handle = slugify(urlparse(product_url).path, max_length=70)
                        handle = slugify(title, max_length=70) or fallback_handle or "item"
                        vendor_obj = obj.get("brand") or {}
                        vendor = (
                            str(vendor_obj.get("name") or "").strip()
                            if isinstance(vendor_obj, dict)
                            else str(vendor_obj or "").strip()
                        ) or host_slug
                        brand_slug = slugify(vendor) if vendor else "unknown"
                        normalized_key, match_confidence = self._build_normalized_key(
                            brand_slug=brand_slug,
                            sku=None,
                            title=title,
                            tags=[],
                        )
                        gender, subcategory = classify_gender_and_subcategory(
                            product_type=None,
                            title=title,
                            tags="",
                        )
                        products.append(
                            ProductInfo(
                                title=title,
                                vendor=vendor,
                                handle=handle,
                                product_type=None,
                                price=price,
                                compare_at_price=None,
                                currency=currency,
                                sku=None,
                                image_url=image_url,
                                tags=None,
                                product_url=product_url,
                                product_key=f"{platform_prefix}:{host_slug}:{handle}",
                                is_available=True,
                                gender=gender,
                                subcategory=subcategory,
                                normalized_key=normalized_key,
                                match_confidence=match_confidence,
                            )
                        )
                        page_count += 1

                    if page_count == 0:
                        break
                    await asyncio.sleep(self._delay)
                    continue

                page_count = 0
                for card in cards:
                    a = card.select_one(link_selector) or card.select_one("a[href]")
                    if not a:
                        continue
                    href = (a.get("href") or "").strip()
                    if not href:
                        continue
                    product_url = urljoin(base + "/", href)
                    if product_url in seen_urls:
                        continue
                    seen_urls.add(product_url)

                    title_node = card.select_one(title_selector)
                    title = (
                        title_node.get_text(" ", strip=True)
                        if title_node
                        else a.get_text(" ", strip=True)
                    )
                    if not title or self._is_title_denied(title):
                        continue

                    price_node = card.select_one(price_selector)
                    price_text = (
                        price_node.get_text(" ", strip=True)
                        if price_node
                        else card.get_text(" ", strip=True)
                    )
                    price = self._extract_price_from_text(price_text)
                    if price is None:
                        continue

                    image = card.select_one("img")
                    image_url = image.get("src") if image else None
                    if image_url:
                        image_url = urljoin(base + "/", image_url)

                    fallback_handle = slugify(urlparse(product_url).path, max_length=70)
                    handle = slugify(title, max_length=70) or fallback_handle or "item"
                    vendor = host_slug
                    brand_slug = slugify(vendor) if vendor else "unknown"
                    normalized_key, match_confidence = self._build_normalized_key(
                        brand_slug=brand_slug,
                        sku=None,
                        title=title,
                        tags=[],
                    )
                    gender, subcategory = classify_gender_and_subcategory(
                        product_type=None,
                        title=title,
                        tags="",
                    )
                    products.append(
                        ProductInfo(
                            title=title,
                            vendor=vendor,
                            handle=handle,
                            product_type=None,
                            price=price,
                            compare_at_price=None,
                            currency=currency,
                            sku=None,
                            image_url=image_url,
                            tags=None,
                            product_url=product_url,
                            product_key=f"{platform_prefix}:{host_slug}:{handle}",
                            is_available=True,
                            gender=gender,
                            subcategory=subcategory,
                            normalized_key=normalized_key,
                            match_confidence=match_confidence,
                        )
                    )
                    page_count += 1

                if page_count == 0:
                    break
                await asyncio.sleep(self._delay)

        return products

    async def _try_makeshop_products(self, channel_url: str, currency: str) -> list[ProductInfo]:
        return await self._crawl_generic_product_cards(
            channel_url,
            currency,
            platform_prefix="makeshop",
            item_selector=".item-list li, .product-list li, .prd-list li, li.item",
            link_selector="a[href*='/view/item/'], a[href*='/shopdetail/'], a[href*='/shop/g/']",
            title_selector=".item_name, .name, .ttl, .product_name",
            price_selector=".price, .item_price, .price_wrap, .money",
            entry_paths=[
                "/",
                "/shop/goods/search.aspx",
                "/shop/goods/search.aspx?sort=popular",
                "/shop/g/gALL/",
                "/shop/g/g01/",
            ],
        )

    async def _try_stores_jp_products(self, channel_url: str, currency: str) -> list[ProductInfo]:
        return await self._crawl_generic_product_cards(
            channel_url,
            currency,
            platform_prefix="storesjp",
            item_selector=".item-list li, .products li, .product-list li, [data-item-id]",
            link_selector="a[href*='/items/'], a[href*='/products/']",
            title_selector=".item-name, .name, .product-name, .title",
            price_selector=".item-price, .price, .money, [class*='price']",
            entry_paths=[
                "/",
                "/items/all",
                "/items",
                "/collections/all",
                "/products",
            ],
        )

    async def _try_ochanoko_products(self, channel_url: str, currency: str) -> list[ProductInfo]:
        return await self._crawl_generic_product_cards(
            channel_url,
            currency,
            platform_prefix="ochanoko",
            item_selector=".item-list li, .product-list li, .goods-list li, li.item",
            link_selector="a[href*='/product/'], a[href*='/shopdetail/'], a[href*='/goods/']",
            title_selector=".item_name, .name, .title, .goods-name",
            price_selector=".price, .item_price, .money, [class*='price']",
            entry_paths=[
                "/",
                "/item-list",
                "/category",
                "/new",
                "/recommend",
            ],
        )

    # ── normalized_key 생성 ───────────────────────────────────────────────

    @staticmethod
    def _extract_model_code(text: str) -> str | None:
        """텍스트에서 브랜드 모델코드 추출 (예: M2002R, DD9336, AJ1).

        우선 긴 패턴(3자리+ 숫자), 없으면 짧은 패턴(AJ1 등) 순으로 시도.
        EU42(사이즈), FW23(시즌) 등 오탐은 _EXCLUDE_PREFIXES로 필터.
        """
        text_upper = text.upper()
        for pattern in (_MODEL_CODE_RE, _SHORT_CODE_RE):
            for m in pattern.finditer(text_upper):
                code = m.group(1)
                if code[:2] not in _EXCLUDE_PREFIXES:
                    return code.lower()
        return None

    @staticmethod
    def _build_normalized_key(
        brand_slug: str,
        sku: str | None,
        title: str,
        tags: list,
    ) -> tuple[str | None, float | None]:
        """교차채널 매칭용 normalized_key 생성.

        우선순위:
        1. SKU에 공식 스타일 코드 있으면 → 신뢰도 1.0
        2. tags에서 모델코드 추출         → 신뢰도 0.8
        3. title에서 모델코드 추출        → 신뢰도 0.7
        4. title slug (fallback)          → 신뢰도 0.5
        """
        if not brand_slug or brand_slug == "unknown":
            return None, None

        # 1순위: SKU — 영문+숫자 패턴이면 공식 스타일 코드
        if sku:
            code = ProductCrawler._extract_model_code(sku)
            if code:
                clean = re.sub(r"[^a-z0-9]", "", code)
                return f"{brand_slug}:{clean}", 1.0

        # 2순위: 개별 태그 중 모델코드 형태인 것
        for tag in (tags if isinstance(tags, list) else []):
            tag_str = str(tag).strip()
            if 3 <= len(tag_str) <= 15:
                code = ProductCrawler._extract_model_code(tag_str)
                if code:
                    return f"{brand_slug}:{re.sub(r'[^a-z0-9]', '', code)}", 0.8

        # 3순위: title에서 모델코드 추출
        code = ProductCrawler._extract_model_code(title)
        if code:
            return f"{brand_slug}:{re.sub(r'[^a-z0-9]', '', code)}", 0.7

        # 4순위: title slug fallback (처음 60자)
        title_slug = slugify(title, max_length=60, word_boundary=True)
        if title_slug:
            return f"{brand_slug}:{title_slug}", 0.5

        return None, None

    # ── 파싱 ─────────────────────────────────────────────────────────────

    def _parse_product(
        self, p: dict, base_url: str, currency: str
    ) -> ProductInfo | None:
        title: str = (p.get("title") or "").strip()
        vendor: str = (p.get("vendor") or "").strip()
        handle: str = (p.get("handle") or "").strip()
        product_type: str | None = (p.get("product_type") or "").strip() or None

        if not title or not handle:
            return None

        # 비패션 제품 거부 목록 체크
        vendor_lower = vendor.lower().strip()
        if vendor_lower in _VENDOR_DENYLIST:
            return None

        product_type_lower = (product_type or "").lower().strip()
        if product_type_lower and product_type_lower in _PRODUCT_TYPE_DENYLIST:
            return None

        if self._is_title_denied(title):
            return None

        # 첫 번째 variant에서 가격 추출
        variants = p.get("variants") or []
        if not variants:
            return None

        v0 = variants[0]
        try:
            price = float(v0.get("price") or 0)
        except (ValueError, TypeError):
            return None

        if price <= 0:
            return None

        compare_raw = v0.get("compare_at_price")
        compare_at_price: float | None = None
        if compare_raw:
            try:
                val = float(compare_raw)
                if val > price:  # 정가가 현재가보다 클 때만 세일로 인정
                    compare_at_price = val
            except (ValueError, TypeError):
                pass

        sku: str | None = (v0.get("sku") or "").strip() or None
        is_available = any(bool(v.get("available", False)) for v in variants)

        # 사이즈별 재고 추출 (option1이 사이즈인 경우)
        _NON_SIZE_VALUES = {"default title", "one size", "os", "onesize", "one-size", "free", "free size"}
        size_variants = [
            v for v in variants
            if (v.get("option1") or "").strip().lower() not in _NON_SIZE_VALUES
            and (v.get("option1") or "").strip()
        ]
        size_availability: list[dict] | None = None
        if size_variants:
            size_availability = [
                {"size": v.get("option1", "").strip(), "in_stock": bool(v.get("available", False))}
                for v in size_variants
            ]

        # 첫 번째 이미지
        images = p.get("images") or []
        image_url: str | None = images[0]["src"] if images else None

        product_url = f"{base_url}/products/{handle}"
        brand_slug = slugify(vendor) if vendor else "unknown"
        product_key = f"{brand_slug}:{handle}"
        tags = p.get("tags") or []
        if isinstance(tags, list):
            tags_list = [str(t).strip() for t in tags if str(t).strip()]
        elif isinstance(tags, str):
            tags_list = [t.strip() for t in tags.split(",") if t.strip()]
        else:
            tags_list = []
        tags_json = json.dumps(tags_list, ensure_ascii=False) if tags_list else None
        tags_text = ", ".join(tags_list)
        gender, subcategory = classify_gender_and_subcategory(
            product_type=product_type,
            title=title,
            tags=tags_text,
        )
        normalized_key, match_confidence = self._build_normalized_key(
            brand_slug=brand_slug,
            sku=sku,
            title=title,
            tags=tags_list,
        )

        return ProductInfo(
            title=title,
            vendor=vendor,
            handle=handle,
            product_type=product_type,
            price=price,
            compare_at_price=compare_at_price,
            currency=currency,
            sku=sku,
            image_url=image_url,
            tags=tags_json,
            product_url=product_url,
            product_key=product_key,
            is_available=is_available,
            gender=gender,
            subcategory=subcategory,
            normalized_key=normalized_key,
            match_confidence=match_confidence,
            size_availability=size_availability,
        )

    async def _fetch_gpt_fallback_html(self, channel_url: str) -> tuple[str, str] | None:
        assert self._client is not None
        base = channel_url.rstrip("/")
        candidates = [
            base,
            f"{base}/collections/all",
            f"{base}/shop/all_items",
            f"{base}/items/all",
            f"{base}/product/list.html?cate_no=1",
        ]
        seen: set[str] = set()
        for url in candidates:
            if url in seen:
                continue
            seen.add(url)
            try:
                resp = await self._client.get(url, headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=self._timeout)
            except Exception:
                continue
            if resp.status_code != 200 or not resp.text.strip():
                continue
            return url, resp.text
        return None

    async def _try_gpt_parser_products(
        self,
        channel_url: str,
        currency: str,
    ) -> list[ProductInfo]:
        try:
            from fashion_engine.crawler.gpt_parser import parse_products_from_html
        except Exception as exc:
            logger.warning("GPT parser import 실패 [%s]: %s", channel_url, exc)
            return []

        fetched = await self._fetch_gpt_fallback_html(channel_url)
        if not fetched:
            return []
        page_url, html = fetched
        try:
            parsed = await parse_products_from_html(page_url, html)
        except Exception as exc:
            logger.warning("GPT parser 실행 실패 [%s]: %s", channel_url, exc)
            return []

        products: list[ProductInfo] = []
        seen_urls: set[str] = set()
        default_vendor = urlparse(channel_url).netloc.replace("www.", "").strip() or "unknown"
        for item in parsed.products:
            if not isinstance(item, dict):
                continue
            title = str(item.get("name") or "").strip()
            if not title or self._is_title_denied(title):
                continue
            product_url = urljoin(channel_url, str(item.get("url") or "").strip())
            if not product_url or product_url in seen_urls:
                continue
            seen_urls.add(product_url)
            vendor = str(item.get("brand") or default_vendor).strip() or default_vendor
            brand_slug = slugify(vendor) if vendor else "unknown"
            handle = (
                urlparse(product_url).path.rstrip("/").split("/")[-1].strip()
                or slugify(title)
                or "unknown"
            )
            try:
                price = float(item.get("price") or 0)
            except (TypeError, ValueError):
                continue
            if price <= 0:
                continue
            try:
                original_price = float(item.get("original_price")) if item.get("original_price") not in (None, "") else None
            except (TypeError, ValueError):
                original_price = None
            tags_text = "gpt-fallback"
            normalized_key, match_confidence = self._build_normalized_key(
                brand_slug=brand_slug,
                sku=None,
                title=title,
                tags=["gpt-fallback"],
            )
            gender, subcategory = classify_gender_and_subcategory(
                product_type=None,
                title=title,
                tags=tags_text,
            )
            products.append(
                ProductInfo(
                    title=title,
                    vendor=vendor,
                    handle=handle,
                    product_type=None,
                    price=price,
                    compare_at_price=original_price,
                    currency=str(item.get("currency") or currency or "USD").upper(),
                    sku=None,
                    image_url=(urljoin(channel_url, str(item.get("image_url"))) if item.get("image_url") else None),
                    tags=json.dumps(["gpt-fallback"], ensure_ascii=False),
                    product_url=product_url,
                    product_key=f"{brand_slug}:{handle}",
                    is_available=True,
                    gender=gender,
                    subcategory=subcategory,
                    normalized_key=normalized_key,
                    match_confidence=match_confidence,
                )
            )
        logger.info(
            "GPT fallback parser 수집 완료 url=%s products=%s",
            channel_url,
            len(products),
        )
        return products

    def _parse_woocommerce_product(
        self,
        item: dict,
        channel_url: str,
        currency: str,
    ) -> ProductInfo | None:
        wc_id = item.get("id")
        title = (item.get("name") or "").strip()
        if not wc_id or not title:
            return None
        if self._is_title_denied(title):
            return None

        product_type: str | None = (item.get("type") or "").strip() or None
        if self._is_product_type_denied(product_type):
            return None

        sale_price_str = str(item.get("sale_price") or "").strip()
        regular_price_str = str(item.get("regular_price") or "").strip()
        price_str = str(item.get("price") or "").strip() or regular_price_str
        try:
            price = float(price_str) if price_str else 0.0
        except Exception:
            return None
        if price <= 0:
            return None

        compare_at_price: float | None = None
        if regular_price_str:
            try:
                regular = float(regular_price_str)
                if regular > price:
                    compare_at_price = regular
            except Exception:
                pass

        images = item.get("images") or []
        image_url = images[0].get("src") if isinstance(images, list) and images else None
        product_url = (item.get("permalink") or "").strip() or f"{channel_url.rstrip('/')}/?p={wc_id}"
        handle = str(wc_id)
        host = urlparse(channel_url).netloc.lower() or "unknown"
        channel_slug = host.replace("www.", "")
        product_key = f"wc:{channel_slug}:{wc_id}"
        vendor = (item.get("brand") or "").strip() or "unknown"
        sku = (item.get("sku") or "").strip() or None
        tags = item.get("tags") or []
        tags_list = []
        if isinstance(tags, list):
            for t in tags:
                if isinstance(t, dict):
                    name = str(t.get("name") or "").strip()
                    if name:
                        tags_list.append(name)
        tags_json = json.dumps(tags_list, ensure_ascii=False) if tags_list else None
        tags_text = ", ".join(tags_list)
        is_available = str(item.get("stock_status") or "").lower() != "outofstock"
        brand_slug = slugify(vendor) if vendor and vendor != "unknown" else "unknown"
        normalized_key, match_confidence = self._build_normalized_key(
            brand_slug=brand_slug,
            sku=sku,
            title=title,
            tags=tags_list,
        )
        gender, subcategory = classify_gender_and_subcategory(
            product_type=product_type,
            title=title,
            tags=tags_text,
        )
        return ProductInfo(
            title=title,
            vendor=vendor,
            handle=handle,
            product_type=product_type,
            price=price,
            compare_at_price=compare_at_price,
            currency=currency,
            sku=sku,
            image_url=image_url,
            tags=tags_json,
            product_url=product_url,
            product_key=product_key,
            is_available=is_available,
            gender=gender,
            subcategory=subcategory,
            normalized_key=normalized_key,
            match_confidence=match_confidence,
        )

    @staticmethod
    def _is_title_denied(title: str) -> bool:
        title_lower = title.lower()
        return any(kw in title_lower for kw in _TITLE_KEYWORD_DENYLIST)

    @staticmethod
    def _is_product_type_denied(product_type: str | None) -> bool:
        val = (product_type or "").lower().strip()
        return bool(val and val in _PRODUCT_TYPE_DENYLIST)
    @staticmethod
    def _classify_error(exc: BaseException | None, http_status: int | None = None) -> str:
        if http_status == 403:
            return "http_403"
        if http_status == 404:
            return "http_404"
        if http_status == 429:
            return "http_429"
        if http_status is not None and http_status >= 500:
            return "http_5xx"
        if isinstance(exc, (httpx.TimeoutException, TimeoutError, asyncio.TimeoutError)):
            return "timeout"
        if isinstance(exc, (json.JSONDecodeError, ValueError, KeyError)):
            return "parse_error"
        return "parse_error"
