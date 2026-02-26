"""
채널별 제품·가격 크롤러.

Shopify /products.json (공개 REST API) 기반으로 제품 목록과 가격을 수집.
Playwright 불필요 — httpx 직접 사용.
"""
import asyncio
import logging
from dataclasses import dataclass, field

import httpx
from slugify import slugify

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
    "TW": "TWD",
    "CN": "CNY",
}

# Shopify 제품 크롤 시 최대 페이지 수 (250개/페이지 × 16 = 최대 4000개)
SHOPIFY_MAX_PAGES = 16


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
    product_url: str     # 채널 내 제품 URL
    product_key: str     # "brand-slug:handle" 교차 채널 매칭용


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
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
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
        assert self._client is not None
        try:
            resp = await self._client.get(f"{base_url.rstrip('/')}/shop.json", timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("shop", {}).get("currency")
        except Exception:
            pass
        return None

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
        }
        prefix = host.split(".")[0]
        if prefix in SUBDOMAIN_CURRENCY:
            return SUBDOMAIN_CURRENCY[prefix]
        return COUNTRY_CURRENCY.get(country or "", "USD")

    async def crawl_channel(
        self, channel_url: str, country: str | None = None
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
                result.error = "No products found (non-Shopify or empty store)"
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
                resp = await self._client.get(url)
                if resp.status_code != 200:
                    break
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

        # 첫 번째 이미지
        images = p.get("images") or []
        image_url: str | None = images[0]["src"] if images else None

        product_url = f"{base_url}/products/{handle}"
        brand_slug = slugify(vendor) if vendor else "unknown"
        product_key = f"{brand_slug}:{handle}"

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
            product_url=product_url,
            product_key=product_key,
        )
