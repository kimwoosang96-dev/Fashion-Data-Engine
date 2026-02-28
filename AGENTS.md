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
products:       id, channel_id FK, brand_id FK, name, vendor, product_key,
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
uv run python scripts/scheduler.py --dry-run          # 스케줄 등록 확인
uv run python scripts/scheduler.py                    # 자동 스케줄 실행
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

## ⚠️ 스크립트 DB 접근 — 절대 규칙

### 절대 하지 말 것

```python
# ❌ 금지: sqlite3 직접 사용, 하드코딩 경로
import sqlite3
DB_PATH = Path("data/fashion.db")
conn = sqlite3.connect(DB_PATH)
```

이유: Railway PostgreSQL에서 동작하지 않음. 환경변수 DATABASE_URL을 무시함.

### 반드시 이렇게 작성

```python
# ✅ 정답: SQLAlchemy async + DATABASE_URL 환경변수 자동 지원
from __future__ import annotations
import asyncio, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sqlalchemy import text                                   # noqa: E402
from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402

async def run(*, apply: bool) -> int:
    await init_db()
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(text("SELECT id FROM brands"))).fetchall()
        if apply:
            await db.execute(text("UPDATE ..."))
            await db.commit()
    return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(apply=False)))
```

실행 방법:
```bash
# 로컬 SQLite (기본, .env 또는 환경변수 없을 때)
uv run python scripts/my_script.py --apply

# Railway PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:pw@host:5432/railway \
  uv run python scripts/my_script.py --apply
```

### IN 절 바인딩 (PostgreSQL 호환)

```python
# ❌ 금지: f-string SQL 인젝션 위험 + PostgreSQL 비호환
cur.execute(f"DELETE FROM brands WHERE id IN ({','.join(map(str, ids))})")

# ✅ 정답: SQLAlchemy expandable bindparam
from sqlalchemy import bindparam, text

bp = bindparam("ids", expanding=True)
await db.execute(
    text("DELETE FROM brands WHERE id IN :ids").bindparams(bp),
    {"ids": ids},
)
await db.commit()
```

### 기존 올바른 스크립트 참고 (반드시 확인)

- `scripts/purge_fake_brands.py` — 삭제 스크립트의 정석
- `scripts/seed_directors.py` — CSV 시드 스크립트의 정석
- `scripts/remap_product_brands.py` — 대량 UPDATE 배치 처리

---

## 배포 환경

| 환경 | DB | 실행 방법 |
|------|----|-----------|
| 로컬 개발 | SQLite (`data/fashion.db`) | `uv run python scripts/xxx.py` |
| Railway (운영) | PostgreSQL | `DATABASE_URL=postgresql+asyncpg://... uv run python scripts/xxx.py` |

**Railway 재배포 트리거**: git push 후 Railway 자동 배포 → `alembic upgrade head` 자동 실행
**Railway 스크립트 실행**: 로컬에서 `DATABASE_URL` 환경변수 설정 후 실행

---

## Current Status (2026-03-01)

### Done ✅

| Phase | 내용 |
|-------|------|
| Phase 1~5 | 159채널·2,561브랜드·120 tier, 협업/구매점수/Discord알림/Next.js 15개 페이지 |
| Phase 6 | Makefile, 뉴스 RSS 크롤러, 협업 타임라인 페이지 |
| Phase 7 | BrandDirector 모델, Admin 입력폼, Instagram URL, 브랜드 상세 통합뷰 |
| Phase 8~9 | 세일 dedup(product_key 최저가), 협업 Admin CRUD, 채널-브랜드 감사 도구 |
| Phase 10~11 | 품절 아카이브(archived_at), 멀티채널 경쟁 페이지, Cloud(Railway+Vercel) 전환 |
| Phase 12~13 | 브랜드 인리치먼트(CSV), 크리에이티브 디렉터 CSV(125개), 가짜 브랜드 정제(~500개 삭제) |
| GH#41 | Product.vendor 컬럼 + product_key→brand_id 재매핑(2,423개 복구) |

### DB 현황 (2026-03-01)

| 항목 | 수치 |
|------|------|
| 채널 | 159개 (edit-shop 81 + brand-store 78) |
| 브랜드 | ~2,561개 (Railway) |
| 제품 | ~26,000개 |
| brand_directors | 125개 (로컬) / 109개 (Railway) |
| brand_id NULL 제품 | ~18,900개 (FASCINATE 등 vendor=채널명인 경우) |

### 진행 중 / Pending

`agents/TASK_DIRECTIVE.md` 참조 (항상 최신 소스).

---

## Important Notes for Agents

- **`data/fashion.db` 커밋 금지** (gitignored)
- **`.env` 커밋 금지** (Discord webhook 포함)
- **WatchList가 비어있으면 Discord 알림 없음** (정상 동작)
- **크롤러 전략 변경 시 `--limit 1` 테스트 먼저**
- **Alembic**: 모델 변경 시 `uv run alembic revision --autogenerate` 필수
- **프론트엔드 nvm 필요**: `export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh"` 먼저 실행
- **스크립트 DB 접근**: 반드시 위의 "스크립트 DB 접근 — 절대 규칙" 섹션 준수
  - `sqlite3` 직접 사용 절대 금지 — Railway PostgreSQL에서 동작 안 함
  - 하드코딩된 `DB_PATH = Path("data/fashion.db")` 절대 금지
  - 반드시 `AsyncSessionLocal` + `init_db()` 패턴 사용
  - 이 규칙 위반 시 PR 전체 반려
