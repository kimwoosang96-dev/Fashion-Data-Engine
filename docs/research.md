# Fashion Data Engine — 프로젝트 리서치

> 작성일: 2026-03-01
> 목적: 코드베이스 전체 파악. 이 문서를 기반으로 plan.md를 작성한다.

---

## 목차

1. [프로젝트 한 줄 요약](#1-프로젝트-한-줄-요약)
2. [전체 구조](#2-전체-구조)
3. [데이터베이스 모델](#3-데이터베이스-모델)
4. [핵심 개념: product_key](#4-핵심-개념-product_key)
5. [크롤링 시스템](#5-크롤링-시스템)
6. [API 엔드포인트 전체 목록](#6-api-엔드포인트-전체-목록)
7. [프론트엔드 페이지](#7-프론트엔드-페이지)
8. [알림 시스템 (Discord)](#8-알림-시스템-discord)
9. [스케줄러 (자동화)](#9-스케줄러-자동화)
10. [배포 구조 (Railway + Vercel)](#10-배포-구조-railway--vercel)
11. [현재 데이터 현황](#11-현재-데이터-현황)
12. [알려진 문제점 및 한계](#12-알려진-문제점-및-한계)
13. [설정 및 환경변수](#13-설정-및-환경변수)

---

## 1. 프로젝트 한 줄 요약

**여러 패션 판매채널(편집숍, 브랜드 공식몰 등)의 제품 가격을 수집하여, 동일 제품의 채널별 가격을 비교하고 구매 최적 타이밍을 분석하는 플랫폼.**

---

## 2. 전체 구조

```
fashion-data-engine/
├── src/fashion_engine/       ← 백엔드 (Python, FastAPI)
│   ├── api/                  ← HTTP 엔드포인트 (라우터)
│   ├── models/               ← DB 테이블 정의 (SQLAlchemy)
│   ├── services/             ← 비즈니스 로직 (쿼리, 계산)
│   ├── crawler/              ← 데이터 수집 (Shopify API, Playwright)
│   └── config.py             ← 환경변수 설정
│
├── frontend/src/             ← 프론트엔드 (Next.js, TypeScript)
│   ├── app/                  ← 페이지 (18개)
│   ├── components/           ← 공통 컴포넌트
│   └── lib/                  ← API 호출 함수, 타입 정의
│
├── scripts/                  ← 실행 스크립트 (크롤, 감사, 시드 등)
├── alembic/                  ← DB 마이그레이션 버전 관리
├── data/fashion.db           ← 로컬 SQLite DB
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
| 크롤링 | httpx (Shopify REST), Playwright (브라우저 자동화) |
| 프론트엔드 | Next.js 14, TypeScript, Tailwind CSS, Shadcn/UI |
| 배포 | Railway (백엔드 API), Vercel (프론트엔드) |
| 알림 | Discord Webhook |
| 스케줄링 | APScheduler (Python) |

---

## 3. 데이터베이스 모델

### 3.1 Channel (판매채널)

쿠팡, PATTA Korea, New Balance 공식몰처럼 제품을 파는 온라인 쇼핑몰.

```
channel_type 분류:
  brand-store       : 단일 브랜드 공식몰 (예: New Balance KR, ALIVEFORM)
  edit-shop         : 여러 브랜드를 취급하는 편집숍 (예: 무신사, KASINA)
  department-store  : 백화점 (SSF, W컨셉 등)
  marketplace       : 마켓플레이스 (오늘의집 등)
  non-fashion       : 비패션 (추적 제외)
  secondhand        : 중고 마켓 (번개장터 등)
```

**현황 (2026-03-01 Railway)**: 159개 채널, 이 중 35개만 크롤 완료.

---

### 3.2 Brand (브랜드)

```
tier 분류:
  high-end  : 루이비통, 에르메스 등
  premium   : New Balance, Stone Island 등
  street    : Supreme, Palace 등
  sports    : 나이키, 아디다스 등
  spa       : 자라, H&M 등
```

**현황**: 2,561개 브랜드 등록. 이 중 상당수가 "유령 브랜드" (channel_brands 링크 0개).

---

### 3.3 Product (제품)

크롤링으로 수집된 실제 판매 제품.

```
주요 컬럼:
  channel_id    : 어느 채널에서 수집됐는지
  brand_id      : 어느 브랜드인지 (NULL 가능 — 현재 41% NULL)
  product_key   : "brand-slug:handle" — 교차채널 동일 제품 식별자
  vendor        : Shopify의 vendor 필드 (브랜드명 원본 텍스트)
  gender        : men / women / unisex / kids
  subcategory   : shoes / outer / top / bottom / ...
  is_active     : 현재 판매 가능 여부
  is_sale       : 세일 중 여부
  archived_at   : 품절 전환된 시간 (NULL이면 현재 판매 중)
```

**현황**: 12,733개 (Railway). 로컬 SQLite에는 약 80,096개.

---

### 3.4 PriceHistory (가격 이력)

크롤할 때마다 새로운 행을 추가하여 가격 변동을 시계열로 추적.

```
product_id    : 어느 제품인지
price         : 현재가 (KRW 환산)
original_price: 정가 (세일 시 더 높음)
discount_rate : 할인율 (%) = (1 - 현재가/정가) × 100
crawled_at    : 이 가격을 수집한 시간
```

---

### 3.5 ExchangeRate (환율)

```
from_currency → to_currency(KRW) → rate
예: USD → KRW → 1440.9
    EUR → KRW → 1700.7
    JPY → KRW → 9.2
```

open.er-api.com에서 일 1회 자동 업데이트. 현재 12개 통화 지원.

---

### 3.6 BrandCollaboration (협업)

두 브랜드 간 콜라보레이션 기록.

```
brand_a_id, brand_b_id : 협업한 두 브랜드
collab_name            : 예) "Adidas x Wales Bonner SS26"
collab_category        : footwear / apparel / accessories / lifestyle
release_year           : 발매 연도
hype_score             : 0-100 (취급 채널 수 × 10, 최대 100)
```

**현황**: 35개 협업 등록.

---

### 3.7 BrandDirector (크리에이티브 디렉터)

```
brand_id    : 브랜드
name        : 디렉터명
role        : 역할 (기본값: "Creative Director")
start_year  : 재직 시작 연도
end_year    : 퇴임 연도 (NULL = 현직)
```

**현황**: 109명 등록.

---

### 3.8 Purchase (구매 이력)

사용자가 직접 입력하는 구매 기록. 구매 성공도(S/A/B/C/D) 계산에 사용.

```
product_key       : "brand-slug:handle"
paid_price_krw    : 실제 지불 금액
original_price_krw: 정가
purchased_at      : 구매 일시
```

---

### 3.9 WatchListItem (관심 목록)

Discord 알림을 받을 대상을 지정.

```
watch_type   : "brand" | "channel" | "product_key"
watch_value  : slug, URL, 또는 product_key

⚠️ 중요: WatchList가 비어있으면 모든 알림이 차단됨.
   즉, 알림을 받으려면 반드시 항목을 추가해야 함.
```

---

### 3.10 Drop (발매/드롭 정보)

크롤러가 감지한 신제품 또는 예정 발매 정보.

```
status: "upcoming" (예정) | "released" (발매됨) | "sold_out" (품절)
```

---

### 3.11 FashionNews (뉴스)

RSS 피드에서 수집한 패션 뉴스.

```
source: "instagram" | "website" | "press" | "youtube"
entity_type: "brand" | "channel"
entity_id: 관련 브랜드/채널 ID
```

---

## 4. 핵심 개념: product_key

**product_key = "{brand-slug}:{product-handle}"**

예시:
- `new-balance:2002r`
- `nike:air-force-1-low`
- `032c:selfie-sweater-4`

**왜 필요한가?**

동일한 제품이 여러 채널에서 판매될 때, 각 채널의 DB 행은 서로 다른 `product.id`를 가진다. product_key가 있어야 "이건 같은 제품"이라는 걸 알 수 있다.

```
PATTA Korea에서 판매하는 New Balance 2002R: product.id = 74
무신사에서 판매하는 New Balance 2002R:     product.id = 2341
→ 둘 다 product_key = "new-balance:2002r" → 가격 비교 가능
```

**product_key 생성 방법:**
1. Shopify `/products.json` 응답에서 `handle` 필드 추출
2. `vendor` 필드를 slug로 변환 → brand-slug
3. `"{brand-slug}:{handle}"` 조합

**한계:**
- Shopify 기반이 아닌 채널은 product_key가 NULL
- vendor명이 정확하지 않으면 잘못된 brand-slug 생성

---

## 5. 크롤링 시스템

### 5.1 제품 크롤러 (product_crawler.py)

**대상**: Shopify 기반 채널의 `/products.json` API

```
크롤 흐름:
1. channels 테이블에서 active 채널 목록 조회
2. 각 채널에 대해:
   a. GET {channel_url}/products.json?limit=250&page=N (최대 16페이지)
   b. 통화 추론 (URL 서브도메인 기반)
      kr. → KRW, jp. → JPY, eu. → EUR, uk. → GBP, us. → USD
   c. product_key 생성 ({brand_slug}:{handle})
   d. DB upsert (기존 제품이면 가격 업데이트, 신규면 INSERT)
   e. PriceHistory 기록 (항상 새 행)
3. 변화 감지 시 Discord 알림:
   🚀 신규 product_key
   🔥 is_sale False → True 전환
   📉 가격 10%+ 하락
```

**실행 방법:**
```bash
make crawl                    # 전체 크롤 (알림 없음)
make crawl --channel-type brand-store  # brand-store만
uv run python scripts/crawl_products.py --limit 3  # 테스트 (3채널)
```

---

### 5.2 브랜드 크롤러 (brand_crawler.py)

**대상**: 각 채널의 브랜드 목록 페이지 (Playwright 브라우저 자동화)

채널마다 HTML 구조가 달라서, CHANNEL_STRATEGIES 딕셔너리에 채널별 CSS 선택자를 직접 등록해야 한다.

```
예) 8division.com: "ul.sub-menu.sub-menu-brands > li > a"
    musinsa.com:   ".brand-item"
    cafe24 기반:   "a[href*='cate_no=']"
```

**Shopify 채널은 자동 처리 가능**: `/products.json`의 `vendor` 필드에서 브랜드명 자동 추출.

---

### 5.3 드롭 크롤러 (drop_crawler.py)

신제품/예정 발매를 감지.

```
방법 1: GET {channel}/products.json?sort_by=created-at-desc&limit=20
        → DB에 없는 product_key = 신제품

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

### 5.5 현재 크롤 가능한 채널

| 채널 타입 | 전체 | 크롤 완료 | 미크롤 |
|----------|------|----------|--------|
| brand-store | 75 | 35 | **40** |
| edit-shop | 80 | 0 | **80** |
| department-store | 2 | 0 | 2 |
| marketplace | 1 | 0 | 1 |

**edit-shop 80개가 크롤 0인 이유**: 편집숍은 채널마다 HTML 구조가 달라 Shopify 자동 크롤이 안 되는 경우가 많음. 각 채널별 커스텀 전략 필요.

---

## 6. API 엔드포인트 전체 목록

### 공개 API (인증 불필요)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 서버 헬스체크 |
| GET | `/brands/` | 브랜드 목록 (tier 필터) |
| GET | `/brands/landscape` | 브랜드 그래프 데이터 |
| GET | `/brands/highlights` | 브랜드별 신상품 현황 |
| GET | `/brands/search` | 브랜드 검색 |
| GET | `/brands/{slug}` | 브랜드 상세 |
| GET | `/brands/{slug}/channels` | 브랜드 취급 채널 |
| GET | `/brands/{slug}/products` | 브랜드 제품 |
| GET | `/brands/{slug}/collabs` | 브랜드 협업 |
| GET | `/brands/{slug}/directors` | 브랜드 디렉터 |
| GET | `/channels/` | 채널 목록 |
| GET | `/channels/highlights` | 채널별 세일/신상품 현황 |
| GET | `/channels/landscape` | 채널 지형 데이터 |
| GET | `/channels/{id}` | 채널 상세 |
| GET | `/channels/{id}/brands` | 채널 취급 브랜드 |
| GET | `/products/sales` | 세일 제품 (필터: brand, tier, gender, category, 가격범위) |
| GET | `/products/search` | 제품 검색 |
| GET | `/products/sales-highlights` | 세일 하이라이트 (product_key 기준 최저가) |
| GET | `/products/sales-count` | 세일 제품 총 개수 |
| GET | `/products/related-searches` | 연관 검색어 |
| **GET** | **`/products/compare/{product_key}`** | **채널별 가격 비교 (핵심!)** |
| GET | `/products/price-history/{product_key}` | 30일 가격 이력 |
| GET | `/products/archive` | 품절 제품 목록 |
| GET | `/products/multi-channel` | 2개+ 채널 판매 제품 (가격 스프레드) |
| GET | `/collabs/` | 협업 목록 |
| GET | `/collabs/hype-by-category` | 카테고리별 하입 점수 |
| GET | `/purchases/` | 구매 이력 |
| GET | `/purchases/stats` | 구매 통계 |
| GET | `/purchases/{id}/score` | 구매 성공도 (S/A/B/C/D) |
| POST | `/purchases/` | 구매 기록 추가 |
| DELETE | `/purchases/{id}` | 구매 기록 삭제 |
| GET | `/watchlist/` | 관심 목록 |
| POST | `/watchlist/` | 관심 항목 추가 |
| DELETE | `/watchlist/{id}` | 관심 항목 삭제 |
| GET | `/drops/upcoming` | 예정 발매 |
| GET | `/drops/` | 드롭 목록 |
| GET | `/news/` | 패션 뉴스 |
| GET | `/directors/` | 디렉터 목록 |
| GET | `/directors/by-brand` | 브랜드별 디렉터 |

### 관리자 API (Bearer Token 필요)

```
Authorization: Bearer {ADMIN_BEARER_TOKEN}
```

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/admin/stats` | DB 전체 통계 |
| GET | `/admin/channels-health` | 채널 건강도 |
| GET | `/admin/crawl-status` | 채널별 마지막 크롤 시간 |
| POST | `/admin/crawl-trigger` | 크롤 작업 실행 (job=products/brands/drops) |
| GET | `/admin/brand-channel-audit` | 브랜드-채널 혼재 감사 |
| GET/POST | `/admin/collabs` | 협업 관리 |
| DELETE | `/admin/collabs/{id}` | 협업 삭제 |
| GET/POST | `/admin/directors` | 디렉터 관리 |
| DELETE | `/admin/directors/{id}` | 디렉터 삭제 |
| PATCH | `/admin/brands/{id}/instagram` | 브랜드 인스타그램 URL |
| PATCH | `/admin/channels/{id}/instagram` | 채널 인스타그램 URL |

---

## 7. 프론트엔드 페이지

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
- 뒤로가기 버튼 (브라우저 히스토리 기반)

**`/sales` (세일 제품)**
- 성별/카테고리/가격범위 필터
- 무한스크롤 (더보기 버튼 방식)
- 각 제품 카드 클릭 → `/compare/{product_key}`

**`/compete` (경쟁 제품)**
- 2개+ 채널에서 팔리는 제품 목록
- 채널 수 / 가격 스프레드로 정렬
- 가격 스프레드 = 최고가 - 최저가

**`/purchases` (구매 이력)**
- 내가 구매한 제품 기록
- 성공도 점수 (S~D): 과거 가격 데이터 백분위 기반
- "역대 상위 5%" 같은 배지 표시

**`/watchlist` (관심 목록)**
- 브랜드/채널/제품_key 단위로 알림 대상 지정
- ⚠️ 비어있으면 Discord 알림이 전혀 오지 않음

**`/admin` (운영 관리)**
- Bearer 토큰 입력 후 접근
- 채널별 크롤 상태 확인 + 단일 채널 수동 크롤
- 디렉터/협업 추가/삭제
- 브랜드-채널 혼재 감사 실행

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

`scripts/scheduler.py` — APScheduler 기반. **Railway Worker 서비스로 배포해야 자동 실행.**

| 시간 (KST) | 작업 | 빈도 |
|-----------|------|------|
| 매일 03:00 | 전체 제품 크롤 | 매일 |
| 매일 07:00 | 환율 업데이트 | 매일 |
| 매일 07:10 | 드롭 감지 | 매일 |
| 매일 08:00 | 뉴스 수집 | 매일 |
| 일요일 09:00 | 데이터 감사 + Discord 알림 | 주 1회 |

**⚠️ 현재 상태**: Railway에 Worker 서비스가 없어서 스케줄러가 실행되지 않음.
모든 크롤/업데이트를 로컬에서 수동 실행하고 있음.

---

## 10. 배포 구조 (Railway + Vercel)

### 현재 상태

```
Railway API 서비스 (배포됨):
  - 브랜치: main
  - 시작 명령: uv run alembic upgrade head && uv run uvicorn ...
  - DB: Railway PostgreSQL (12,733개 제품)
  - 헬스체크: GET /health

Vercel 프론트엔드 (미확인, 별도 설정 필요):
  - Root Directory: frontend
  - 환경변수: NEXT_PUBLIC_API_URL=https://<railway-url>.railway.app

Railway Worker 서비스 (미설정):
  - 시작 명령이 되어야 할 것: uv run python scripts/scheduler.py
  - 설정 안 됨 → 자동 크롤/환율업데이트 없음
```

### 로컬 개발

```bash
# 백엔드
make api          # http://localhost:8000
make web          # http://localhost:3000

# Railway DB에 연결해서 실행
DATABASE_URL="postgresql+asyncpg://..." uv run python scripts/...
```

---

## 11. 현재 데이터 현황

### Railway PostgreSQL (운영 DB, 2026-03-01 기준)

| 항목 | 수치 |
|------|------|
| 총 제품 | 12,733개 |
| brand_id NULL 제품 | ~41% (약 5,200개) |
| 크롤된 채널 | 35/159 (22%) |
| 미크롤 채널 | 124개 |
| 활성 제품 | ~59% |
| 품절/비활성 | ~41% |
| 브랜드 수 | 2,561개 |
| 유령 브랜드 (링크 없음) | ~2,501개 |
| 디렉터 | 109명 |
| 협업 | 35건 |
| 환율 마지막 업데이트 | 2026-02-28 |

### 로컬 SQLite (개발 DB)

- 약 80,096개 제품 (Railway보다 6배 이상)
- 로컬에서 훨씬 더 많이 크롤됨

---

## 12. 알려진 문제점 및 한계

### 데이터 품질

| 문제 | 심각도 | 원인 | 상태 |
|------|--------|------|------|
| brand_id NULL 41% | 높음 | brand-store 외 채널은 자동 매핑 어려움 | 부분 해결 (T-046, 991개 리매핑) |
| 유령 브랜드 2,501개 | 중간 | 크롤 브랜드가 채널과 미연결 | 미해결 |
| edit-shop 0개 크롤 | 높음 | 채널별 커스텀 전략 필요 | 미해결 |
| brand-store 40개 미크롤 | 중간 | 크롤 미실행 | 진행 중 |
| 환율 자동 업데이트 없음 | 중간 | Railway Worker 미설정 | 미해결 |

### 구조적 한계

| 한계 | 설명 |
|------|------|
| 사용자 계정 없음 | 구매이력/관심목록이 기기에 종속됨 (브라우저 localStorage 없이 API 직접 호출) |
| 권한 관리 없음 | 관리자 Bearer 토큰 하나로만 구분. 사용자별 데이터 분리 불가 |
| 실시간 알림 없음 | Discord 알림은 크롤 시점에만 발생. 브라우저 푸시 없음 |
| Shopify만 지원 | edit-shop 대부분이 Shopify 미사용 → 크롤 불가 |
| product_key 정확도 | vendor 필드가 부정확하면 잘못된 product_key 생성 |

---

## 13. 설정 및 환경변수

### .env 파일 (로컬)

```bash
# DB
DATABASE_URL=sqlite+aiosqlite:///./data/fashion.db  # 로컬
RAILWAY_DATABASE_URL=postgresql+asyncpg://...        # Railway (수동 지정 시)

# 크롤러
CRAWLER_DELAY_SECONDS=2.0
CRAWLER_MAX_RETRIES=3
CRAWLER_TIMEOUT_SECONDS=30

# API
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# 관리자
ADMIN_BEARER_TOKEN=<비밀값>

# 알림
DISCORD_WEBHOOK_URL=https://discordapp.com/api/webhooks/...
ALERT_PRICE_DROP_THRESHOLD=0.10  # 10% 이상 하락 시 알림
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

## 요약: 현재 가장 중요한 과제

1. **Railway Worker 설정** → 스케줄러가 자동으로 돌아야 크롤/환율/알림이 작동
2. **edit-shop 크롤** → 80개 채널, 0개 제품. 데이터 커버리지의 핵심
3. **사용자 계정 시스템** → 구매이력/관심목록의 실용성을 위해 필요
4. **brand_id NULL 해소** → 41%로 여전히 높음. 브랜드 연관 기능 품질 저하

---

*최종 업데이트: 2026-03-01*
