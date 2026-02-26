"""
드롭(발매) 크롤러.

Shopify /products.json 두 가지 방법으로 신제품 감지:
  1. ?sort_by=created-at-desc&limit=20 → 최근 추가된 product_key 중 DB에 없는 것
  2. ?tag=coming-soon&limit=50 → "coming-soon" 태그 = upcoming drop

두 경우 모두 product_key 기준으로 drops 테이블에 upsert 후
is_new=True 인 것만 Discord 알림 전송.
"""
import asyncio
import logging
from dataclasses import dataclass, field

import httpx
from slugify import slugify

logger = logging.getLogger(__name__)


@dataclass
class DropCandidate:
    product_name: str
    product_key: str
    source_url: str
    image_url: str | None
    price_krw: int | None
    status: str = "released"   # "upcoming" | "released"
    channel_name: str = ""


@dataclass
class DropCrawlResult:
    channel_url: str
    channel_name: str
    candidates: list[DropCandidate] = field(default_factory=list)
    error: str | None = None


class DropCrawler:
    """Shopify 채널에서 신제품 / upcoming 드롭 감지."""

    def __init__(self, request_delay: float = 1.0, timeout: float = 15.0):
        self._delay = request_delay
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "DropCrawler":
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

    async def crawl_new_arrivals(
        self, channel_url: str, channel_name: str, rate_to_krw: float = 1.0
    ) -> DropCrawlResult:
        """최근 추가된 제품 20개 감지 (sort_by=created-at-desc)."""
        result = DropCrawlResult(channel_url=channel_url, channel_name=channel_name)
        assert self._client is not None
        base = channel_url.rstrip("/")
        try:
            resp = await self._client.get(
                f"{base}/products.json?sort_by=created-at-desc&limit=20"
            )
            if resp.status_code != 200:
                result.error = f"HTTP {resp.status_code}"
                return result
            data = resp.json()
        except Exception as e:
            result.error = str(e)[:200]
            return result

        for p in data.get("products", []):
            candidate = self._parse_candidate(p, base, channel_name, "released", rate_to_krw)
            if candidate:
                result.candidates.append(candidate)

        await asyncio.sleep(self._delay)
        return result

    async def crawl_coming_soon(
        self, channel_url: str, channel_name: str, rate_to_krw: float = 1.0
    ) -> DropCrawlResult:
        """coming-soon 태그 제품 감지."""
        result = DropCrawlResult(channel_url=channel_url, channel_name=channel_name)
        assert self._client is not None
        base = channel_url.rstrip("/")
        try:
            resp = await self._client.get(
                f"{base}/products.json?tag=coming-soon&limit=50"
            )
            if resp.status_code != 200:
                result.error = f"HTTP {resp.status_code}"
                return result
            data = resp.json()
        except Exception as e:
            result.error = str(e)[:200]
            return result

        for p in data.get("products", []):
            candidate = self._parse_candidate(p, base, channel_name, "upcoming", rate_to_krw)
            if candidate:
                result.candidates.append(candidate)

        await asyncio.sleep(self._delay)
        return result

    def _parse_candidate(
        self, p: dict, base_url: str, channel_name: str, status: str, rate_to_krw: float
    ) -> DropCandidate | None:
        title = (p.get("title") or "").strip()
        vendor = (p.get("vendor") or "").strip()
        handle = (p.get("handle") or "").strip()
        if not title or not handle:
            return None

        brand_slug = slugify(vendor) if vendor else "unknown"
        product_key = f"{brand_slug}:{handle}"
        source_url = f"{base_url}/products/{handle}"

        images = p.get("images") or []
        image_url = images[0]["src"] if images else None

        price_krw: int | None = None
        variants = p.get("variants") or []
        if variants:
            try:
                raw_price = float(variants[0].get("price") or 0)
                if raw_price > 0:
                    price_krw = int(raw_price * rate_to_krw)
            except (ValueError, TypeError):
                pass

        return DropCandidate(
            product_name=title,
            product_key=product_key,
            source_url=source_url,
            image_url=image_url,
            price_krw=price_krw,
            status=status,
            channel_name=channel_name,
        )
