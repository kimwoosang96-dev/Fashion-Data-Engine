# CAFE24_CRAWL_FIX_01: Cafe24 수집 실패 원인 조사 + 개선

**Task ID**: T-20260302-066
**Owner**: codex-dev
**Priority**: P1
**Labels**: backend, crawler, cafe24, reliability, performance

---

## 배경

### 현황 (CrawlRun #2 기준)

| 항목 | 값 |
|------|-----|
| DB 등록 Cafe24 채널 | **1개** (THEXSHOP, `platform='cafe24'`) |
| HTTP 탐색으로 추가 확인된 Cafe24 채널 | **7개** — platform=NULL이나 Cafe24 신호 확인 |
| **실질 Cafe24 채널 합계** | **8개** (THEXSHOP + 아래 7개) |
| `channel_brands.cate_no` 등록 수 | **0개** (매번 HTML 자동 발견) |
| CrawlRun #2 THEXSHOP 결과 | **TIMEOUT** (정확히 600초, T-061 guard 동작) |
| CrawlRun #1 THEXSHOP 결과 | 45,242개 수집 성공 (단, T-060으로 SOLD OUT 필터 적용됨) |

#### platform=NULL이나 HTTP 탐색으로 Cafe24 확인된 7개 채널

```
8DIVISION     https://www.8division.com
empty         https://www.empty.seoul.kr
grds          https://www.grds.com
NOCLAIM       https://www.noclaim.co.kr
PARLOUR       https://www.parlour.kr
SCULP STORE   https://www.sculpstore.com
Unipair       https://www.unipair.com
```

→ T-067 Step 1 `channel_probe.py --apply` 실행 후 이 채널들의 `platform='cafe24'`가 자동 업데이트된다.

### 근본 원인 분석

```
_discover_cafe24_brand_categories()
  → 3개 URL 후보 순차 탐색 후 cate_no 자동 발견
  ↓ (예: 100+ 카테고리 발견됨)

for brand_name, cate_no in categories:         ← 순차 처리 (병렬화 없음)
    await self._try_cafe24_products(...)        ← 각 카테고리 최대 80페이지 순회
                                                ← 429/503 재시도 없음

추정: 100 카테고리 × 평균 5초 = 500초+ → 600초 타임아웃 초과
```

**추가 문제**:
- 73개 NULL platform 채널 중 실제 Cafe24 스토어 수 미파악
  → URL 패턴 3개(`/product/maker.html`, `/product/brand.html`, `/brands2.html`) 외의 Cafe24 스토어는 `not_supported`로 처리
- `_discover_cafe24_brand_categories()`가 실패하면 Cafe24임에도 수집 불가
- THEXSHOP 단독 크롤 시에도 600초 내 완료 불확실

### 코드 위치 참고

- `_discover_cafe24_brand_categories()`: `product_crawler.py:344-381` (3개 URL 후보)
- `crawl_channel()` Cafe24 분기: `product_crawler.py:249-303` (순차 처리 루프)
- `_try_cafe24_products()`: `product_crawler.py:383-508` (최대 80페이지/카테고리, 재시도 없음)
- Cafe24 카테고리 DB 로드: `crawl_products.py:95-114` (edit-shop만, `cate_no IS NOT NULL` 필터)
- 타임아웃 설정: `crawl_products.py` `_CHANNEL_TIMEOUT_SECS["cafe24"] = 600`

---

## 리서치 항목 (Codex 구현 전 조사 필수)

### 1. NULL platform 채널 중 Cafe24 후보 식별

```sql
-- Cafe24 URL 패턴 탐색
SELECT c.id, c.name, c.url, c.country, c.platform, c.channel_type,
       cl.status, cl.products_found, cl.error_msg
FROM channels c
LEFT JOIN crawl_channel_logs cl ON cl.channel_id = c.id
  AND cl.run_id = (SELECT MAX(id) FROM crawl_runs)
WHERE c.is_active = 1
  AND (c.platform IS NULL OR c.platform = 'cafe24')
  AND (c.url LIKE '%cafe24%' OR c.url LIKE '%echosting%' OR c.url LIKE '%sitem%')
ORDER BY c.url;
```

```sql
-- NULL platform + not_supported 채널 전체 URL 목록 (Cafe24 의심 수동 확인)
SELECT c.name, c.url, c.country
FROM crawl_channel_logs cl
JOIN channels c ON c.id = cl.channel_id
WHERE cl.run_id = (SELECT MAX(id) FROM crawl_runs)
  AND cl.status = 'not_supported'
  AND c.platform IS NULL
ORDER BY c.url;
```

### 2. THEXSHOP 실제 카테고리 수 확인

```python
# 구현 전 직접 실행하여 실제 카테고리 수 파악
import httpx
from bs4 import BeautifulSoup

base = "https://www.thexshop.co.kr"
for path in ["/product/maker.html", "/product/brand.html", "/brands2.html"]:
    try:
        r = httpx.get(base + path, timeout=10, follow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")
        links = soup.select("a[href*='cate_no=']:not([href*='product_no='])")
        cate_nos = set()
        for a in links:
            import re
            m = re.search(r"cate_no=(\d+)", a.get("href", ""))
            if m:
                cate_nos.add(m.group(1))
        print(f"{path}: status={r.status_code}, unique cate_no={len(cate_nos)}")
    except Exception as e:
        print(f"{path}: ERROR {e}")
```

→ **카테고리 수에 따라 병렬화 정도 결정** (50개 이상이면 병렬화 필수)

### 3. Cafe24 공식 API 가능성 조사

```
검색어: "cafe24 developer API products list public endpoint"
         "cafe24 open API storefront products no auth"
         "site:developers.cafe24.com products endpoint"
         "cafe24 REST API 제품 목록 공개 접근"
```

- Cafe24 Open API (OAuth 방식) vs HTML 파싱 trade-off
- 판매자 API 토큰 없이 공개 제품 목록 접근 가능한지 확인
- 가능하다면 HTML 파싱 대신 API 전환 검토

### 4. Cafe24 URL 패턴 다양성 및 HTML 구조 조사

```
검색어: "cafe24 브랜드 카테고리 페이지 URL 패턴 목록"
         "cafe24 product list cate_no URL structure 2024"
         "echosting cafe24 skin brand page HTML class names"
         "cafe24 쇼핑몰 브랜드관 URL 구조"
```

- `/product/maker.html` 외에 한국 패션 편집샵에서 흔히 쓰이는 브랜드 카테고리 URL 패턴
- 특정 Cafe24 스킨별 HTML 선택자 차이 (`.prdList`, `li[id^='anchorBoxId_']` 등)
- 브랜드별 cate_no를 나열하는 대표적 페이지 URL 패턴 5가지 이상

---

## 요구사항

### Step 1: Cafe24 채널 플랫폼 태깅 — T-067 `channel_probe.py` 위임 (별도 스크립트 불필요)

> ⚠️ **중복 제거**: 기존 계획의 `probe_cafe24_channels.py`는 T-067 Step 1이 확장하는
> `channel_probe.py`와 Cafe24 감지 로직이 동일하다. 별도 스크립트를 만들지 않는다.

T-067 Step 1의 `channel_probe.py --apply` 실행이 완료되면, 위 7개 채널의 `platform='cafe24'`가
자동으로 업데이트된다. T-066 Step 2 이후 작업의 전제 조건이다.

```bash
# T-067 Step 1 완료 후 platform 업데이트 확인
sqlite3 data/fashion.db "
SELECT name, platform FROM channels
WHERE name IN ('8DIVISION', 'empty', 'grds', 'NOCLAIM', 'PARLOUR', 'SCULP STORE', 'Unipair');
"
# 예상: platform='cafe24'
```

**T-067과의 실행 순서**: T-067 Step 1 → (T-066 Step 2~5 실행 가능)

### Step 2: Cafe24 카테고리 DB 사전 등록 (`scripts/seed_cafe24_categories.py`)

크롤 시마다 HTML 자동 발견하는 대신, `channel_brands.cate_no`를 DB에 미리 등록한다.

```python
"""
Cafe24 채널의 브랜드 카테고리를 DB에 사전 등록 (channel_brands.cate_no).

동작:
  1. platform='cafe24' 채널에 대해 _discover_cafe24_brand_categories() 실행
  2. 발견된 (brand_name, cate_no)를 channel_brands 테이블에 저장
     - brand_name 매칭 전략 (아래 설명):
         a. slug 변환 후 brands.slug 정확 일치
         b. LOWER(brands.name) = LOWER(brand_name)
         c. 일치 없으면 brand_id=NULL로 저장 (cate_no는 보존)
     - 기존 레코드가 있으면 cate_no 업데이트 (upsert)
  3. 등록 후 crawl_products.py가 DB에서 로드하여 자동 발견 스킵

brand_name 매칭 전략 (세부):
  - slug 변환: brand_name → 소문자, 공백→'-', 특수문자 제거
    예: "New Balance" → "new-balance"
  - brands 테이블에서 slug 정확 일치 먼저 시도
  - 실패 시 brands.name ILIKE brand_name 시도
  - 여전히 없으면 brand_id=NULL로 channel_brands 레코드 저장
    (brand_id 없어도 cate_no는 사용 가능 — crawl_products.py에서 cate_no만 활용)

안전장치:
  - dry-run 기본 (--apply 명시 필요)
  - 발견된 카테고리가 0개이면 DB 업데이트 스킵 + 경고 출력
  - brand_id=NULL로 저장된 항목은 WARNING 로그로 표시

인터페이스:
  uv run python scripts/seed_cafe24_categories.py                # 전체 Cafe24 채널
  uv run python scripts/seed_cafe24_categories.py --channel-id 28  # THEXSHOP만
  uv run python scripts/seed_cafe24_categories.py --apply
"""
```

### Step 3: `product_crawler.py` — Cafe24 카테고리 병렬 처리

**파일**: `src/fashion_engine/crawler/product_crawler.py`

`crawl_channel()` 내 Cafe24 분기 (현재 라인 266-278):

```python
# 현재: 순차 처리 O(카테고리 × 페이지)
for brand_name, cate_no in categories:
    cafe24_products.extend(
        await self._try_cafe24_products(channel_url, cate_no, brand_name, currency)
    )

# 수정: asyncio.gather로 병렬 처리 (동시 최대 5개 카테고리)
_CAFE24_CATEGORY_SEM = asyncio.Semaphore(5)  # 모듈 레벨 또는 클래스 속성

async def _fetch_one(brand_name: str, cate_no: str) -> list[ProductInfo]:
    async with _CAFE24_CATEGORY_SEM:
        return await self._try_cafe24_products(
            channel_url, cate_no, brand_name, currency
        )

results = await asyncio.gather(
    *[_fetch_one(n, c) for n, c in categories],
    return_exceptions=True,
)
cafe24_products = [
    p
    for r in results
    if isinstance(r, list)
    for p in r
]
```

→ **100개 카테고리 기준**: 순차 500초 → 병렬(5개 동시) 100초로 단축

### Step 4: `_try_cafe24_products()` — 429/503 재시도 추가

**파일**: `src/fashion_engine/crawler/product_crawler.py`

현재 비-200 응답 시 즉시 `break`. Shopify와 동일하게 재시도 로직 추가:

```python
# 현재 (라인 399-404)
resp = await self._client.get(list_url, timeout=self._timeout)
if resp.status_code != 200:
    break

# 수정: 429/503은 최대 3회 재시도
for attempt in range(3):
    resp = await self._client.get(list_url, timeout=self._timeout)
    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", 10))
        logger.warning("Cafe24 429: %s, retry after %ds", list_url, retry_after)
        await asyncio.sleep(retry_after)
        continue
    if resp.status_code == 503:
        wait = 5 * (attempt + 1)
        logger.warning("Cafe24 503: %s, retry after %ds", list_url, wait)
        await asyncio.sleep(wait)
        continue
    break  # 200 또는 다른 오류 → 재시도 불필요

if resp.status_code != 200:
    break  # 재시도 소진 후 비-200이면 카테고리 순회 종료
```

### Step 5: `_discover_cafe24_brand_categories()` — URL 패턴 확장

**파일**: `src/fashion_engine/crawler/product_crawler.py`

리서치 결과를 바탕으로 candidates 리스트를 확장한다:

```python
# 현재 3개
candidates = [
    f"{base}/product/maker.html",
    f"{base}/product/brand.html",
    f"{base}/brands2.html",
]

# 수정: 리서치 후 확인된 추가 패턴들 포함
# (Codex가 리서치 결과를 반영하여 최소 5개 이상의 패턴으로 확장)
```

**추가 조건**: 첫 번째 성공 URL에서만 파싱하던 로직을 → **모든 URL에서 cate_no 수집 후 합산**으로 변경
(동일 cate_no 중복 제거 필요)

```python
# 현재: 첫 성공 URL에서 즉시 return
for url in candidates:
    ...
    if found:
        return found  # ← 다른 URL에 더 많은 카테고리가 있어도 무시

# 수정: 모든 URL 탐색 후 합산
all_found: dict[str, str] = {}  # cate_no → brand_name
for url in candidates:
    ...
    for name, cate_no in found:
        all_found[cate_no] = name  # 중복 cate_no는 마지막 name으로 덮어쓰기
return list(all_found.items())
```

---

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `src/fashion_engine/crawler/product_crawler.py` | 병렬 처리, 재시도, URL 패턴 확장 (Step 3~5) |
| `scripts/channel_probe.py` | T-067에서 확장 — Cafe24 포함 전체 플랫폼 감지 (Step 1 대체) |
| `scripts/seed_cafe24_categories.py` | 신규 — 카테고리 DB 사전 등록 + brand_name 매칭 (Step 2) |
| `scripts/crawl_products.py` | `_CHANNEL_TIMEOUT_SECS["cafe24"]` 조정 가능 |

---

## DoD (완료 기준)

- [ ] T-067 Step 1 완료 후 Cafe24 8개 채널 모두 `platform='cafe24'` 업데이트 확인 (7개 추가)
- [ ] `scripts/seed_cafe24_categories.py` — THEXSHOP + 8개 Cafe24 채널 카테고리 DB 등록 (brand_name slug 매칭 포함)
- [ ] `crawl_channel()` Cafe24 카테고리 병렬 처리 (`asyncio.gather`, 동시 최대 5개)
- [ ] `_try_cafe24_products()` 429/503 재시도 로직 추가 (최대 3회)
- [ ] `_discover_cafe24_brand_categories()` URL 패턴 5개 이상으로 확장 + 전체 합산 방식 전환
- [ ] THEXSHOP 단독 크롤 600초 타임아웃 없이 완료 (목표: 300초 이내)
- [ ] 8개 Cafe24 채널 중 크롤 성공 채널 수 보고

## 검증

```bash
# Step 1 전제조건: T-067 Step 1이 완료되어야 함
# T-067 channel_probe.py --apply 실행 후 Cafe24 platform 업데이트 확인
sqlite3 data/fashion.db "
SELECT name, platform FROM channels
WHERE name IN ('8DIVISION','empty','grds','NOCLAIM','PARLOUR','SCULP STORE','Unipair');
"

# Step 2: 카테고리 DB 등록 (dry-run)
uv run python scripts/seed_cafe24_categories.py

# Step 2 적용
uv run python scripts/seed_cafe24_categories.py --apply

# Step 3~5 검증: THEXSHOP 단독 크롤 (타임아웃 확인)
uv run python scripts/crawl_products.py --channel-name THEXSHOP

# 결과 확인
sqlite3 data/fashion.db "
SELECT c.name, cl.status, cl.products_found, cl.duration_ms,
       ROUND(cl.duration_ms / 1000.0, 1) as duration_sec
FROM crawl_channel_logs cl
JOIN channels c ON c.id = cl.channel_id
WHERE cl.run_id = (SELECT MAX(id) FROM crawl_runs)
  AND c.platform = 'cafe24';
"
# 예상: status='success', duration_sec < 300

# 카테고리 DB 등록 확인
sqlite3 data/fashion.db "
SELECT c.name, COUNT(cb.cate_no) as cate_count
FROM channels c
LEFT JOIN channel_brands cb ON cb.channel_id = c.id AND cb.cate_no IS NOT NULL
WHERE c.platform = 'cafe24'
GROUP BY c.id, c.name;
"
# 예상: THEXSHOP cate_count > 0
```
