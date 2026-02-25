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

### DB 상태 (Phase 2 완료 기준)
- 154개 채널 로드 완료 (75 edit-shop, 75 brand-store, 4 others)
- 브랜드 크롤 **완료** — edit-shop 75개 중 43개 성공
  - 총 브랜드: **2,508개** / 총 channel_brand 링크: **2,557개**
  - 0결과 채널 32개 (일본 플랫폼·SSL 오류 등, 미해결)
- 브랜드 티어: **120개** 분류 완료 (high-end 3, premium 94, sports 14, street 9)
- 협업 데이터: **34개** seed 완료, hype_score 재계산 완료

### Phase 2 스키마 (모두 적용 완료)
- `Brand`: `tier`, `description_ko` 컬럼
- `BrandCollaboration`: 협업 추적 (hype_score 포함)
- `FashionNews`: 뉴스/이벤트 (미사용 예정)
- `alembic upgrade head` 실행됨 → `data/fashion.db` 최신 상태

### API 엔드포인트 (검증 완료)
- `GET /brands/?tier=<tier>` — 티어별 브랜드 목록 ✅
- `GET /brands/landscape` — 2508 nodes, 2557 edges ✅
- `GET /brands/{slug}/collabs` — 브랜드별 협업 목록 ✅
- `GET /collabs/` — hype_score 정렬, footwear 24건·apparel 10건 ✅
- `GET /collabs/hype-by-category` — avg/max 집계 ✅
- `GET /channels/landscape` — 154채널, KR 36·JP 61·US 15 ✅

### Top 채널 (브랜드 수 기준)
1. NUBIAN (JP): 251개 브랜드
2. ARKnets (JP): 226개 브랜드
3. COVERCHORD (JP): 191개 브랜드
4. NOCLAIM (KR): 181개 브랜드
5. H. Lorenzo (US): 167개 브랜드

### 크롤러 현황 (brand_crawler.py)
- **Shopify** `/products.json` API: 안정적
- **Cafe24**: cate_no dedup + 한국어 UI워드 필터 + 콜라보 패턴 필터 (> 40자)
- **커스텀 전략**: 11개 채널 (8division, kasina, thexshop, obscura 등)
- **0결과 32개 채널**: Cafe24 DOM 불일치·일본 플랫폼(BASE/Ocnk/laidback)·SSL 오류

### 완료된 Codex 이슈
- `CODEX_ISSUE_01.md` ✅ — Cafe24 개선 + 전체 크롤 실행 + stale 삭제 버그 수정
- `CODEX_ISSUE_02.md` ✅ — 브랜드 티어 분류 (classify_brands.py)
- `CODEX_ISSUE_03.md` ✅ — 협업 seed + hype_score 재계산
- `CODEX_ISSUE_04.md` ✅ — landscape API 검증

### 플래그된 URL (참고)
- `https://www.corteiz.com/password` — 비밀번호 잠금 (크롤 불가)
- `https://www.tune.kr` — SSL 오류
- `https://www.kerouac.okinawa` — SSL 오류

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
