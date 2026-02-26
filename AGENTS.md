# Fashion Data Engine — Agent Guide

This document is the **primary reference** for all AI coding agents (Claude, Codex, etc.).
Read this before writing any code. Keep this file up to date after every phase.

---

## Project Overview

A fashion data platform that:
1. **Aggregates** sales channels (편집샵 / brand-store) from a curated list
2. **Maps** which brands each channel carries (via web scraping)
3. **Tracks** prices, new arrivals, and sales across channels
4. **Compares** prices cross-channel via `product_key` matching
5. **Alerts** via Discord when watched brands/channels go on sale
6. **Scores** purchases by percentile vs. historical price data
7. **Surfaces** upcoming drops and release dates

**Current phase:** Phase 5 — Next.js 프론트엔드 대시보드 (완료)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Package manager | `uv` (not pip, not poetry) |
| Database | SQLite (`data/fashion.db`) / PostgreSQL (production) |
| ORM | SQLAlchemy 2.0 async + Alembic migrations |
| API | FastAPI (async) |
| Crawler | httpx (Shopify REST) + Playwright (headless) + BeautifulSoup4 |
| Validation | Pydantic v2 |
| CLI | Typer + Rich |
| Frontend | Next.js 16 (App Router) + TypeScript + Tailwind CSS + shadcn/ui |
| Node.js | v24 via nvm |
| Alerts | Discord webhook (httpx) |

---

## Repository Structure

```
fashion-data-engine/
├── AGENTS.md              ← YOU ARE HERE (always up to date)
├── CLAUDE.md              ← Claude Code specific session notes
├── agents/                ← Agent collaboration system
│   ├── README.md
│   ├── PLAYBOOK.md        ← PM-Dev handshake protocol
│   ├── TASK_DIRECTIVE.md  ← Active & completed task board (source of truth)
│   └── WORK_LOG.md        ← Append-only activity log
├── pyproject.toml
├── .env / .env.example    ← DISCORD_WEBHOOK_URL, ALERT_PRICE_DROP_THRESHOLD
├── data/
│   ├── fashion.db         ← SQLite (gitignored)
│   ├── brand_tiers.csv    ← 120개 브랜드 tier 분류
│   └── brand_collabs.csv  ← 34개 콜라보 시드 데이터
├── alembic/               ← DB migrations
├── scripts/
│   ├── crawl_brands.py
│   ├── crawl_products.py  ← 제품·가격 수집 + Discord 알림
│   ├── crawl_drops.py
│   ├── update_exchange_rates.py
│   ├── classify_brands.py
│   ├── seed_collabs.py
│   └── agent_coord.py     ← 에이전트 태스크 관리 CLI
└── src/fashion_engine/
    ├── config.py
    ├── database.py
    ├── models/
    │   ├── channel.py, brand.py, channel_brand.py
    │   ├── product.py      ← product_key = "brand-slug:shopify-handle"
    │   ├── price_history.py, exchange_rate.py
    │   ├── purchase.py, watchlist.py, drop.py
    ├── crawler/
    │   ├── brand_crawler.py
    │   └── product_crawler.py
    ├── services/
    │   ├── channel_service.py, brand_service.py
    │   ├── product_service.py  ← upsert_product → (product, is_new, sale_just_started)
    │   ├── purchase_service.py ← calc_score (S/A/B/C/D 백분위)
    │   ├── watchlist_service.py ← should_alert()
    │   ├── drop_service.py
    │   └── alert_service.py   ← Discord embed
    └── api/
        ├── main.py         ← FastAPI + CORSMiddleware (localhost:3000)
        ├── schemas.py
        ├── brands.py, channels.py, products.py, collabs.py
        ├── purchases.py, drops.py, watchlist.py
```

### Frontend Structure

```
frontend/
  src/
    app/
      layout.tsx, page.tsx          ← 루트 레이아웃 + 대시보드
      sales/page.tsx                ← 세일 제품 전체 목록
      brands/page.tsx               ← 브랜드 목록 + 신상품 현황
      channels/page.tsx             ← 채널 목록 + 세일/신상품 현황
      watchlist/page.tsx            ← 관심목록 관리
      purchases/page.tsx, new/, [id]/
      drops/page.tsx
      compare/[key]/page.tsx        ← 채널별 가격 비교 (핵심)
    components/
      Nav.tsx                       ← 7개 메뉴 사이드바
      ProductCard.tsx               ← 세일 제품 카드 (링크 내장)
      ScoreBadge.tsx                ← S/A/B/C/D 등급 배지
    lib/
      api.ts                        ← fetch wrapper + API 클라이언트 함수
      types.ts                      ← TypeScript 인터페이스
  .env.local                        ← NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Database Schema

```
channels:       id, name, url (UNIQUE), channel_type, country, is_active
brands:         id, name, slug (UNIQUE), name_ko, tier, origin_country, description_ko
channel_brands: channel_id FK, brand_id FK, crawled_at
products:       id, channel_id FK, brand_id FK, name, product_key,
                url (UNIQUE), image_url, price_krw, original_price_krw,
                currency, is_active, is_new, is_sale, discount_rate
price_history:  id, product_id FK, price_krw, original_price_krw,
                is_sale, discount_rate, crawled_at
exchange_rates: id, currency, rate_to_krw, updated_at
purchases:      id, product_key, product_name, brand_slug, channel_name,
                paid_price_krw, original_price_krw, purchased_at, notes
watchlist:      id, watch_type ("brand"|"channel"|"product_key"), watch_value, notes
drops:          id, brand_id FK, product_name, product_key, source_url,
                image_url, price_krw, release_date,
                status ("upcoming"|"released"|"sold_out"), detected_at, notified_at
brand_collaborations: id, brand1_id FK, brand2_id FK, collab_name, hype_score
```

**product_key 형식**: `"brand-slug:shopify-handle"` (예: `new-balance:new-balance-2002r`)

---

## Key API Endpoints

```
GET  /products/sales?brand=&tier=&limit=   → 세일 제품 (할인율 정렬)
GET  /products/sales-highlights?limit=     → 세일 하이라이트 (image, is_new 포함)
GET  /products/search?q=                   → 제품명 검색
GET  /products/related-searches?q=         → 연관검색어 제안
GET  /products/compare/{product_key}       → 전 채널 가격 비교 ← 핵심

GET  /brands/?tier=                        → 브랜드 목록
GET  /brands/search?q=                     → 브랜드명 검색 (KO/EN)
GET  /brands/highlights?limit=             → 브랜드별 신상품 현황
GET  /brands/landscape                     → 시각화용 노드/엣지
GET  /brands/{slug}/channels               → 브랜드 취급 채널

GET  /channels/                            → 채널 목록
GET  /channels/highlights?limit=           → 채널별 세일/신상품 현황

POST /purchases/                           → 구매 등록
GET  /purchases/stats                      → 통계
GET  /purchases/{id}/score                 → 성공도 (S/A/B/C/D + 백분위)
DELETE /purchases/{id}

GET  /watchlist/                           → 관심목록
POST /watchlist/                           → 추가 {watch_type, watch_value}
DELETE /watchlist/{id}

GET  /drops/upcoming                       → 예정 드롭
GET  /drops/?status=                       → 드롭 목록
```

---

## Development Workflow

### Setup

```bash
# Python 환경
source /Users/kim-usang/.local/bin/env
cd /Users/kim-usang/fashion-data-engine
uv sync

# Node.js (nvm 필요)
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh"
cd frontend && npm install
```

### Run

```bash
# 터미널 1 — 백엔드
uv run uvicorn fashion_engine.api.main:app --reload
# → http://localhost:8000/docs

# 터미널 2 — 프론트엔드
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh"
cd frontend && npm run dev
# → http://localhost:3000
```

### Data Pipeline

```bash
uv run python scripts/update_exchange_rates.py        # 환율 (일 1회)
uv run python scripts/crawl_products.py --no-alerts   # 초기 시드
uv run python scripts/crawl_products.py               # 알림 포함 크롤
uv run python scripts/crawl_drops.py                  # 드롭 수집
```

### Agent Coordination

```bash
python scripts/agent_coord.py add-task --title "..." --owner codex-dev --priority P1
python scripts/agent_coord.py complete-task --id T-YYYYMMDD-NNN --agent codex-dev --summary "..."
python scripts/agent_coord.py log --agent codex-dev --task-id T-... --message "..."
```

---

## Coding Conventions

1. **Async-first**: 모든 DB 연산은 `async`
2. **Services layer**: DB 로직은 `services/`에만
3. **Models `__init__.py`**: 새 모델 추가 시 반드시 import 등록
4. **product_key**: `f"{brand_slug}:{shopify_handle}"` 형식
5. **Brand slugs**: `python-slugify`로 생성
6. **Currency inference**: URL 서브도메인 기반 (`kr.` → KRW, `jp.` → JPY)
7. **알림 조건**: `should_alert()` — watchlist 비어있으면 False
8. **프론트엔드 변경 후**: `npm run build`로 타입 에러 확인 필수
9. **새 API 엔드포인트**: `api.ts` + `types.ts` 동시 업데이트 필수

---

## Current Status (2026-02-27)

### Done ✅

| Phase | 내용 |
|-------|------|
| Phase 1 | 159개 채널, 2,508개 브랜드, 120개 tier 분류, 34개 협업 |
| Phase 2 | Cafe24 크롤러 개선 (43/75 편집샵), Landscape API |
| Phase 3 | product_key 교차채널 매칭, ExchangeRate, 898개 제품 초기 크롤 |
| Phase 4 | Purchase 성공도, WatchList 알림 필터, Drop 크롤러, Discord webhook |
| Phase 5 | Next.js 11개 페이지, CORS, highlight/related-search API, agents/ 협업 시스템 |

### Pending

| Task ID | 내용 | 담당 | 우선순위 |
|---------|------|------|----------|
| FRONTEND_02 | 대시보드 검색 브랜드 자동완성 드롭다운 | codex-dev | P1 |
| FRONTEND_03 | 브랜드/채널 페이지 클라이언트 사이드 검색 필터 | codex-dev | P1 |
| DB_01 | 0결과 채널 원인 분류 + 재크롤 전략 실행 | codex-dev | P1 |
| DB_02 | DB 인덱스 최적화 + 쿼리 개선 | codex-dev | P2 |

---

## Important Notes for Agents

- **`data/fashion.db` 커밋 금지** (gitignored)
- **`.env` 커밋 금지** (Discord webhook 포함)
- **WatchList가 비어있으면 Discord 알림 없음** (정상 동작)
- **크롤러 전략 변경 시 `--limit 1` 테스트 먼저**
- **Alembic**: 모델 변경 시 `uv run alembic revision --autogenerate` 필수
- **프론트엔드 nvm 필요**: `export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh"` 먼저 실행
