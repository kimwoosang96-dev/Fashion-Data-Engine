# T-069 | CAFE24_SINGLE_BRAND_CRAWL_01

> **목적**: Cafe24 단일 브랜드 스토어(brand-store) 6개의 제품 수집 지원
> — `/product/maker.html` 브랜드 카테고리 전략 대신 `/product/list.html` 직접 목록 사용

---

## 배경 (실측 분석)

**현황**: Cafe24 채널 30개 중 6개 brand-store가 지속 실패:

| 채널명 | URL | 실패 원인 |
|--------|-----|---------|
| CAYL | https://www.cayl.co.kr | maker.html 404 + KR DNS |
| and wander | https://www.andwander.co.kr | maker.html 404 + KR DNS |
| 브레슈 (Breche) | https://www.breche-online.com | maker.html 404 + KR DNS |
| heritagefloss | https://www.heritagefloss.com | maker.html 404 |
| Sun Chamber Society | https://www.sunchambersociety.com | maker.html 404 |
| nightwaks | https://www.nightwaks.com | maker.html 404 |

**근본 원인**:

```
현재 crawl_channel() Cafe24 분기:
  1. channel_brands.cate_no DB 로드 OR _discover_cafe24_brand_categories() 실행
  2. _discover_cafe24_brand_categories()가 시도하는 URL:
     - /product/maker.html   ← 편집숍용 (여러 브랜드 목록)
     - /product/brand.html
     - /brands2.html
     등 6개 후보 → 단일 브랜드 스토어에서 모두 404
  3. categories = [] → "No products found"
```

단일 브랜드 스토어는 브랜드 카테고리 페이지가 없음.
대신 `/product/list.html` 또는 루트 카테고리 `/category/main/` 직접 사용.

**실측 확인**:
```bash
# heritagefloss
GET /product/maker.html → 404
GET /product/list.html → 200 OK (제품 목록 페이지)

# THEXSHOP (edit-shop)
GET /product/maker.html → 404  ← T-066에서도 실패로 확인
GET /product/list.html → 200 OK
```

---

## 추가 이슈: Korean Domain DNS

3개 채널 (CAYL, and wander, 브레슈)의 도메인이 로컬 macOS에서 DNS 미해석:

```
cayl.co.kr     → NXDOMAIN (로컬 DNS 기준)
andwander.co.kr → NXDOMAIN
breche-online.com → NXDOMAIN
```

→ 이 채널들은 Railway 환경에서 크롤해야 함 (T-070 참조).
→ 현재 과업(T-069)은 crawler 로직 수정에 집중, 실제 수집은 T-070에서 검증.

---

## 요구사항

### Step 1: `product_crawler.py` — 단일 브랜드 Cafe24 전략 추가

**파일**: `src/fashion_engine/crawler/product_crawler.py`

현재 `crawl_channel()` Cafe24 분기에 단일 브랜드 fallback 추가:

```python
async def _try_cafe24_single_brand(self, channel_url: str, currency: str) -> list[ProductInfo]:
    """
    단일 브랜드 Cafe24 스토어용 제품 수집.
    브랜드 카테고리 페이지 없이 전체 상품 목록에서 직접 수집.

    시도 URL 순서:
      1. /product/list.html?cate_no=all&page=N  (전체 카테고리)
      2. /product/list.html?page=N               (기본 목록)
      3. /                                        (홈 → 제품 파싱)

    페이지네이션:
      - page=1부터 시작, 빈 페이지면 중단
      - 최대 100페이지 (단일 브랜드 최대 제품 수 고려)

    반환: ProductInfo 리스트
    """
    base = channel_url.rstrip('/')
    products = []

    # 후보 URL 패턴
    list_candidates = [
        f"{base}/product/list.html?cate_no=all",
        f"{base}/product/list.html",
        f"{base}/category/main/",
    ]

    # 응답하는 목록 URL 찾기
    working_base = None
    for candidate in list_candidates:
        try:
            resp = await self._client.get(f"{candidate}&page=1" if '?' in candidate else f"{candidate}?page=1",
                                          timeout=self._timeout)
            if resp.status_code == 200 and 'cafe24' in resp.text.lower():
                working_base = candidate
                break
        except Exception:
            continue

    if not working_base:
        return []

    # 페이지네이션
    for page in range(1, 101):
        sep = '&' if '?' in working_base else '?'
        url = f"{working_base}{sep}page={page}"
        try:
            resp = await self._client.get(url, timeout=self._timeout)
            if resp.status_code != 200:
                break
        except Exception:
            break

        page_products = self._parse_cafe24_product_list(resp.text, channel_url, currency, brand_name=None)
        if not page_products:
            break
        products.extend(page_products)

    return products
```

**`crawl_channel()` Cafe24 분기 수정**:

```python
# 기존 흐름
categories = loaded_categories or await self._discover_cafe24_brand_categories(channel_url)
if not categories:
    # 단일 브랜드 fallback 추가
    logger.info(f"[{channel.name}] Cafe24 단일 브랜드 전략 시도")
    single_brand_products = await self._try_cafe24_single_brand(channel_url, currency)
    if single_brand_products:
        return CrawlResult(
            channel_id=channel.id,
            products=single_brand_products,
            crawl_strategy="cafe24-single-brand",
        )
    # 여기까지 오면 진짜 실패
    return CrawlResult(channel_id=channel.id, products=[], error="No products found", ...)
```

### Step 2: 파서 재사용 — `_parse_cafe24_product_list()` 추출

기존 `_try_cafe24_products()`의 HTML 파싱 로직을 공통 함수로 추출:

```python
def _parse_cafe24_product_list(
    self, html: str, channel_url: str, currency: str, brand_name: str | None
) -> list[ProductInfo]:
    """Cafe24 제품 목록 HTML에서 ProductInfo 추출 (공통 파서)"""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(".xans-product-listnormal li, .prd-list li, .product-list li")
    # ... 기존 파싱 로직 ...
```

### Step 3: `crawl_products.py` — 단일 브랜드 채널 전처리

brand-store 타입 Cafe24 채널의 경우 `cate_no` 로딩 스킵:

```python
# crawl_products.py 내 cate_no 로딩 부분
if channel.channel_type == 'brand-store' and channel.platform == 'cafe24':
    # brand-store는 카테고리 없이 단일 브랜드 전략 사용
    channel_cats[channel.id] = []  # 빈 categories → 단일 브랜드 fallback 트리거
```

---

## 대상 채널 (검증 목표)

| 채널 | URL | DNS 이슈 | 검증 환경 |
|------|-----|---------|---------|
| heritagefloss | heritagefloss.com | 없음 | 로컬 가능 |
| Sun Chamber Society | sunchambersociety.com | 없음 | 로컬 가능 |
| nightwaks | nightwaks.com | 없음 | 로컬 가능 |
| CAYL | cayl.co.kr | **KR DNS** | Railway 필요 |
| and wander | andwander.co.kr | **KR DNS** | Railway 필요 |
| 브레슈 | breche-online.com | **KR DNS** | Railway 필요 |

---

## DoD

- [ ] `_try_cafe24_single_brand()` 구현 (`/product/list.html` 기반 페이지네이션)
- [ ] `_parse_cafe24_product_list()` 공통 파서 추출
- [ ] `crawl_channel()` — categories=[] 시 single_brand fallback 적용
- [ ] 로컬에서 heritagefloss, Sun Chamber Society, nightwaks 수집 성공 ≥ 1개
- [ ] `crawl_strategy='cafe24-single-brand'` 기록됨
- [ ] CAYL / and wander / 브레슈: T-070 Railway 크롤에서 검증

---

## 검증

```bash
# 단일 브랜드 Cafe24 채널 테스트 (로컬 가능)
uv run python scripts/crawl_products.py --channel-name heritagefloss
uv run python scripts/crawl_products.py --channel-name 'Sun Chamber Society'

# 결과 확인
sqlite3 data/fashion.db "
SELECT c.name, cl.status, cl.products_found, cl.crawl_strategy, cl.duration_ms
FROM crawl_channel_logs cl JOIN channels c ON c.id = cl.channel_id
WHERE cl.run_id = (SELECT MAX(id) FROM crawl_runs)
AND c.platform = 'cafe24' AND c.channel_type = 'brand-store';
"
```
