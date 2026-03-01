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
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from slugify import slugify
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from fashion_engine.crawler.product_classifier import classify_gender_and_subcategory

logger = logging.getLogger(__name__)

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
SHOPIFY_MAX_PAGES = 16

# ── 모델코드 추출용 정규식 ──────────────────────────────────────────────
# 3자리 이상 숫자 포함 (M2002R, DD9336, GZ6094, NMD_R1 등)
_MODEL_CODE_RE = re.compile(r'\b([A-Z]{1,3}[0-9]{3,}[A-Z0-9]{0,6})\b')
# 1~2자리 숫자 포함 (AJ1, AF1, AM90, AM95 등 짧은 코드)
_SHORT_CODE_RE = re.compile(r'\b([A-Z]{2,4}[0-9]{1,2})\b')
# 사이즈·시즌 코드 제외 (EU40, FW23 등 오탐 방지)
_EXCLUDE_PREFIXES = frozenset(["EU", "UK", "US", "JP", "CM", "FW", "SS", "AW", "SP"])
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


@dataclass
class ChannelProductResult:
    channel_url: str
    products: list[ProductInfo] = field(default_factory=list)
    error: str | None = None
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
            timeout=self._timeout,
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
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    async def _fetch_with_retry(self, url: str, timeout: float | None = None) -> httpx.Response:
        assert self._client is not None
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        response = await self._client.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response

    @staticmethod
    def _infer_currency(channel_url: str, country: str | None) -> str:
        """URL 서브도메인 + 국가 코드에서 통화 추론.
        Shopify 다국어 스토어는 kr., jp. 등의 서브도메인을 사용함.
        """
        from urllib.parse import urlparse
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

    async def crawl_channel(
        self,
        channel_url: str,
        country: str | None = None,
        cafe24_brand_categories: list[tuple[str, str]] | None = None,
    ) -> ChannelProductResult:
        """채널 URL에서 전체 제품 목록 수집."""
        currency = self._infer_currency(channel_url, country)
        result = ChannelProductResult(channel_url=channel_url)

        try:
            products = await self._try_shopify_products(channel_url, currency)
            if products:
                result.products = products
                result.crawl_strategy = "shopify-api"
            else:
                categories = list(cafe24_brand_categories or [])
                if not categories:
                    categories = await self._discover_cafe24_brand_categories(channel_url)
                cafe24_products: list[ProductInfo] = []
                for brand_name, cate_no in categories:
                    cafe24_products.extend(
                        await self._try_cafe24_products(
                            channel_url=channel_url,
                            cate_no=cate_no,
                            brand_name=brand_name,
                            currency=currency,
                        )
                    )
                if cafe24_products:
                    dedup: dict[str, ProductInfo] = {}
                    for p in cafe24_products:
                        dedup[p.product_url] = p
                    result.products = list(dedup.values())
                    result.crawl_strategy = "cafe24-html"
                else:
                    result.error = "No products found (non-Shopify/Cafe24 or empty store)"
        except Exception as e:
            result.error = str(e)[:200]
            logger.warning(f"제품 크롤 실패 [{channel_url}]: {e}")

        return result

    # ── Shopify 전략 ─────────────────────────────────────────────────────

    async def _try_shopify_products(
        self, channel_url: str, currency: str
    ) -> list[ProductInfo]:
        """
        Shopify /products.json?limit=250&page=N 순회.
        최대 SHOPIFY_MAX_PAGES 페이지.
        """
        assert self._client is not None
        base = channel_url.rstrip("/")
        products: list[ProductInfo] = []

        for page in range(1, SHOPIFY_MAX_PAGES + 1):
            url = f"{base}/products.json?limit=250&page={page}"
            try:
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

            if len(page_products) < 250:
                break

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
        ]
        found: list[tuple[str, str]] = []
        seen: set[str] = set()
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
                if cate_no in seen:
                    continue
                name = a.get_text(" ", strip=True)
                if not name:
                    continue
                seen.add(cate_no)
                found.append((name, cate_no))
            if found:
                break
        return found

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
                resp = await self._client.get(list_url, timeout=self._timeout)
                if resp.status_code != 200:
                    break
            except Exception:
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select(
                "li[id^='anchorBoxId_'], ul.prdList > li, .xans-product-listnormal li"
            )
            if not cards:
                break

            page_count = 0
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
                if not nums:
                    continue
                try:
                    price = float(nums[0].replace(",", ""))
                except ValueError:
                    continue
                if price <= 0:
                    continue

                img = card.select_one("img")
                image_url = img.get("src") if img else None
                if image_url:
                    image_url = urljoin(base + "/", image_url)

                product_url = urljoin(base + "/", href)
                text = card.get_text(" ", strip=True).lower()
                is_available = not ("품절" in text or "sold out" in text or "soldout" in text)

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
                        vendor=brand_name,
                        handle=product_no,
                        product_type=None,
                        price=price,
                        compare_at_price=None,
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
                page_count += 1

            if page_count == 0:
                break
            await asyncio.sleep(self._delay)

        return products

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

        if not title or not handle:
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
            product_type=(p.get("product_type") or "").strip() or None,
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
            product_type=(p.get("product_type") or "").strip() or None,
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
