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

## Current Session Notes (2026-02-25)

- 154 channels are loaded in `data/fashion.db` (SQLite)
- Brand crawling has NOT been run yet — `channel_brands` table is empty
- Channel names need curation: many are product titles, not store names
  - `data/channels_cleaned.csv` → edit the `name` column → re-run `seed_channels.py`
- 3 flagged URLs in `data/channels_flagged.csv`:
  - `https://www.corteiz.com/password` — password-protected
  - `https://tune.kr/account/draw-history` → normalized to `https://www.tune.kr` (already in DB)
  - `https://joefreshgoods.com/password` → normalized to `https://www.joefreshgoods.com` (already in DB)

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
