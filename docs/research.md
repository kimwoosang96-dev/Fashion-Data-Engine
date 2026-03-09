# Fashion Data Engine — 프로젝트 리서치

> 작성일: 2026-03-01 | 최종 업데이트: 2026-03-09 (아카이빙 기준)
> ⚠️ **이 프로젝트는 2026-03-09에 아카이빙되었습니다.** → [ARCHIVE.md](./ARCHIVE.md) 참조

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
13. [최종 데이터 현황](#13-최종-데이터-현황)
14. [알려진 문제점 및 한계](#14-알려진-문제점-및-한계)
15. [설정 및 환경변수](#15-설정-및-환경변수)

---

## 1. 프로젝트 한 줄 요약

**여러 패션 판매채널(편집숍, 브랜드 공식몰 등)의 제품 가격을 수집하여, 동일 제품의 채널별 가격을 비교하고 구매 최적 타이밍을 분석하는 플랫폼.**

스트릿웨어에서 시작해 하이엔드·디자이너·스포츠·아웃도어 브랜드까지 확장 예정이었으나, 인프라 복잡도 문제로 Phase 8 완료 후 아카이빙.

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
├── scripts/                  ← 실행 스크립트 31개
├── alembic/                  ← DB 마이그레이션 (16개 버전)
├── agents/                   ← Codex 협업 과업지시
├── docs/                     ← 리서치 및 기획 문서
├── data/fashion.db           ← 로컬 SQLite DB
└── .env                      ← 환경변수 (Git 제외)
```

### 기술 스택

| 레이어 | 기술 |
|--------|------|
| 백엔드 | Python 3.12, FastAPI, SQLAlchemy 2.0 (async) |
| DB | SQLite (로컬) / PostgreSQL (Railway 운영) |
| DB 마이그레이션 | Alembic |
| 크롤링 | httpx (Shopify REST), BeautifulSoup4 (HTML) |
| 프론트엔드 | Next.js 14, TypeScript, Tailwind CSS, Shadcn/UI |
| 배포 | Railway (백엔드 API + Worker), Vercel (프론트엔드) |
| 알림 | Discord Webhook |
| 스케줄링 | APScheduler (Python) |
| 에이전트 협업 | Claude Code (PM/인터랙티브) + OpenAI Codex (벌크 구현) |

---

## 3. 데이터베이스 모델

**18개 테이블** (alembic_version 제외)

### 3.1 Channel (판매채널)

```
주요 컬럼:
  id, name, url, original_url
  channel_type : brand-store | edit-shop | department-store | marketplace | secondhand-marketplace
  platform     : shopify | cafe24 | etc (자동 감지)
  country      : KR / JP / US / UK / SE / ES / IT / HK 등
  is_active    : 크롤 대상 여부
```

**최종 현황**: 활성 ~137개 (접근 불가 7개 + 저우선 22개 비활성화)

---

### 3.2 Brand (브랜드)

```
tier 분류:
  high-end  : 루이비통, 에르메스 등
  premium   : New Balance, Stone Island 등
  street    : Supreme, Palace 등
  sports    : 나이키, 아디다스 등
  designer  : 르메르, 마르지엘라 등
  outdoor   : Arc'teryx, Patagonia 등
  spa       : 자라, H&M 등

주요 컬럼:
  id, name, slug, name_ko, origin_country
  description, description_ko, official_url, instagram_url
  tier
```

**최종 현황**: 2,500+개 브랜드 (brand_id backfill 완료, NULL 24% → 1.3%)

---

### 3.3 Product (제품)

```
주요 컬럼:
  channel_id, brand_id, category_id
  name, vendor, product_key, normalized_key, match_confidence
  gender     : men / women / unisex / kids
  subcategory: shoes / outer / top / bottom / bag / cap / accessory
  sku, url, image_url, tags, description
  is_active, is_new, is_sale, archived_at
```

**최종 현황**: 80,000+개 (Railway PostgreSQL 기준)

---

### 3.4 PriceHistory (가격 이력)

```
product_id, price, original_price, currency
is_sale, discount_rate, crawled_at
```

**최종 현황**: 80,000+개 레코드 (T-101에서 JPY 오염 레코드 43,314건 삭제 후)

---

### 3.5 ExchangeRate (환율)

```
from_currency → to_currency(KRW) → rate
```

12개 통화 지원. open.er-api.com에서 일 1회 자동 업데이트.

**주의**: T-101에서 JPY 이중부패 버그 발견 및 수정 (JPY=88.6 → 9.41).
`_validate_rates()` 및 5× 이상값 방어 로직 추가.

---

### 3.6 기타 모델

| 모델 | 설명 | 현황 |
|------|------|------|
| ChannelBrand | 채널-브랜드 링크 | 3,245개 |
| Category | 카테고리 계층 | - |
| BrandCollaboration | 협업 정보 | 34건 |
| BrandDirector | 크리에이티브 디렉터 | 125명 |
| FashionNews | RSS 뉴스 수집 | - |
| Purchase | 구매 이력 (사용자 입력) | - |
| WatchListItem | Discord 알림 대상 | - |
| Drop | 발매/드롭 정보 | - |
| CrawlRun | 크롤 실행 단위 | CrawlRun #35 (최신, 2026-03-07) |
| CrawlChannelLog | 채널별 크롤 결과 | - |
| ProductCatalog | normalized_key 기준 집계 | 64,075개 |
| ChannelNote | 채널 운영 메모 | - |
| IntelEvent | Fashion Intel 이벤트 | 591건 (news 47 + collabs 34 + sales_spike 510) |
| IntelEventSource | 이벤트 소스 | - |
| IntelIngestRun | Intel 수집 실행 | - |

---

## 4. 핵심 개념: product_key / normalized_key

### product_key (1세대)

`product_key = "{brand-slug}:{product-handle}"`

Shopify `/products.json`의 `vendor`와 `handle` 필드 조합.
Shopify 기반이 아닌 채널은 NULL.

### normalized_key (2세대)

product_key보다 정교한 교차채널 매칭 키.
- vendor명 부정확 문제 보완 (`match_confidence` 0.0~1.0)
- `backfill_normalized_key.py`로 기존 제품에 소급 적용

```
PATTA Korea의 New Balance 2002R: product.id = 74
무신사의 New Balance 2002R:       product.id = 2341
→ 둘 다 normalized_key = "new-balance:new-balance-2002r" → 가격 비교 가능
```

---

## 5. 크롤링 시스템

### 5.1 제품 크롤러 (product_crawler.py)

**지원 플랫폼**: Shopify, Cafe24

```
크롤 흐름:
1. active 채널 목록 조회
2. asyncio.Semaphore(5)로 최대 5채널 병렬 크롤
3. 각 채널:
   a. [Shopify] GET {url}/products.json?limit=250&page=N
      [Cafe24 ] HTML 파싱 /category/{cate_no}
   b. 통화 자동 감지 (URL 서브도메인 기반)
   c. 비패션 제품 필터링 (vendor/type/title denylist)
   d. normalized_key 생성
   e. DB upsert + PriceHistory 기록
   f. Discord 알림 (신규/세일/10%+ 하락)
4. CrawlRun/CrawlChannelLog에 결과 기록
```

**T-101 핵심 버그 수정**: `Accept-Language` 헤더가 Shopify Markets KRW 현지화를 트리거
→ JP 스토어 가격 9.5× 과다 책정. 헤더 제거로 해결.

### 5.2 Intel 수집 시스템 (Phase 26~27)

```
intel_events 테이블:
  event_type: news | collab | sale_start | sold_out | restock | sales_spike | drops

파생 이벤트 자동 감지:
  sale_start   : discount_rate severity 기반
  sold_out     : archived_at 전환 시
  restock      : archived_at NULL 복귀 시
  sales_spike  : 7일 baseline 대비 급등
  drops        : Shopify coming-soon 태그 자동 감지

뉴스 수집 피드 (8개):
  영문: hypebeast.com, highsnobiety.com, sneakernews.com, complex.com
  한국: hypebeast.kr, vogue.co.kr, wkorea.com, boon.so

Discord 실시간 알림: critical/high severity만 발송
```

---

## 6. API 엔드포인트 전체 목록

### 공개 API

| 경로 | 설명 |
|------|------|
| `GET /channels/`, `/channels/{id}`, `/channels/landscape` | 채널 |
| `GET /brands/`, `/brands/{slug}`, `/brands/search` | 브랜드 |
| `GET /products/sales`, `/products/search`, `/products/sales-highlights` | 제품 |
| **`GET /products/compare/{product_key}`** | **전 채널 가격 비교 ← 핵심** |
| `GET /products/price-history/{product_key}` | 30일 가격 이력 |
| `GET /catalog/`, `/catalog/{normalized_key}` | 카탈로그 |
| `GET /collabs/`, `/purchases/`, `/watchlist/` | 기타 |
| `GET /drops/upcoming`, `/news/`, `/directors/` | 기타 |
| `GET /intel/events`, `/intel/timeline`, `/intel/highlights` | Intel Hub |
| `GET /health` | 헬스체크 |

### 관리자 API (`Authorization: Bearer {token}`)

| 경로 | 설명 |
|------|------|
| `GET /admin/stats`, `/admin/crawl-runs` | DB/크롤 현황 |
| `POST /admin/crawl-trigger` | 수동 크롤 실행 |
| `GET /admin/channel-signals` | 채널 트래픽 라이트 |
| `GET /admin/intel-status` | Intel Hub 현황 |
| `GET /admin/catalog-stats` | ProductCatalog 현황 |

---

## 7. 프론트엔드 페이지

**17개 페이지**

```
📊 대시보드        /
🔥 세일 제품       /sales
⚔️  경쟁           /compete
🏪 판매채널        /channels
🏷️ 브랜드          /brands
🧠 디렉터          /directors
📰 뉴스            /news
🤝 협업            /collabs
❤️ 관심목록        /watchlist
🛍️ 구매이력        /purchases
🚀 드롭            /drops
🗺️ 세계지도        /map
📡 Intel           /intel
⚙️ 운영관리        /admin
📊 랭킹            /ranking
💰 가격 인사이트   /sales/insights
```

---

## 8. 알림 시스템 (Discord)

| 알림 | 조건 |
|------|------|
| 🚀 신제품 | product_key 첫 등장 |
| 🔥 세일 시작 | is_sale False → True |
| 📉 가격 하락 | 직전 대비 10%+ 하락 |
| Intel 알림 | critical/high severity 이벤트 |

WatchList가 비어있으면 모든 알림 차단.

---

## 9. 스케줄러 (자동화)

Railway Worker 서비스로 배포. `scripts/scheduler.py` — APScheduler 기반.

| 시간 (KST) | 작업 |
|-----------|------|
| 03:00 | 전체 제품 크롤 + intel 자동 트리거 |
| 00/06/12/18:00 | 뉴스 수집 (영문 4 + 한국 4) |
| 00/06/12/18:10 | Intel mirror |
| 03/09/15/21:00 | Intel spike |
| 07:00 | 환율 업데이트 |
| 매주 일요일 09:00 | 데이터 감사 |

---

## 10. 스크립트 전체 목록

**31개 스크립트 (`scripts/`)**

| 분류 | 스크립트 |
|------|----------|
| 크롤링 | `crawl_products.py`, `crawl_brands.py`, `crawl_drops.py`, `crawl_news.py` |
| Intel | `ingest_intel_events.py` (--job mirror/derived_spike/shopify_drops) |
| 시딩 | `seed_channels.py`, `seed_brands_luxury.py`, `seed_collabs.py`, `seed_directors.py` |
| 데이터 정제 | `fix_null_brand_id.py`, `cleanup_route_products.py`, `backfill_normalized_key.py` |
| 분석 | `data_audit.py`, `build_product_catalog.py`, `channel_probe.py` |
| 인프라 | `update_exchange_rates.py`, `scheduler.py`, `migrate_sqlite_to_pg.py` |

---

## 11. Alembic 마이그레이션 이력

**16개 버전** (Phase 22 기준, Railway에 모두 적용 완료)

최신: `e5f6a7b8c9d0` — `crawl_channel_logs.error_type` 컬럼 추가

---

## 12. 배포 구조 (Railway + Vercel)

```
Railway API 서비스:
  - 브랜치: main (아카이빙 커밋 792a199 기준)
  - URL: https://fashion-data-engine-production.up.railway.app
  - DB: Railway PostgreSQL (80,000+개 제품)
  - 헬스체크: GET /health → {"status":"ok","database":"ok"}

Railway Worker 서비스:
  - 시작: uv run python scripts/scheduler.py
  - 자동 크롤/뉴스/Intel/환율 운영

Vercel 프론트엔드:
  - URL: https://fashion-data-engine.vercel.app
  - 환경변수: NEXT_PUBLIC_API_URL → Railway URL
```

---

## 13. 최종 데이터 현황

**2026-03-09 아카이빙 시점 기준 (Railway PostgreSQL)**

| 항목 | 수치 |
|------|------|
| 채널 (활성) | ~137개 |
| 브랜드 | 2,500+개 (brand_id NULL 1.3%) |
| 제품 | 80,000+개 |
| ProductCatalog | 64,075개 |
| BrandCollaboration | 34건 |
| BrandDirector | 125명 |
| IntelEvent | 591건 |
| 환율 | 12개 통화 (JPY=9.4085, 수정 완료) |
| CrawlRun (최신) | #35 (2026-03-07) |

---

## 14. 알려진 문제점 및 한계

### 해결된 버그

| 버그 | 해결 | 커밋 |
|------|------|------|
| Shopify Markets KRW 현지화 과다 가격 | `Accept-Language` 헤더 제거 | T-101 |
| JPY 환율 이중부패 (88.6 → 9.41) | `update_exchange_rates.py` 재실행 + 방어 로직 | T-101 |
| JPY 오염 가격 이력 43,314건 | 삭제 후 재크롤 | T-101 |
| Route 배송보험 제품 오인덱싱 | vendor/type/title denylist | T-054 |

### 구조적 한계 (아카이빙 사유 포함)

| 한계 | 설명 |
|------|------|
| Railway 잦은 크래시 | Worker + API 동시 운영 시 메모리 부족 추정 |
| 비표준 플랫폼 지원 없음 | stores.jp / buyshop.jp / theshop.jp 크롤 불가 |
| 사용자 계정 없음 | 구매이력/관심목록 다기기 동기화 불가 |
| 크롤 의존성 | 데이터 신선도가 크롤 주기에 종속 |
| 스코프 과다 확장 | Phase 3~8에서 BI·Intel·Analytics 등 무분별 추가 |

---

## 15. 설정 및 환경변수

```bash
# .env (로컬)
DATABASE_URL=sqlite+aiosqlite:///./data/fashion.db
RAILWAY_DATABASE_URL=postgresql+asyncpg://...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
ADMIN_BEARER_TOKEN=<비밀값>
CORS_ALLOWED_ORIGINS=http://localhost:3000

# Railway (운영)
DATABASE_URL=<Railway PostgreSQL URL>
ALLOWED_ORIGINS=https://fashion-data-engine.vercel.app
ADMIN_BEARER_TOKEN=<비밀값>
DISCORD_WEBHOOK_URL=<Discord URL>

# Vercel (프론트엔드)
NEXT_PUBLIC_API_URL=https://fashion-data-engine-production.up.railway.app
```

---

*최종 업데이트: 2026-03-09 (아카이빙 기준 — Phase 27 / T-101 완료)*
*→ 아카이빙 사유 및 다음 방향: [ARCHIVE.md](./ARCHIVE.md)*
