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

## Current Session Notes (2026-03-03)

### DB 상태 (Phase 26 완료)
- **채널**: 활성 ~137개 (접근 불가 7개 + 저우선 22개 비활성화)
- **브랜드**: 2,500+개 / brand_id backfill 완료 (NULL 24% → 1.3%)
- **제품**: 80,000+개 (Railway PG 기준) / ProductCatalog 64,075개
- **Intel 이벤트**: `intel_events` 테이블 운영 중 (drops/collabs/news mirror + sale_start/sold_out/restock/sales_spike 파생 이벤트)

### 완료된 Phase (최신 순)
- **Phase 26 — Fashion Intel Hub (T-072~T-076)** ✅
  - `intel_events / intel_event_sources / intel_ingest_runs / intel_ingest_logs` 4개 테이블
  - `/intel/events`, `/intel/map-points`, `/intel/timeline`, `/intel/highlights`, `/intel/events/{id}` API
  - `/intel` 프론트엔드: 레이어 토글, 가상 스크롤 피드, Maplibre 지도(npm), 타임라인
  - `scripts/ingest_intel_events.py` — mirror(drops/collabs/news) + derived_spike 잡
  - 파생 이벤트: sale_start(discount_rate severity) / sold_out / restock / sales_spike(7d baseline)
  - `GET /admin/intel-status` 운영 대시보드 섹션
  - 스케줄러 `intel_ingest_0730` 잡 (INTEL_INGEST_ENABLED gate)

- **Phase 22~25 — 크롤러 안정화** ✅
  - `channel_probe.py`, `deactivate_dead_channels.py`, Cafe24 + WooCommerce 수집
  - price guard, catalog_service(incremental), CrawlRun 모니터링

### API 엔드포인트 (전체)
- `GET /brands/*`, `/collabs/*`, `/channels/landscape`
- `GET /products/sales`, `/products/search`, `/products/compare/{product_key}`
- `GET /catalog/`, `/catalog/{normalized_key:path}`
- `GET /purchases/*`, `/drops/*`
- `GET /intel/events`, `/intel/map-points`, `/intel/timeline`, `/intel/highlights`, `/intel/events/{id}`
- `GET /admin/crawl-runs`, `/admin/intel-status`, `/admin/catalog-stats`

### 주요 실행 명령
```bash
# 제품 크롤
uv run python scripts/crawl_products.py --limit 3

# Intel 이벤트 ingest
uv run python scripts/ingest_intel_events.py --job mirror
uv run python scripts/ingest_intel_events.py --job derived_spike --window-hours 48

# 카탈로그 빌드
uv run python scripts/build_product_catalog.py

# 환율 업데이트
uv run python scripts/update_exchange_rates.py
```

### 완료된 이슈
- Phase 2~4, 17~19, 22~26 (T-001~T-076) 모두 완료 ✅

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
