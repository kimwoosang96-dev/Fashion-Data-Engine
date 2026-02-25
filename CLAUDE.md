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

### DB 상태
- 154개 채널 로드 완료 (75 brand-store, 75 edit-shop, 4 others)
- 채널 이름·국가·타입 수동 큐레이션 완료 (`data/channels_cleaned.csv`)
- 브랜드 크롤 **부분 실행** — `channel_brands` 테이블에 일부 데이터 있음
  - `--limit 3` 테스트로 +81(60개), 8DIVISION(453개), ADDICTED(77개) 저장됨
  - **전체 75개 edit-shop 크롤은 아직 실행 안 됨** → CODEX_ISSUE_01 과업

### 크롤러 현황 (brand_crawler.py)
- **Shopify** `/products.json` API: 안정적 (vendor 필드 정확)
- **Cafe24** `cate_no=` 필터: 개선됨
  - `cate_no` URL 기반 중복 제거 (영문/한글 동일 브랜드 dedup)
  - 한국어 카테고리 헤더 필터 (신상품, 상의, 아우터 등)
  - 콜라보 패턴 필터 (` by `, ` x `, ` X ` 포함 + 길이 > 25자)
  - CAFE24_MAX = 500 (대형 편집샵 허용)
- **8DIVISION** (kasina.co.kr에 커스텀 전략 있음): 453개 via cafe24 — 여전히 정제 필요
  - 일부 콜라보 서브카테고리 혼입 의심 → CODEX_ISSUE_01에서 추가 개선 예정

### 완료된 스키마 변경 (Alembic 마이그레이션 적용 완료)
- `Brand`: `tier`, `description_ko` 컬럼 추가
- 신규 모델: `BrandCollaboration`, `FashionNews`
- `alembic upgrade head` 실행됨 → `data/fashion.db` 최신 상태

### Codex 이슈 파일
- `CODEX_ISSUE_01.md` — Cafe24 개선 + 전체 크롤 실행
- `CODEX_ISSUE_02.md` — 브랜드 티어 seed CSV + classify_brands.py
- `CODEX_ISSUE_03.md` — 협업 데이터 seed + hype_score 계산
- `CODEX_ISSUE_04.md` — 시각화 API 검증 + channels/landscape

### 플래그된 URL (참고)
- `https://www.corteiz.com/password` — 비밀번호 잠금 (크롤 불가)
- `https://tune.kr` — DB에 있음
- `https://www.joefreshgoods.com` — DB에 있음

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
