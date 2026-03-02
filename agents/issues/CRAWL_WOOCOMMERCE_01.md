# CRAWL_WOOCOMMERCE_01: WooCommerce REST API 크롤러 추가

**Task ID**: T-20260302-062
**Owner**: codex-dev
**Priority**: P2
**Labels**: backend, crawler, feature, new-platform

---

## 배경

CrawlRun #1에서 136개 채널이 `not_supported` 실패. 분류:
- **74개 (platform=NULL)**: Shopify API + Cafe24 HTML 모두 실패
- **62개 (platform=shopify)**: Shopify 감지됐으나 제품 없음 (비공개/빈 스토어)

platform=NULL 74개 채널의 상당수는 **WooCommerce** 기반 스토어로 추정:
- WooCommerce는 WordPress 기반 가장 대중적인 오픈소스 쇼핑몰
- 공개 REST API: `/wp-json/wc/v3/products` (인증 없이 접근 가능한 스토어도 있음)
- 예시: Goldwin Global, Cole Buxton, AXEL ARIGATO 등

---

## 요구사항

### 변경 파일: `src/fashion_engine/crawler/product_crawler.py`

#### 1. WooCommerce 감지 함수

```python
async def _try_woocommerce_detect(self, base_url: str) -> bool:
    """WooCommerce REST API 엔드포인트 존재 확인."""
    url = f"{base_url.rstrip('/')}/wp-json/wc/v3/"
    try:
        resp = await self._client.get(url, timeout=8)
        # 401 = WooCommerce 있지만 인증 필요 (존재 확인)
        # 200 = 공개 접근 가능
        return resp.status_code in (200, 401)
    except Exception:
        return False
```

#### 2. WooCommerce 제품 수집 함수

```python
async def _try_woocommerce_products(
    self,
    channel: Channel,
) -> list[ProductInfo]:
    """WooCommerce /wp-json/wc/v3/products 페이지네이션 수집."""
    base_url = channel.url.rstrip("/")
    api_base = f"{base_url}/wp-json/wc/v3/products"
    products: list[ProductInfo] = []
    page = 1
    per_page = 100

    while True:
        url = f"{api_base}?per_page={per_page}&page={page}&status=publish"
        try:
            resp = await self._client.get(url, timeout=15)
        except httpx.HTTPError as e:
            logger.warning(f"[woocommerce] {base_url} p{page}: {e}")
            break

        if resp.status_code == 401:
            # 인증 필요 → 비공개 스토어
            logger.info(f"[woocommerce] {base_url}: 인증 필요 (비공개)")
            return []
        if resp.status_code != 200:
            break

        data = resp.json()
        if not isinstance(data, list) or not data:
            break

        for item in data:
            info = self._parse_woocommerce_product(item, channel)
            if info:
                products.append(info)

        # 페이지네이션: X-WP-TotalPages 헤더 활용
        total_pages = int(resp.headers.get("X-WP-TotalPages", "1"))
        if page >= total_pages:
            break
        page += 1

    return products
```

#### 3. WooCommerce 제품 파싱

```python
def _parse_woocommerce_product(
    self,
    item: dict,
    channel: Channel,
) -> ProductInfo | None:
    """WooCommerce 제품 JSON → ProductInfo 변환."""
    wc_id = item.get("id")
    name = (item.get("name") or "").strip()
    if not name or not wc_id:
        return None

    # 제목 키워드 덴리스트 적용
    if self._is_title_denied(name):
        return None

    # 가격 처리 (세일가 우선)
    sale_price_str = item.get("sale_price") or ""
    regular_price_str = item.get("regular_price") or ""
    price_str = item.get("price") or regular_price_str

    try:
        price = float(price_str) if price_str else None
        original_price = float(regular_price_str) if regular_price_str else None
    except ValueError:
        price = None
        original_price = None

    is_sale = bool(sale_price_str and sale_price_str != regular_price_str)

    # 이미지
    images = item.get("images") or []
    image_url = images[0].get("src") if images else None

    # product_key
    channel_slug = channel.url.replace("https://", "").replace("http://", "").split("/")[0]
    product_key = f"wc:{channel_slug}:{wc_id}"

    # 통화 추론 (URL 기반 기존 로직 재사용)
    currency = self._infer_currency(channel.url)

    return ProductInfo(
        product_key=product_key,
        name=name,
        price=price,
        original_price=original_price,
        currency=currency,
        is_sale=is_sale,
        image_url=image_url,
        url=item.get("permalink") or channel.url,
        vendor=None,
        product_type=item.get("type"),
        tags=",".join(t.get("name", "") for t in item.get("tags", [])),
    )
```

#### 4. `crawl_channel()` fallback 체인에 WooCommerce 추가

```python
async def crawl_channel(self, channel: Channel) -> CrawlResult:
    # 1. Shopify API 시도 (기존)
    result = await self._try_shopify(channel)
    if result.products or not result.error:
        return result

    # 2. Cafe24 HTML 시도 (기존)
    result = await self._try_cafe24(channel)
    if result.products or not result.error:
        return result

    # 3. WooCommerce REST API 시도 (신규)
    if await self._try_woocommerce_detect(channel.url):
        products = await self._try_woocommerce_products(channel)
        if products:
            return CrawlResult(
                channel_id=channel.id,
                products=products,
                crawl_strategy="woocommerce-api",
                error=None,
                error_type=None,
            )

    # 4. 미지원
    return CrawlResult(
        channel_id=channel.id,
        products=[],
        error="No products found (non-Shopify/Cafe24/WooCommerce or empty store)",
        error_type="not_supported",
        crawl_strategy=None,
    )
```

#### 5. `crawl_products.py` platform 업데이트 연동

```python
# 기존
if result.crawl_strategy == "shopify-api":
    await update_platform(db, channel.id, "shopify")
elif result.crawl_strategy == "cafe24-html":
    await update_platform(db, channel.id, "cafe24")

# 추가
elif result.crawl_strategy == "woocommerce-api":
    await update_platform(db, channel.id, "woocommerce")
```

---

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `src/fashion_engine/crawler/product_crawler.py` | WooCommerce 감지/파싱 함수 추가, fallback 체인 확장 |
| `scripts/crawl_products.py` | `woocommerce-api` strategy 시 platform 업데이트 |

---

## 주의사항

- WooCommerce API 인증 없이 접근 가능한 스토어만 대상 (401 → skip)
- 가격은 문자열로 반환됨 (`"price": "120.00"`) → float 변환 필요
- `sale_price`가 빈 문자열이면 세일 아님
- `X-WP-TotalPages` 헤더가 없으면 1페이지만 있다고 간주
- 기존 `_infer_currency()` 재사용 (URL 기반 통화 추론)

---

## DoD (완료 기준)

- [ ] `_try_woocommerce_detect()` 함수 존재
- [ ] `_try_woocommerce_products()` 함수 존재 (페이지네이션 포함)
- [ ] `_parse_woocommerce_product()` 함수 존재
- [ ] `crawl_channel()` fallback 체인에 WooCommerce 추가 (3번째)
- [ ] `crawl_products.py`에서 `woocommerce-api` strategy → `platform='woocommerce'` 업데이트

## 검증

```bash
# platform=NULL 채널 중 WooCommerce 가능성 있는 채널 하나 선택
# (예: Cole Buxton - https://www.colebuxton.com)
sqlite3 data/fashion.db "SELECT id, name, url FROM channels WHERE platform IS NULL AND is_active=1 LIMIT 5;"

# 단독 크롤 시도
uv run python scripts/crawl_products.py --channel-id <ID>

# 결과 확인
sqlite3 data/fashion.db "SELECT p.name, p.price FROM products p WHERE p.channel_id=<ID> LIMIT 10;"
sqlite3 data/fashion.db "SELECT platform FROM channels WHERE id=<ID>;"
# 예상: platform='woocommerce'
```
