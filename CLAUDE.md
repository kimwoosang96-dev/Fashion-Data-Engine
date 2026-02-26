# Fashion Data Engine — Claude Code Context

> For full project documentation, see AGENTS.md.
> This file contains Claude Code-specific notes and current session context.

---

## Working Directory

Always run commands from: `/Users/kim-usang/fashion-data-engine`

```bash
# Activate uv environment before any command
source /Users/kim-usang/.local/bin/env
cd /Users/kim-usang/fashion-data-engine
```

---

## Allowed Shell Commands

- `uv run python <script>` — run any script
- `uv run uvicorn fashion_engine.api.main:app --reload` — start API
- `uv run pytest` — run tests
- `uv sync` — install dependencies
- `git add/commit/status/diff/log` — version control

---

## Current Session Notes (2026-02-26)

### DB 상태 (Phase 3 구축 중)
- **채널**: 159개 (154 기존 + DSM, HBX, Slam Jam, Goodhood, Bodega 5개 추가)
- **브랜드**: 2,508개 / channel_brand 링크: 2,557개 (Phase 2 기준)
- **브랜드 티어**: 120개 분류 (high-end 3, premium 94, sports 14, street 9)
- **협업**: 34개 seed, hype_score 계산 완료
- **제품**: 898개 초기 크롤 완료 (ALIVEFORM·Patta·BoTT, brand-store 5채널 테스트)
  - Patta KR: 642개 (세일 179개)
  - BoTT: 188개
  - ALIVEFORM: 68개
- **환율**: USD 1,426 / EUR 1,686 / GBP 1,934 / JPY 9.1 / HKD 182 (2026-02-26 기준)

### Phase 3 스키마 (완료)
- `Product.product_key`: "brand-slug:handle" 교차 채널 매칭 인덱스
- `ExchangeRate`: 통화 → KRW 환율 저장
- 마이그레이션: `c3ad818a067f_add_product_key_and_exchange_rates`

### API 엔드포인트 (전체)
**Phase 2 (검증 완료):**
- `GET /brands/?tier=<tier>`, `/brands/landscape`, `/brands/{slug}/channels`
- `GET /collabs/`, `/collabs/hype-by-category`
- `GET /channels/landscape`

**Phase 3 (신규, 검증 완료):**
- `GET /products/sales?brand=&tier=` — 세일 제품 (할인율 정렬)
- `GET /products/search?q=` — 제품명 검색
- `GET /products/compare/{product_key}` — 전 채널 가격 비교 ← 핵심
- `GET /brands/{slug}/products` — 브랜드별 제품 + 가격

### 크롤러 현황
- **brand_crawler.py**: 브랜드명 수집 (Shopify vendor + Cafe24 cate_no)
- **product_crawler.py**: 제품·가격 수집 (Shopify REST API, httpx 기반)
  - URL 서브도메인 기반 통화 자동 감지 (kr.→KRW, jp.→JPY 등)
  - 전체 크롤: `uv run python scripts/crawl_products.py` (미실행)

### 실행 명령
```bash
# 환율 업데이트 (일 1회 권장)
uv run python scripts/update_exchange_rates.py

# 제품 크롤 (전체 또는 테스트)
uv run python scripts/crawl_products.py --limit 3
uv run python scripts/crawl_products.py --channel-type brand-store

# 가격 비교 조회 예시
# GET /products/compare/new-balance:new-balance-2002r
```

### 완료된 이슈
- Phase 2 Codex Issues 01~04 ✅
- Phase 3 제품 가격 비교 인프라 ✅ (전체 채널 크롤은 미실행)

---

## Collaboration with Codex

This project is set up for dual-agent development:
- **Claude Code** (this session): interactive local development, debugging, data exploration
- **OpenAI Codex**: longer context tasks, bulk feature implementation via GitHub issues/PRs

**How to handoff to Codex:**
1. Commit current state to git
2. Open a GitHub issue with the task description, referencing AGENTS.md for context
3. Codex will read AGENTS.md as its primary context

**How to integrate Codex PRs:**
1. Review the PR diff carefully
2. Run `uv run pytest` to verify no regressions
3. If DB schema changed, check that `alembic/` has a migration

---

## Frequently Needed Commands

```bash
# Check DB contents
uv run python -m fashion_engine.cli channels
uv run python -m fashion_engine.cli brands

# Run brand crawler (test mode)
uv run python scripts/crawl_brands.py --limit 3

# API docs
uv run uvicorn fashion_engine.api.main:app --reload
# → open http://localhost:8000/docs

# Query: which channels carry a brand?
uv run python -m fashion_engine.cli brand <slug>
uv run python -m fashion_engine.cli search <query>
```

---

## File Change Checklist

When adding a new SQLAlchemy model:
1. Create `src/fashion_engine/models/<name>.py`
2. Add import to `src/fashion_engine/models/__init__.py`
3. Add Pydantic schema to `src/fashion_engine/api/schemas.py`
4. Add service functions to `src/fashion_engine/services/`
5. Add API routes if needed

When adding a new channel-specific crawler strategy:
1. Edit `src/fashion_engine/crawler/brand_crawler.py::CHANNEL_STRATEGIES`
2. Test: `uv run python scripts/crawl_brands.py --limit 1`
