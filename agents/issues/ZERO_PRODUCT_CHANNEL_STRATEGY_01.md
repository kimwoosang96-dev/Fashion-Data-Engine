# ZERO_PRODUCT_CHANNEL_STRATEGY_01: 제품 0개 채널 플랫폼별 맞춤 수집 전략

**Task ID**: T-20260302-067
**Owner**: codex-dev
**Priority**: P1
**Labels**: backend, crawler, channel-strategy, japan, multi-platform

---

## 배경

### 현황 (DB + HTTP 탐색 실측)

**159개 활성 채널 중 77개(48.4%)가 제품 0개** — 원인 분석 완료.

| 유형 | 채널 수 | 즉시 처리 가능 |
|------|---------|-------------|
| Cafe24 (HTTP 탐색으로 확인) | **7개** | T-066 크롤러로 즉시 커버 |
| 일본 SaaS (MakeShop/STORES.jp/OceanNet) | **5개** | 신규 크롤러 필요 |
| SSL/DNS 오류 (물리적 접근 불가) | **8개** | 비활성화 처리 |
| HTTP 403/429 (봇 차단) | **11개** | 헤더 강화 시도 → 불가 시 비활성화 |
| Custom 독립 플랫폼 (미파악) | **~46개** | HTTP 탐색 후 전략 결정 |

### T-066과의 분리

- **T-066**: Cafe24 크롤러 자체 개선 (병렬화, 재시도, 카테고리 캐싱)
- **T-067** (본 과업): Cafe24 외 플랫폼 전략 + 접근 불가 채널 정리 + 전체 채널 재탐색

### 확인된 채널 목록

#### Cafe24로 확인 (T-066 probe_cafe24_channels.py로 처리)
```
8DIVISION     https://www.8division.com
empty         https://www.empty.seoul.kr
grds          https://www.grds.com
NOCLAIM       https://www.noclaim.co.kr
PARLOUR       https://www.parlour.kr
SCULP STORE   https://www.sculpstore.com
Unipair       https://www.unipair.com
```

#### 일본 SaaS (본 과업 핵심 대상)
```
Laid back           https://laidback0918.shop-pro.jp   → MakeShop
elephant TRIBAL     https://elephab.buyshop.jp          → STORES.jp
UNDERCOVER Kanazawa https://undercoverk.theshop.jp      → STORES.jp
SOMEIT              https://someit.stores.jp             → STORES.jp (HTTP 403 확인됨)
TITY                https://tity.ocnk.net               → OceanNet (おちゃのこネット)
```

#### SSL/DNS 오류 (비활성화 대상)
```
CLESSTE             → DNS 해석 불가
Dover Street Market → DNS 해석 불가 (store.doverstreetmarket.com)
Harrods             → 대형 백화점 (크롤 차단 + 봇 방어)
Kerouac             → SSL 인증서 오류
PALACE SKATEBOARDS  → 무한 리다이렉트 (10회 초과)
Pherrow's           → SSL 인증서 오류
TUNE.KR             → SSL 인증서 오류
The Real McCoy's    → SSL 인증서 오류
```

---

## 리서치 항목 (Codex 구현 전 웹서치 필수)

### 1. MakeShop (shop-pro.jp) 공개 API 조사

```
검색어: "MakeShop API 商品一覧 公開エンドポイント shop-pro.jp"
         "makeshop developer API products list no auth"
         "shop-pro.jp REST API 商品一覧取得"
         "site:developer.makeshop.jp products"
```

조사할 사항:
- 인증 없이 접근 가능한 공개 제품 목록 API 존재 여부
- API 엔드포인트 URL 패턴 (`/api/products` 등)
- 없을 경우: HTML 제품 목록 페이지 URL 구조 (`/shop/g/gXXXX/` 또는 `/category/` 등)

### 2. STORES.jp (stores.jp / buyshop.jp / theshop.jp) API 조사

```
검색어: "STORES.jp 商品一覧 API 公開 エンドポイント"
         "stores.jp developer API products no auth"
         "buyshop.jp API 商品 取得"
         "theshop.jp products JSON endpoint"
```

조사할 사항:
- 공개 API 또는 JSON 엔드포인트 존재 여부 (Shopify처럼 `/products.json` 등)
- HTML 파싱 시 제품 카드의 CSS 클래스명 특성
- buyshop.jp / theshop.jp / stores.jp 간 HTML 구조 차이

### 3. OceanNet/おちゃのこネット (ocnk.net) API 조사

```
검색어: "おちゃのこネット API 商品一覧 取得"
         "ocnk.net product list API endpoint"
         "OceanNet 商品データ API"
```

### 4. 403 채널 (BAYCREW'S, Stone Island 등) 봇 차단 방식 조사

```
검색어: "BAYCREW'S ウェブサイト bot protection cloudflare"
         "Stone Island stoneis.com anti-scraping protection"
         "Cloudflare challenge bypass python httpx 2024"
```

→ Cloudflare Protected인 경우: 헤더 강화로 우회 가능한지, 또는 처음부터 비활성화 대상인지 판단

---

## 요구사항

### Step 1: `channel_probe.py` — 일본 SaaS 플랫폼 감지 추가

**파일**: `scripts/channel_probe.py`

기존 probe 로직에 URL 패턴 기반 즉시 감지와 HTTP 신호 감지를 추가:

```python
# 신규: URL 패턴으로 플랫폼 즉시 판별 (HTTP 요청 전)
_URL_PLATFORM_MAP = {
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

def _detect_platform_from_url(url: str) -> str | None:
    for pattern, platform in _URL_PLATFORM_MAP.items():
        if pattern in url:
            return platform
    return None

# 신규: HTTP 응답 헤더/HTML에서 플랫폼 신호 감지
def _detect_platform_from_response(resp: httpx.Response) -> str | None:
    powered_by = resp.headers.get("x-powered-by", "").lower()
    if "makeshop" in powered_by:
        return "makeshop"

    html_lower = resp.text[:5000].lower()
    if "stores.js" in html_lower or "buyshop.jp/js" in html_lower:
        return "stores-jp"
    if "ocnk" in html_lower or "ochanoko" in html_lower:
        return "ochanoko"
    return None
```

`--apply` 시 감지된 플랫폼을 `channels.platform`에 업데이트.

전체 0개 채널 탐색 실행 후 분류 보고서 출력:
- 채널별: 감지된 플랫폼 / HTTP 상태 / 봇 차단 여부
- 플랫폼별 집계: platform → 채널 수

### Step 2: MakeShop 크롤러 (`product_crawler.py` 확장)

**파일**: `src/fashion_engine/crawler/product_crawler.py`

리서치 결과를 기반으로 구현 방식 결정:

```python
async def _try_makeshop_products(
    self,
    channel_url: str,
    currency: str,
) -> list[ProductInfo]:
    """
    MakeShop (shop-pro.jp) 제품 목록 수집.

    우선순위:
      1. 공개 REST API가 있으면 → API 호출 (리서치 결과 기반)
      2. 없으면 → HTML 제품 목록 페이지 파싱 (폴백 전략):

         폴백 전략 (리서치로 확인 후 구현):
           a. 카테고리 목록 페이지 탐색:
              후보 URL: /shop/list.cgi, /shop/g/g0/, /products/, /item/list.html
              → <a href*="cate_no=" or href*="gid="> 링크 추출
           b. 각 카테고리 페이지에서 제품 카드 파싱:
              후보 선택자: .item_list li, .product_list .item, div[class*="item"]
              → 제품명: .item_name, .product_name, h2, h3
              → 가격: .price, .item_price, span[class*="price"]
              → 이미지: img.main_image, .thumb img
           c. 페이지네이션: ?page=N 또는 ?start=N×100 패턴 순회
    """
    # 리서치 결과 반영하여 구현
    # 단계: (1) 공개 API 시도 → (2) 폴백 HTML 파싱
    ...
```

`crawl_channel()` fallback 체인에 추가:
```python
# 기존: Shopify → Cafe24 → WooCommerce
# 수정: Shopify → Cafe24 → WooCommerce → MakeShop → STORES.jp
if not products:
    platform = self._detect_platform(channel_url)
    if platform == "makeshop":
        products = await self._try_makeshop_products(channel_url, currency)
    elif platform == "stores-jp":
        products = await self._try_stores_jp_products(channel_url, currency)
    elif platform == "ochanoko":
        products = await self._try_ochanoko_products(channel_url, currency)
```

### Step 3: STORES.jp 크롤러 (`product_crawler.py` 확장)

**파일**: `src/fashion_engine/crawler/product_crawler.py`

```python
async def _try_stores_jp_products(
    self,
    channel_url: str,
    currency: str,
) -> list[ProductInfo]:
    """
    STORES.jp 패밀리 (stores.jp / buyshop.jp / theshop.jp) 제품 목록 수집.

    우선순위:
      1. JSON API 엔드포인트 시도 (리서치 결과 기반):
         - 후보: /api/v1/items, /items.json, /products.json
         - 응답이 JSON 배열이면 파싱
      2. 없으면 → HTML 파싱 (폴백 전략):

         폴백 전략 (리서치로 선택자 확인 후 구현):
           a. 제품 목록 페이지 탐색:
              후보 URL: /items, /products, / (루트가 제품 목록인 경우)
           b. 제품 카드 파싱:
              STORES.jp 공통 선택자 (리서치로 확인):
              - 제품 카드: .item-list__item, [class*="item-card"], .storeItem
              - 제품명: .item-list__item-name, .item__name, h2
              - 가격: .item-list__item-price, .item__price
              - 이미지: .item-list__item-image img, .item__image img
              buyshop.jp / theshop.jp는 HTML 구조 동일하나 선택자 일부 차이
              → 리서치로 확인 후 플랫폼별 분기 처리
           c. 페이지네이션: ?page=N 패턴 순회, max 50페이지
           d. SOMEIT (stores.jp) 403 대응:
              User-Agent + Referer 헤더 추가 후 재시도, 실패 시 skip
    """
    # 리서치 결과 반영하여 구현
    # 단계: (1) JSON API 시도 → (2) 폴백 HTML 파싱
    ...
```

### Step 4: 접근 불가 채널 비활성화 (`scripts/deactivate_dead_channels.py` 확장)

> ⚠️ **중복 제거**: T-063에서 이미 `scripts/deactivate_dead_channels.py`가 구현되어 있다.
> 별도 스크립트를 만들지 않고, 기존 스크립트에 `--inaccessible-only` 모드를 추가한다.

**파일**: `scripts/deactivate_dead_channels.py` (기존 파일 확장)

```python
"""
기존 deactivate_dead_channels.py에 --inaccessible-only 모드 추가.

추가 비활성화 기준 (--inaccessible-only 시):
  - DNS 해석 실패 (NXDOMAIN, socket.gaierror)
  - SSL 인증서 오류 (httpx.ConnectError with SSL 관련 메시지)
  - 무한 리다이렉트 (TooManyRedirects, 10회 초과)
  - HTTP 404/410 (사이트 완전 삭제됨)

비활성화 사유 기록:
  - channels 모델에 deactivation_reason 컬럼 없음 → 별도 로그 파일에 기록
  - 로그 파일: logs/deactivate_inaccessible_YYYYMMDD.json
  - 형식: {"channel_id": N, "name": "...", "url": "...", "reason": "dns_error", "checked_at": "..."}

안전장치:
  - dry-run 기본 (--apply 명시 시 적용)
  - brand-store 채널은 기본 skip (--include-brand-stores로 포함 가능)

인터페이스:
  uv run python scripts/deactivate_dead_channels.py --inaccessible-only           # dry-run
  uv run python scripts/deactivate_dead_channels.py --inaccessible-only --apply   # 적용
  uv run python scripts/deactivate_dead_channels.py --inaccessible-only --apply --yes  # 확인 없이
"""
```

**확정 비활성화 대상** (Codex가 probe 후 최종 확인):

| 채널 | 사유 |
|------|------|
| CLESSTE | DNS NXDOMAIN |
| Kerouac | SSL 인증서 오류 |
| TUNE.KR | SSL 인증서 오류 |
| The Real McCoy's | SSL 인증서 오류 |
| Pherrow's | SSL 인증서 오류 |
| PALACE SKATEBOARDS | 무한 리다이렉트 |

**보류 (수동 판단 필요)**:
- Dover Street Market: DNS 오류이나 고급 패션 채널 → URL 재확인 후 결정
- Harrods: 접근 가능하나 강한 봇 방어 → `channel_type` 재분류 권장

### Step 5: 전체 0개 채널 HTTP 탐색 + 분류 보고서

Codex가 직접 실행하여 결과를 WORK_LOG에 기록:

```bash
# 전체 제품 0개 채널 HTTP 탐색 (platform 자동 업데이트)
uv run python scripts/channel_probe.py --apply

# 탐색 결과 저장
uv run python scripts/channel_probe.py > reports/channel_probe_$(date +%Y%m%d).csv
```

결과 분류 기준:
1. 신규 감지된 Cafe24 → T-066 `seed_cafe24_categories.py` 후 크롤 실행
2. MakeShop/STORES.jp/OceanNet → Step 2~3으로 처리
3. HTTP 200이지만 수집 불가 → HTML 구조 분석 후 다음 과업 수립
4. 403 반복 채널 → Step 4 `deactivate_dead_channels.py --inaccessible-only` 후보로 보고

---

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `src/fashion_engine/crawler/product_crawler.py` | MakeShop/STORES.jp/OceanNet 크롤러 추가 (Step 2~3 + OceanNet) |
| `scripts/channel_probe.py` | 일본 SaaS URL 패턴 + HTTP 신호 감지 추가 (Step 1) |
| `scripts/deactivate_dead_channels.py` | 기존 T-063 스크립트 확장 — `--inaccessible-only` 모드 추가 (Step 4) |

---

## DoD (완료 기준)

- [ ] `channel_probe.py` — MakeShop/STORES.jp/OceanNet/Cafe24 URL 패턴 + HTTP 신호 감지 추가, 전체 0개 채널 탐색 실행
- [ ] 전체 0개 채널 플랫폼별 분류 보고서 출력
- [ ] MakeShop 크롤러 `_try_makeshop_products()` 구현 (공개 API 또는 HTML 파싱 폴백)
- [ ] STORES.jp 크롤러 `_try_stores_jp_products()` 구현 (JSON API 또는 HTML 파싱 폴백)
- [ ] OceanNet 크롤러 `_try_ochanoko_products()` 구현 (TITY/ocnk.net 대상, 리서치 기반)
- [ ] `scripts/deactivate_dead_channels.py --inaccessible-only` — SSL/DNS 오류 채널 6+개 비활성화, 사유를 JSON 로그로 기록
- [ ] 크롤 가능한 신규 채널 ≥ 3개 추가 달성 (MakeShop/STORES.jp/OceanNet 중 성공 채널)
- [ ] 탐색 보고서: 나머지 Custom 채널 현황 정리 (다음 과업 수립용)

## 검증

```bash
# Step 1: 전체 0개 채널 탐색 (platform 자동 업데이트)
uv run python scripts/channel_probe.py --apply

# 플랫폼 분류 현황
sqlite3 data/fashion.db "
SELECT platform, COUNT(*) as n
FROM channels WHERE is_active=1
GROUP BY platform ORDER BY n DESC;
"

# Step 2~3: MakeShop/STORES.jp/OceanNet 크롤 테스트
uv run python scripts/crawl_products.py --channel-name 'Laid back'
uv run python scripts/crawl_products.py --channel-name 'elephant TRIBAL fabrics'
uv run python scripts/crawl_products.py --channel-name 'TITY'

# Step 4: 비활성화 dry-run (기존 스크립트의 --inaccessible-only 모드)
uv run python scripts/deactivate_dead_channels.py --inaccessible-only

# Step 4 적용
uv run python scripts/deactivate_dead_channels.py --inaccessible-only --apply

# 비활성화 결과 확인
sqlite3 data/fashion.db "
SELECT name, is_active, platform
FROM channels
WHERE name IN ('CLESSTE', 'Kerouac', 'TUNE.KR', 'The Real McCoy''s', 'Pherrow''s', 'PALACE SKATEBOARDS')
ORDER BY name;
"
# 예상: is_active=0

# 비활성화 사유 로그 확인
cat logs/deactivate_inaccessible_*.json

# 전체 수집 성과 확인
sqlite3 data/fashion.db "
SELECT c.name, c.platform, COUNT(p.id) as product_count
FROM channels c
LEFT JOIN products p ON p.channel_id = c.id AND p.is_active=1
WHERE c.platform IN ('makeshop', 'stores-jp', 'ochanoko')
GROUP BY c.id, c.name, c.platform
ORDER BY product_count DESC;
"
```
