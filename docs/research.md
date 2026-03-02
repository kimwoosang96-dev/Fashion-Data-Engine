# Fashion Data Engine — 프로젝트 리서치

> 작성일: 2026-03-01 | 최종 업데이트: 2026-03-02 (Phase 22 기준)
> 목적: 코드베이스 전체 파악. 이 문서를 기반으로 plan.md를 작성한다.

---

## 목차

1. [프로젝트 한 줄 요약](#1-프로젝트-한-줄-요약)
2. [전체 구조](#2-전체-구조)
3. [데이터베이스 모델](#3-데이터베이스-모델)
4. [핵심 개념: product_key / normalized_key](#4-핵심-개념-product_key--normalized_key)
5. [크롤링 시스템](#5-크롤링-시스템)
6. [API 엔드포인트 전체 목록](#6-api-엔드포인트-전체-목록)
7. [프론트엔드 페이지](#7-프론트엔드-페이지)
8. [알림 시스템 (Discord)](#8-알림-시스템-discord)
9. [스케줄러 (자동화)](#9-스케줄러-자동화)
10. [스크립트 전체 목록](#10-스크립트-전체-목록)
11. [Alembic 마이그레이션 이력](#11-alembic-마이그레이션-이력)
12. [배포 구조 (Railway + Vercel)](#12-배포-구조-railway--vercel)
13. [현재 데이터 현황](#13-현재-데이터-현황)
14. [알려진 문제점 및 한계](#14-알려진-문제점-및-한계)
15. [설정 및 환경변수](#15-설정-및-환경변수)
16. [Makefile 주요 커맨드](#16-makefile-주요-커맨드)

---

## 1. 프로젝트 한 줄 요약

**여러 패션 판매채널(편집숍, 브랜드 공식몰 등)의 제품 가격을 수집하여, 동일 제품의 채널별 가격을 비교하고 구매 최적 타이밍을 분석하는 플랫폼.**

---

## 2. 전체 구조

```
fashion-data-engine/
├── src/fashion_engine/       ← 백엔드 (Python, FastAPI)
│   ├── api/                  ← HTTP 엔드포인트 라우터 (12개 모듈)
│   ├── models/               ← DB 테이블 정의 (SQLAlchemy, 17개 모델)
│   ├── services/             ← 비즈니스 로직 (쿼리, 계산)
│   ├── crawler/              ← 데이터 수집 (Shopify REST API, Cafe24 HTML)
│   └── config.py             ← 환경변수 설정
│
├── frontend/src/             ← 프론트엔드 (Next.js, TypeScript)
│   ├── app/                  ← 페이지 17개
│   ├── components/           ← 공통 컴포넌트 (Shadcn/UI 기반)
│   └── lib/                  ← API 호출 함수, 타입 정의
│
├── scripts/                  ← 실행 스크립트 33개 (크롤, 감사, 시드, 정제 등)
├── alembic/                  ← DB 마이그레이션 (16개 버전)
├── agents/                   ← Codex 협업 과업지시 (TASK_DIRECTIVE.md + issues/)
├── docs/                     ← 리서치 및 GPT Pro 의뢰 문서
├── data/fashion.db           ← 로컬 SQLite DB
├── logs/                     ← 스케줄러/크롤 로그
├── Makefile                  ← 자주 쓰는 명령어 모음
├── railway.json              ← Railway 배포 설정
└── .env                      ← 환경변수 (Git 제외)
```

### 기술 스택

| 레이어 | 기술 |
|--------|------|
| 백엔드 | Python 3.12, FastAPI, SQLAlchemy 2.0 (async) |
| DB | SQLite (로컬 개발) / PostgreSQL (Railway 운영) |
| DB 마이그레이션 | Alembic |
| 크롤링 | httpx (Shopify REST), BeautifulSoup4 (HTML 파싱) |
| 프론트엔드 | Next.js 14, TypeScript, Tailwind CSS, Shadcn/UI |
| 배포 | Railway (백엔드 API), Vercel (프론트엔드) |
| 알림 | Discord Webhook |
| 스케줄링 | APScheduler (Python) |
| 에이전트 협업 | Claude Code (PM/인터랙티브) + OpenAI Codex (벌크 구현) |

---

## 3. 데이터베이스 모델

**18개 테이블** (alembic_version 제외)

### 3.1 Channel (판매채널)

쿠팡, PATTA Korea, New Balance 공식몰처럼 제품을 파는 온라인 쇼핑몰.

```
주요 컬럼:
  id, name, url, original_url
  channel_type : brand-store | edit-shop | department-store | marketplace | non-fashion | secondhand-marketplace
  platform     : shopify | cafe24 | etc (자동 감지)
  country      : KR / JP / US / UK / SE / ES / IT / HK 등
  instagram_url: 브랜드 인스타그램 URL
  is_active    : 크롤 대상 여부
```

**현황**: 159개 채널. 이 중 81개에서 제품 수집됨, 78개는 제품 0개.

---

### 3.2 Brand (브랜드)

```
tier 분류:
  high-end  : 루이비통, 에르메스 등
  premium   : New Balance, Stone Island 등
  street    : Supreme, Palace 등
  sports    : 나이키, 아디다스 등
  spa       : 자라, H&M 등

주요 컬럼:
  id, name, slug, name_ko, origin_country
  description, description_ko, official_url, instagram_url
  tier
```

**현황**: 2,570개 브랜드. 이 중 제품이 있는 브랜드 1,420개.

---

### 3.3 Product (제품)

크롤링으로 수집된 실제 판매 제품.

```
주요 컬럼:
  channel_id    : 어느 채널에서 수집됐는지
  brand_id      : 어느 브랜드인지 (NULL 가능 — 현재 23.6% NULL)
  category_id   : 카테고리 (NULL 가능)
  name          : 제품명
  vendor        : Shopify의 vendor 필드 (브랜드명 원본 텍스트)
  product_key   : "brand-slug:handle" — 교차채널 동일 제품 식별자 (Shopify)
  normalized_key: 정규화된 교차채널 매칭 키 (product_key보다 정교)
  match_confidence: normalized_key 신뢰도 (0.0~1.0)
  gender        : men / women / unisex / kids
  subcategory   : shoes / outer / top / bottom / bag / cap / accessory
  sku, url, image_url, tags, description
  is_active     : 현재 판매 가능 여부
  is_new        : 신상품 여부
  is_sale       : 세일 중 여부
  archived_at   : 품절 전환된 시간 (NULL이면 현재 판매 중)
```

**현황**: 80,096개 (로컬). 이 중 세일 19,997개(25%).

---

### 3.4 PriceHistory (가격 이력)

```
product_id    : 어느 제품인지
price         : 현재가 (원래 통화)
original_price: 정가 (세일 시 더 높음)
currency      : 원래 통화 (KRW / USD / JPY 등)
is_sale       : 당시 세일 여부
discount_rate : 할인율 (%) = (1 - 현재가/정가) × 100
crawled_at    : 이 가격을 수집한 시간
```

**현황**: 81,892개 레코드.

---

### 3.5 ExchangeRate (환율)

```
from_currency → to_currency(KRW) → rate
예: USD → KRW → 1,440.92
    EUR → KRW → 1,700.68
    JPY → KRW → 9.23
```

open.er-api.com에서 일 1회 자동 업데이트. 현재 12개 통화 지원.

| 통화 | KRW 환율 (2026-02-28 기준) |
|------|--------------------------|
| USD | 1,440.92 |
| EUR | 1,700.68 |
| GBP | 1,941.75 |
| JPY | 9.23 |
| HKD | 184.13 |
| SEK | 159.36 |
| DKK | 228.00 |
| SGD | 1,138.95 |
| CAD | 1,054.85 |
| AUD | 1,024.59 |
| TWD | (지원) |
| CNY | (지원) |

---

### 3.6 ChannelBrand (채널-브랜드 링크)

```
channel_id : 채널
brand_id   : 브랜드
cate_no    : Cafe24 카테고리 번호 (Cafe24 채널용)
crawled_at : 브랜드가 이 채널에서 마지막 발견된 시간
```

**현황**: 3,245개 링크.

---

### 3.7 Category (카테고리)

```
id, name, name_en, slug
parent_id  : 상위 카테고리 (self-join, 계층 구조)
level      : 깊이 (1=최상위)
```

---

### 3.8 BrandCollaboration (협업)

```
brand_a_id, brand_b_id : 협업한 두 브랜드
collab_name            : 예) "Adidas x Wales Bonner SS26"
collab_category        : footwear / apparel / accessories / lifestyle
release_year           : 발매 연도
hype_score             : 0-100 (취급 채널 수 × 10, 최대 100)
source_url, notes
```

**현황**: 34개 협업 등록.

---

### 3.9 BrandDirector (크리에이티브 디렉터)

```
brand_id    : 브랜드
name        : 디렉터명
role        : 역할 (기본값: "Creative Director")
start_year  : 재직 시작 연도
end_year    : 퇴임 연도 (NULL = 현직)
note        : 메모
```

**현황**: 125명 등록.

---

### 3.10 FashionNews (뉴스)

```
entity_type : "brand" | "channel"
entity_id   : 관련 브랜드/채널 ID
title, url, summary
published_at: 발행일
source      : "instagram" | "website" | "press" | "youtube"
crawled_at
```

---

### 3.11 Purchase (구매 이력)

사용자가 직접 입력하는 구매 기록.

```
product_key       : "brand-slug:handle"
product_name      : 제품명 (스냅샷)
brand_slug, channel_name, channel_url
paid_price_krw    : 실제 지불 금액
original_price_krw: 정가
purchased_at      : 구매 일시
notes             : 메모
```

---

### 3.12 WatchListItem (관심 목록)

Discord 알림을 받을 대상을 지정.

```
watch_type   : "brand" | "channel" | "product_key"
watch_value  : slug, URL, 또는 product_key
notes        : 메모

⚠️ 중요: WatchList가 비어있으면 모든 알림이 차단됨.
   즉, 알림을 받으려면 반드시 항목을 추가해야 함.
```

---

### 3.13 Drop (발매/드롭 정보)

크롤러가 감지한 신제품 또는 예정 발매 정보.

```
brand_id, product_name, product_key
source_url, image_url, price_krw
release_date  : 발매 예정일
status        : "upcoming" (예정) | "released" (발매됨) | "sold_out" (품절)
detected_at, notified_at
```

---

### 3.14 CrawlRun (크롤 실행 단위)

전체 크롤 세션 하나를 나타냄.

```
started_at, finished_at
status           : "running" | "done" | "failed"
total_channels   : 크롤 대상 채널 수
done_channels    : 완료된 채널 수
new_products     : 신규 발견 제품 수
updated_products : 업데이트된 제품 수
error_channels   : 실패한 채널 수
```

---

### 3.15 CrawlChannelLog (채널별 크롤 결과)

채널 하나당 하나의 레코드.

```
run_id, channel_id
status         : "success" | "failed" | "skipped"
products_found, products_new, products_updated
error_msg      : 실패 시 오류 메시지 (최대 500자)
error_type     : 실패 유형 코드 (T-059 신규 — 에러 분류 표준화)
                 "http_403" | "http_404" | "http_429" | "http_5xx"
                 "timeout" | "parse_error" | "not_supported" | NULL
strategy       : 사용된 크롤 전략 (shopify / cafe24 등)
duration_ms    : 크롤 소요 시간 (ms)
crawled_at
```

---

### 3.16 ProductCatalog (제품 카탈로그)

normalized_key 기준으로 동일 제품을 하나로 집계한 뷰.

```
normalized_key  : 정규화된 교차채널 매칭 키
canonical_name  : 대표 제품명
brand_id
gender, subcategory, tags
trend_score     : 트렌드 점수 (0.0~1.0)
listing_count   : 판매 채널 수
min_price_krw, max_price_krw
is_sale_anywhere: 어느 채널에서든 세일 중 여부
first_seen_at, updated_at
```

**현황**: **64,075개** (Phase 22 CC-3에서 `build_product_catalog.py` 실행 완료).

---

### 3.17 ChannelNote (채널 운영 메모)

운영자가 채널별로 작성하는 메모 (관리자 어드민에서 인라인 작성).

```
channel_id
note_type  : "issue" | "memo" | "action"
body       : 메모 내용
operator   : 작성자 (관리자 토큰 기반)
created_at
resolved_at: NULL이면 미해결, 값이 있으면 해결됨
```

---

## 4. 핵심 개념: product_key / normalized_key

### product_key (1세대)

**`product_key = "{brand-slug}:{product-handle}"`**

```
예시:
  new-balance:2002r
  nike:air-force-1-low
  032c:selfie-sweater-4
```

Shopify `/products.json` 응답의 `vendor`(→ brand-slug)와 `handle` 필드를 조합.
Shopify 기반이 아닌 채널은 product_key가 NULL.

### normalized_key (2세대, 강화)

product_key보다 정교한 교차채널 매칭 키.
- vendor명 부정확 문제 보완 (`match_confidence` 0.0~1.0)
- 동일 제품이 다른 vendor명으로 등록된 경우도 매칭
- `backfill_normalized_key.py`로 기존 제품에 소급 적용

**왜 필요한가?**

동일한 제품이 여러 채널에서 판매될 때, 각 채널의 DB 행은 서로 다른 `product.id`를 가진다.
normalized_key가 있어야 "이건 같은 제품"이라는 걸 알 수 있다.

```
PATTA Korea에서 파는 New Balance 2002R: product.id = 74
무신사에서 파는 New Balance 2002R:     product.id = 2341
→ 둘 다 normalized_key = "new-balance:new-balance-2002r" → 가격 비교 가능
```

---

## 5. 크롤링 시스템

### 5.1 제품 크롤러 (product_crawler.py)

**지원 플랫폼**: Shopify, Cafe24

```
크롤 흐름:
1. channels 테이블에서 active 채널 목록 조회 (platform 필터 가능)
2. asyncio.Semaphore(5)로 최대 5채널 병렬 크롤
3. 각 채널에 대해:
   a. [Shopify] GET {url}/products.json?limit=250&page=N (최대 16페이지)
      [Cafe24 ] HTML 파싱 /category/{cate_no}
   b. 통화 자동 감지 (URL 서브도메인 기반):
      kr. → KRW, jp. → JPY, eu. → EUR, uk. → GBP, us. → USD
   c. 비패션 제품 필터링 (T-054 ✅ 구현 완료):
      → vendor가 _VENDOR_DENYLIST에 포함 시 skip (route, routeins, extend 등)
      → product_type이 _PRODUCT_TYPE_DENYLIST에 포함 시 skip
      → title 키워드가 _TITLE_KEYWORD_DENYLIST에 포함 시 skip
   d. normalized_key 생성 (정규화된 교차채널 식별자)
   e. DB upsert (기존 제품이면 가격 업데이트, 신규면 INSERT)
   f. PriceHistory 기록 (크롤마다 새 행)
4. 429/503 응답 시 Retry-After 헤더 준수 후 재시도 (tenacity)
5. CrawlRun/CrawlChannelLog에 결과 기록
6. 변화 감지 시 Discord 알림:
   🚀 신규 product_key
   🔥 is_sale False → True 전환
   📉 가격 10%+ 하락
```

**실행 방법:**
```bash
make crawl                                  # 전체 크롤 (크롤 완료 후 ProductCatalog 자동 증분 빌드)
uv run python scripts/crawl_products.py --limit 3          # 테스트 (3채널)
uv run python scripts/crawl_products.py --channel-type brand-store
uv run python scripts/crawl_products.py --channel-id 42    # 특정 채널만
uv run python scripts/crawl_products.py --no-alerts        # Discord 알림 없이
uv run python scripts/crawl_products.py --skip-catalog     # catalog 증분 빌드 생략
```

**병렬화**: `asyncio.Semaphore(5)` + 채널당 독립 `ProductCrawler` 인스턴스.
CrawlRun 카운터 업데이트는 `asyncio.Lock()` + 원자적 SQL UPDATE.

---

### 5.2 브랜드 크롤러 (brand_crawler.py)

**지원 플랫폼**: Shopify (자동), Cafe24, 채널별 커스텀 HTML 파싱

채널마다 HTML 구조가 달라서, `CHANNEL_STRATEGIES` 딕셔너리에 채널별 CSS 선택자를 등록.

```
예) 8division.com: "ul.sub-menu.sub-menu-brands > li > a"
    bdgastore.com: "a[href*='/brands/']"
    cafe24 기반: "a[href*='cate_no=']"
```

Shopify 채널은 자동 처리 가능: `/products.json`의 `vendor` 필드에서 브랜드명 추출.

---

### 5.3 드롭 크롤러 (drop_crawler.py)

신제품/예정 발매 감지.

```
방법 1: GET {channel}/products.json?sort_by=created-at-desc&limit=20
        → DB에 없는 product_key = 신제품 (is_new=True)

방법 2: GET {channel}/products.json?tag=coming-soon&limit=50
        → status="upcoming" (예정 발매)
```

---

### 5.4 뉴스 크롤러 (crawl_news.py)

RSS 피드에서 패션 뉴스 수집.

```
피드:
  - https://hypebeast.com/feed
  - https://www.highsnobiety.com/feed/
  - https://sneakernews.com/feed/
  - https://www.complex.com/style/rss
```

---

### 5.5 현재 크롤 가능한 채널 현황

| 채널 타입 | 전체 | 제품 있음 | 제품 0개 |
|----------|------|---------|---------|
| brand-store | 75 | 26 | **49** |
| edit-shop | 80 | 55 | **25** |
| department-store | 2 | 0 | 2 |
| secondhand-marketplace | 1 | 0 | 1 |
| non-fashion | 1 | 0 | 1 |

edit-shop 55개 제품 있음 = Cafe24 크롤러 Phase 16에서 구현됨.

---

### 5.6 플랫폼 지원 현황

| 플랫폼 | 방식 | 지원 |
|--------|------|------|
| Shopify | `/products.json` REST API | ✅ |
| Cafe24 | HTML 파싱 `/category/{cate_no}` | ✅ |
| stores.jp / buyshop.jp | 미지원 | ❌ |
| MakeShop (shop-pro.jp) | 미지원 | ❌ |
| ocnk.net / theshop.jp | 미지원 | ❌ |

---

## 6. API 엔드포인트 전체 목록

### 공개 API (인증 불필요)

**Channels**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/channels/` | 전체 채널 목록 |
| GET | `/channels/highlights` | 채널 하이라이트 |
| GET | `/channels/landscape` | 시각화용 채널 지형 데이터 |
| GET | `/channels/{id}` | 채널 상세 |
| GET | `/channels/{id}/brands` | 채널 취급 브랜드 목록 |

**Brands**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/brands/` | 브랜드 목록 (tier 필터) |
| GET | `/brands/landscape` | 브랜드-채널 전체 지형 데이터 |
| GET | `/brands/highlights` | 브랜드별 신상품 현황 |
| GET | `/brands/search?q=` | 브랜드명 검색 (한글/영문) |
| GET | `/brands/{slug}` | 브랜드 상세 |
| GET | `/brands/{slug}/channels` | 브랜드 취급 채널 목록 |
| GET | `/brands/{slug}/products` | 브랜드별 제품 목록 |
| GET | `/brands/{slug}/collabs` | 브랜드 협업 목록 |
| GET | `/brands/{slug}/directors` | 브랜드 디렉터 목록 |

**Products**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/products/` | 제품 목록 (brand, is_sale 필터) |
| GET | `/products/sales` | 세일 제품 (brand/tier/gender/category/가격 필터) |
| GET | `/products/search?q=` | 제품명 검색 |
| GET | `/products/sales-highlights` | 세일 하이라이트 (product_key 기준 최저가) |
| GET | `/products/sales-count` | 세일 제품 총 개수 |
| GET | `/products/related-searches?q=` | 연관 검색어 제안 |
| **GET** | **`/products/compare/{product_key}`** | **전 채널 가격 비교 ← 핵심!** |
| GET | `/products/price-history/{product_key}` | 30일 가격 이력 |
| GET | `/products/archive` | 품절 제품 목록 |
| GET | `/products/multi-channel` | 2개+ 채널 판매 제품 (가격 스프레드) |

**Catalog**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/catalog/` | ProductCatalog 목록 (brand/gender/subcategory/on_sale/price/검색 필터) |
| GET | `/catalog/{normalized_key}` | 특정 제품의 전 채널 판매 정보 |

**기타**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/collabs/` | 협업 목록 (hype_score 내림차순) |
| GET | `/collabs/hype-by-category` | 카테고리별 평균 hype_score |
| POST | `/purchases/` | 구매 기록 추가 |
| GET | `/purchases/` | 구매 목록 |
| GET | `/purchases/stats` | 구매 통계 |
| GET | `/purchases/{id}/score` | 구매 성공도 (S/A/B/C/D) |
| DELETE | `/purchases/{id}` | 구매 기록 삭제 |
| GET | `/watchlist/` | 관심 목록 |
| POST | `/watchlist/` | 관심 항목 추가 |
| DELETE | `/watchlist/{id}` | 관심 항목 삭제 |
| GET | `/drops/upcoming` | 예정 발매 |
| GET | `/drops/` | 드롭 목록 |
| POST | `/drops/` | 수동 드롭 추가 |
| GET | `/news/` | 패션 뉴스 |
| GET | `/directors/` | 디렉터 목록 |
| GET | `/directors/by-brand` | 브랜드별 디렉터 |
| GET | `/health` | 서버 헬스체크 |

---

### 관리자 API (Bearer Token 필요)

```
Authorization: Bearer {ADMIN_BEARER_TOKEN}
```

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/admin/stats` | DB 전체 통계 |
| GET | `/admin/channels-health` | 채널 헬스 (브랜드/제품 수 기반) |
| GET | `/admin/crawl-status` | 채널별 마지막 크롤 시간 (ok/stale/never) |
| **GET** | **`/admin/channel-signals`** | **채널별 크롤 건강도 + 트래픽 라이트 (red/yellow/green)** |
| POST | `/admin/crawl-trigger` | 수동 크롤 실행 (job=products/brands/drops/channel) |
| GET | `/admin/crawl-runs` | 크롤 실행 목록 |
| GET | `/admin/crawl-runs/{run_id}` | 특정 크롤 실행 상세 |
| GET | `/admin/crawl-runs/{run_id}/stream` | SSE 실시간 크롤 진행 스트림 |
| GET | `/admin/collabs` | 협업 목록 |
| POST | `/admin/collabs` | 협업 추가 |
| DELETE | `/admin/collabs/{id}` | 협업 삭제 |
| GET | `/admin/brand-channel-audit` | 브랜드-채널 혼재 감사 |
| GET | `/admin/directors` | 디렉터 목록 |
| POST | `/admin/directors` | 디렉터 추가 |
| DELETE | `/admin/directors/{id}` | 디렉터 삭제 |
| PATCH | `/admin/brands/{id}/instagram` | 브랜드 인스타그램 URL 수정 |
| PATCH | `/admin/channels/{id}/instagram` | 채널 인스타그램 URL 수정 |
| GET | `/admin/channels/{id}/notes` | 채널 운영 메모 목록 |
| POST | `/admin/channels/{id}/notes` | 채널 운영 메모 추가 |
| PATCH | `/admin/channels/{id}/notes/{note_id}/resolve` | 메모 해결 처리 |
| **GET** | **`/admin/catalog-stats`** | **ProductCatalog 현황 요약 (T-058 신규)** |

---

## 7. 프론트엔드 페이지

**17개 페이지**

### 네비게이션 (좌측 사이드바)

```
📊 대시보드        /
🔥 세일 제품       /sales
⚔️  경쟁            /compete
🏪 판매채널       /channels
🏷️ 브랜드          /brands
🧠 디렉터          /directors
📰 뉴스            /news
🤝 협업            /collabs
❤️ 관심목록       /watchlist
🛍️ 구매이력       /purchases
🚀 드롭            /drops
🗺️ 세계지도       /map
⚙️ 운영관리       /admin
```

### 주요 페이지 설명

**`/` (대시보드)**
- 세일 제품 60개 그리드 표시 (product_key 기준 중복 제거, 최저가 우선)
- 검색창: 브랜드 8개 + 제품 10개 실시간 제안
- 채널/브랜드 요약 통계

**`/compare/[product_key]` (가격 비교) — 핵심 페이지**
- 동일 product_key를 가진 모든 채널의 가격을 KRW 오름차순으로 정렬
- 최저가 채널 강조 (에메랄드 색상)
- 30일 가격 변동 차트 (SVG 기반 멀티라인)
- 뒤로가기 버튼

**`/sales` (세일 제품)**
- 성별/카테고리/가격범위 필터
- 무한스크롤 (Intersection Observer)
- OOS 제품은 하단 정렬 + 이미지 그레이스케일
- 각 제품 카드 → `/compare/{product_key}` 연결

**`/compete` (경쟁 제품)**
- 2개+ 채널에서 팔리는 제품 목록
- 채널 수 / 가격 스프레드(최고가-최저가) 정렬

**`/brands/[slug]`**
- 브랜드 상세: 채널 목록, 제품 목록, 디렉터 이력, 협업

**`/purchases` (구매 이력)**
- 내가 구매한 제품 기록
- 성공도 점수 (S~D): 과거 가격 데이터 백분위 기반
- "역대 상위 5%" 같은 배지 표시

**`/watchlist` (관심 목록)**
- 브랜드/채널/제품_key 단위로 알림 대상 지정
- ⚠️ 비어있으면 Discord 알림이 전혀 오지 않음

**`/admin` (운영 관리) — 3탭 구조**
- **DB 상태 탭**: 통계, 환율, 디렉터, 인스타그램 URL, 협업, 브랜드-채널 감사
- **크롤러 탭**: 수동 크롤 트리거, 채널별 크롤 현황, SSE 실시간 크롤 모니터
- **채널 관리 탭**: 채널 헬스 테이블 + 인라인 운영 메모 작성/해결

**`/map` (세계지도)**
- 채널 국가별 분포 시각화

---

## 8. 알림 시스템 (Discord)

### 알림 종류

| 알림 | 조건 | 색상 |
|------|------|------|
| 🚀 신제품 | product_key가 DB에 처음 등장 | 파랑 |
| 🔥 세일 시작 | is_sale False → True 전환 | 주황 |
| 📉 가격 하락 | 직전 가격 대비 10%+ 하락 | 초록 |
| 🔔 감사 알림 | 주간 데이터 감사에서 ERROR≥1 또는 WARNING≥3 | 빨강 |

### 알림 필터링 (WatchList)

```
WatchList가 비어있음 → 모든 알림 차단 (알림 없음)
WatchList에 항목 있음 → 매칭되는 것만 알림

예:
  watch_type="brand", watch_value="new-balance"
  → New Balance 관련 제품만 알림

  watch_type="product_key", watch_value="nike:air-force-1"
  → 이 특정 제품만 알림
```

### 설정 방법

```bash
# .env에 Discord Webhook URL 설정
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# 앱에서 /watchlist 페이지에서 알림 받을 대상 추가
```

---

## 9. 스케줄러 (자동화)

`scripts/scheduler.py` — APScheduler 기반.
**Railway Worker 서비스로 배포해야 자동 실행됨.**

| 시간 (KST) | 작업 | 빈도 |
|-----------|------|------|
| 매일 00:00 | 환율 업데이트 | 매일 |
| 매일 06:00 | 드롭/신제품 크롤 | 매일 |
| 매일 12:00 | 패션 뉴스 수집 | 매일 |
| 매일 18:00 | 전체 제품/가격 크롤 | 매일 |
| 매주 월 01:00 | 데이터 감사 + Discord 알림 | 주 1회 |

```bash
uv run python scripts/scheduler.py            # 실행
uv run python scripts/scheduler.py --dry-run  # 드라이런 (실제 실행 없이 확인)
```

**⚠️ 현재 상태**: Railway에 Worker 서비스 미설정 → 스케줄러 실행 안 됨.
모든 크롤/업데이트를 로컬에서 수동 실행 중.

---

## 10. 스크립트 전체 목록

**31개 스크립트 (`scripts/`)**

### 크롤링

| 스크립트 | 설명 |
|----------|------|
| `crawl_products.py` | 제품/가격 크롤 (`--limit`, `--channel-type`, `--channel-id`, `--no-alerts`) |
| `crawl_brands.py` | 브랜드 크롤 |
| `crawl_drops.py` | 드롭/신제품 크롤 |
| `crawl_news.py` | RSS 패션 뉴스 수집 |
| `update_exchange_rates.py` | 환율 업데이트 (open.er-api.com) |
| `scheduler.py` | APScheduler 자동화 (`--dry-run` 지원) |

### 시딩

| 스크립트 | 설명 |
|----------|------|
| `seed_channels.py` | 초기 채널 시딩 |
| `seed_brands_luxury.py` | 럭셔리 브랜드 추가 (`--dry-run / --apply`) |
| `seed_collabs.py` | 협업 정보 추가 |
| `seed_directors.py` | 디렉터 정보 추가 CSV 기반 (`--dry-run / --apply`) |
| `enrich_brands.py` | 브랜드 정보 강화 CSV 기반 (`--dry-run / --apply`) |

### 데이터 정제

| 스크립트 | 설명 |
|----------|------|
| `cleanup_route_products.py` | Route 배송보험 등 비패션 오인덱싱 제품 소프트 삭제 (`--dry-run`) ← Phase 22 CC-1 신규 |
| `fix_null_brand_id.py` | brand_id NULL 수정 (`--dry-run / --apply`) |
| `fix_brand_mece.py` | 브랜드 MECE 위반 처리 |
| `cleanup_mixed_brand_channel.py` | 혼합 브랜드·채널 정리 |
| `cleanup_fake_brands.py` | 가짜 브랜드 탐지 (`--execute`로 삭제) |
| `purge_fake_brands.py` | 가짜 브랜드 삭제 (`--dry-run / --apply`) |
| `remap_product_brands.py` | 제품 브랜드 리매핑 (`--dry-run / --apply`) |
| `backfill_brand_ids.py` | brand_id 백필 |
| `backfill_normalized_key.py` | normalized_key 백필 (`--apply / --force`) |
| `detect_platforms.py` | 채널 플랫폼 자동 감지 (`--apply`) |

### 분석 & 감사

| 스크립트 | 설명 |
|----------|------|
| `data_audit.py` | 데이터 품질 감사 리포트 |
| `data_quality_report.py` | 상세 데이터 품질 리포트 |
| `build_product_catalog.py` | ProductCatalog 빌드 (`--since` / `--since-last-crawl` 증분 옵션 지원) |
| `update_catalog_prices.py` | ProductCatalog 가격 업데이트 |
| `channel_probe.py` | 제품 0개 채널 플랫폼 진단 (`--apply`, `--output CSV`, `--all`) ← T-056 신규 |
| `classify_brands.py` | 브랜드 tier 분류 |
| `recalculate_hype.py` | hype_score 재계산 |

### 마이그레이션 & 인프라

| 스크립트 | 설명 |
|----------|------|
| `migrate_sqlite_to_pg.py` | SQLite → PostgreSQL 마이그레이션 |
| `sync_local_to_railway.py` | 로컬 DB → Railway 동기화 |
| `preprocess_channels.py` | 채널 전처리 |
| `update_channels.py` | 채널 정보 일괄 업데이트 |
| `agent_coord.py` | Codex 협업 과업 등록/관리 |

---

## 11. Alembic 마이그레이션 이력

**16개 버전** (최신 → 과거 순)

| 버전 ID | 설명 |
|---------|------|
| `e5f6a7b8c9d0` | `crawl_channel_logs.error_type` 컬럼 추가 (T-059) |
| `d4e5f6a7b8c9` | `price_history` PostgreSQL RANGE 파티셔닝 월별 (SQLite 무시) (T-057) |
| `c12883027b7b` | ChannelNote 테이블 추가 |
| `0f5706368502` | ProductCatalog 테이블 추가 |
| `66351b967c70` | CrawlRun, CrawlChannelLog 테이블 추가 |
| `8a58dd5a2358` | normalized_key / vendor 브랜치 병합 |
| `b9c0d1e2f3a4` | products.tags, channel_brands.cate_no 컬럼 추가 |
| `a1b2c3d4e5f6` | normalized_key, match_confidence, platform 컬럼 추가 |
| `a7c9d1e3f5b7` | products.vendor 컬럼 추가 |
| `e2a4b6c8d0f1` | products.archived_at 컬럼 추가 |
| `f1d2c3b4a5d6` | BrandDirector 테이블, instagram_url 컬럼 추가 |
| `9f9b0e1f2a3b` | products.gender, subcategory 컬럼 추가 |
| `7b6619f9d1ad` | 쿼리 최적화 인덱스 추가 |
| `25da360cc994` | Purchase, WatchListItem, Drop 테이블 추가 |
| `c3ad818a067f` | product_key, ExchangeRate 테이블 추가 |
| `66fc59a1f128` | tier, description_ko, BrandCollaboration, FashionNews 추가 |

---

## 12. 배포 구조 (Railway + Vercel)

### 현재 상태

```
Railway API 서비스 (배포됨):
  - 브랜치: main
  - 시작 명령: uv run alembic upgrade head && uv run uvicorn ...
  - DB: Railway PostgreSQL (~12,733개 제품)
  - 헬스체크: GET /health

Vercel 프론트엔드 (별도 설정 필요):
  - Root Directory: frontend
  - 환경변수: NEXT_PUBLIC_API_URL=https://<railway-url>.railway.app

Railway Worker 서비스 (미설정):
  - 시작 명령 필요: uv run python scripts/scheduler.py
  - 설정 안 됨 → 자동 크롤/환율업데이트/알림 없음
```

### 로컬 개발

```bash
make api          # 백엔드 http://localhost:8000
make web          # 프론트엔드 http://localhost:3000
make dev          # 원클릭 (API + Web 동시)

# Railway DB에 직접 연결
DATABASE_URL="postgresql+asyncpg://..." uv run python scripts/crawl_products.py
```

---

## 13. 현재 데이터 현황

### 로컬 SQLite `data/fashion.db` (2026-03-02 기준)

| 항목 | 수치 |
|------|------|
| **채널** | |
| 전체 채널 | 159개 |
| 제품 있는 채널 | 81개 |
| 제품 0개 채널 | 78개 (edit-shop 25 + brand-store 49 + 기타 4) |
| **브랜드** | |
| 전체 브랜드 | 2,570개 |
| 제품과 연결된 브랜드 | 1,420개 |
| 채널-브랜드 링크 | 3,245개 |
| **제품** | |
| 전체 제품 | 80,096개 |
| 활성 제품 (is_active=True) | **80,091개** (Route 배송보험 5개 소프트 삭제, CC-1) |
| 세일 제품 (is_sale=True) | 19,997개 (25%) |
| brand_id NULL 제품 | 18,962개 (23.6%) |
| **가격 이력** | |
| PriceHistory 레코드 | 81,892개 |
| **협업** | |
| BrandCollaboration | 34건 |
| **디렉터** | |
| BrandDirector | 125명 |
| **크롤 추적** | |
| CrawlRun | 0개 (로컬 미실행) |
| CrawlChannelLog | 0개 |
| **ProductCatalog** | **64,075개** (Phase 22 CC-3, build_product_catalog.py 실행) |
| **환율** | 12개 통화 |

### Railway PostgreSQL (운영 DB)

- 약 12,733개 제품 (로컬 대비 15% 수준 — 크롤 덜 됨)
- 동기화: `scripts/sync_local_to_railway.py` 또는 `scripts/migrate_sqlite_to_pg.py`

---

## 14. 알려진 문제점 및 한계

### 데이터 품질

| 문제 | 심각도 | 원인 | 상태 |
|------|--------|------|------|
| brand_id NULL 23.6% | 높음 | brand-store 외 채널 자동 매핑 어려움 | 부분 해결 (T-046, 991개 리매핑) |
| Route 배송보험 제품 오인덱싱 | 높음 | Shopify `/products.json`에 Route 앱 제품이 패션 제품처럼 노출 | **✅ 완료** — T-054 denylist 구현 + 기존 5개 CC-1에서 소프트 삭제 |
| brand-store 49개 미크롤 | 중간 | 크롤 미실행 또는 비표준 플랫폼 | T-056 channel_probe.py로 진단 가능 |
| edit-shop 크롤 25개 미완 | 높음 | Cafe24 커스텀 전략 미등록 | 진행 중 |
| 환율 자동 업데이트 없음 | 중간 | Railway Worker 미설정 | 미해결 |
| ProductCatalog 비어있음 | 중간 | build_product_catalog.py 미실행 | **✅ 완료** — Phase 22 CC-3에서 64,075개 빌드 완료 |

### 구조적 한계

| 한계 | 설명 |
|------|------|
| 사용자 계정 없음 | 구매이력/관심목록이 API 직접 호출 방식. 다기기 동기화 불가 |
| 권한 관리 없음 | 관리자 Bearer 토큰 하나뿐. 사용자별 데이터 분리 불가 |
| 실시간 알림 없음 | Discord 알림은 크롤 시점에만 발생. 브라우저 푸시 없음 |
| 비표준 플랫폼 지원 없음 | stores.jp / buyshop.jp / theshop.jp 등 크롤 불가 |
| product_key 정확도 | vendor 필드 부정확 시 잘못된 product_key 생성 → normalized_key로 보완 중 |
| Railway Worker 미설정 | 자동 크롤/환율/알림 없음 → 수동 실행 |

### 완료된 과업 (Phase 21~22)

| Task ID | 제목 | 상태 |
|---------|------|------|
| T-20260301-054 | PRODUCT_DENYLIST_01: Route 배송보험 등 비패션 제품 필터링 | ✅ Codex 구현 완료 |
| T-20260301-055 | CHANNEL_TRAFFIC_LIGHT_01: 채널 크롤 건강도 트래픽 라이트 | ✅ Codex 구현 완료 |
| CC-1 | Route 오인덱싱 5개 소프트 삭제 (`cleanup_route_products.py`) | ✅ Claude Code 완료 |
| CC-2 | 플랫폼 감지 실행 (`detect_platforms.py --apply`) | ✅ 완료 (0 추가 감지) |
| CC-3 | ProductCatalog 64,075개 빌드 (`build_product_catalog.py`) | ✅ 완료 |
| CC-4 | T-054/T-055 코드리뷰 검증 | ✅ 완료 |
| T-20260302-056 | CHANNEL_PROBE_01: 제품 0개 채널 플랫폼 진단 스크립트 | ✅ Codex 구현 완료 |
| T-20260302-057 | PRICE_HISTORY_PARTITION_01: PostgreSQL price_history 월별 파티셔닝 | ✅ Codex 구현 완료 |
| T-20260302-058 | PRODUCT_CATALOG_PIPELINE_01: ProductCatalog 자동 증분 빌드 파이프라인 | ✅ Codex 구현 완료 |
| T-20260302-059 | CRAWL_ERROR_TYPE_01: CrawlChannelLog error_type 분류 필드 추가 | ✅ Codex 구현 완료 |

GPT Pro 채널 리서치: `docs/channel_research_report_2026-03-01.md` 참조
DB 구조 심층 리서치: `docs/deep-research-report.md` 참조

---

## 15. 설정 및 환경변수

### .env 파일 (로컬)

```bash
# DB
DATABASE_URL=sqlite+aiosqlite:///./data/fashion.db
RAILWAY_DATABASE_URL=postgresql+asyncpg://...   # Railway (수동 지정 시)

# 크롤러
CRAWLER_DELAY_SECONDS=2.0
CRAWLER_MAX_RETRIES=3
CRAWLER_TIMEOUT_SECONDS=30
CRAWLER_HEADLESS=true
TZ=Asia/Seoul

# API
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# 관리자
ADMIN_BEARER_TOKEN=<비밀값>
CORS_ALLOWED_ORIGINS=http://localhost:3000

# 알림
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
ALERT_PRICE_DROP_THRESHOLD=0.10   # 10% 이상 하락 시 알림
```

### Railway 환경변수 (운영)

```bash
DATABASE_URL=<Railway PostgreSQL URL>
ALLOWED_ORIGINS=https://<vercel-url>.vercel.app,http://localhost:3000
ADMIN_BEARER_TOKEN=<비밀값>
DISCORD_WEBHOOK_URL=<Discord URL>
```

### Vercel 환경변수 (프론트엔드)

```bash
NEXT_PUBLIC_API_URL=https://<railway-url>.railway.app
```

---

## 16. Makefile 주요 커맨드

```bash
make setup              # uv sync + playwright install
make api                # 백엔드 API 서버 (http://localhost:8000)
make web                # 프론트엔드 개발 서버 (http://localhost:3000)
make dev                # 원클릭 (API + Web 동시)

make crawl              # 전체 제품 크롤 (Discord 알림 없이)
make crawl-cafe24       # Cafe24 편집샵만 크롤
make update-rates       # 환율 업데이트

make scheduler          # APScheduler 실행
make scheduler-dry      # 스케줄러 드라이런

make data-audit         # 데이터 품질 감사
make audit-railway      # Railway DB 감사

make fix-null-brands-apply    # brand_id NULL 수정
make backfill-normalized-key-apply  # normalized_key 백필
make detect-platforms-apply   # 플랫폼 자동 감지

make seed-directors-apply     # 디렉터 시딩
make seed-brands-luxury-apply # 럭셔리 브랜드 시딩
make purge-fake-brands-apply  # 가짜 브랜드 삭제
```

---

## 요약: 현재 가장 중요한 과제

1. **Railway Worker 설정** → 스케줄러가 자동으로 돌아야 크롤/환율/알림 작동
2. **채널 플랫폼 진단** → `channel_probe.py`로 78개 0-product 채널 상태 파악 및 `--apply`
3. **Alembic 마이그레이션 적용** → `d4e5f6a7b8c9` (PG 파티션), `e5f6a7b8c9d0` (error_type) Railway에 적용
4. **edit-shop 미크롤 25개** → Cafe24 커스텀 전략 추가 필요
5. **brand_id NULL 23.6%** → 자동 매핑 강화 또는 수동 연결 필요
6. **사용자 계정 시스템** → 구매이력/관심목록의 실용성을 위해 필요

---

*최종 업데이트: 2026-03-02 (Phase 22 완료 기준)*
