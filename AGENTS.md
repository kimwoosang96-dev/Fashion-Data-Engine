# Fashion Data Engine — Agent Guide

This document is the primary reference for AI coding agents (OpenAI Codex, Claude Code, etc.)
working on this project. Read this before writing any code.

---

## Project Overview

A fashion data platform that:
1. **Aggregates** sales channels (편집샵 / multi-brand edit shops) from a curated list
2. **Maps** which brands each channel carries (via web scraping)
3. **Tracks** prices, new arrivals, and sales across channels
4. **Archives** AI-generated lookbooks with virtual models (future phase)

**Current phase:** Phase 1 — Data Engine (channel preprocessing + brand mapping)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Package manager | `uv` (not pip, not poetry) |
| Database | SQLite (local dev) / PostgreSQL (production) |
| ORM | SQLAlchemy 2.0 async + Alembic migrations |
| API | FastAPI (async) |
| Crawler | Playwright (headless Chromium) + BeautifulSoup4 |
| Validation | Pydantic v2 |
| CLI | Typer + Rich |

---

## Repository Structure

```
fashion-data-engine/
├── AGENTS.md              ← YOU ARE HERE
├── CLAUDE.md              ← Claude Code specific context
├── pyproject.toml         ← uv project + dependencies
├── .env                   ← local config (not committed)
├── .env.example           ← env template
├── docker-compose.yml     ← PostgreSQL for production use
│
├── data/
│   ├── channels_input.csv    ← raw channel URLs (user-provided)
│   ├── channels_cleaned.csv  ← preprocessed channel data
│   ├── channels_flagged.csv  ← URLs needing manual review
│   └── fashion.db            ← SQLite database (gitignored)
│
├── scripts/
│   ├── preprocess_channels.py  ← Step 1: normalize URLs, dedup
│   ├── seed_channels.py        ← Step 2: load cleaned CSV → DB
│   └── crawl_brands.py         ← Step 3: crawl brands per channel
│
└── src/fashion_engine/
    ├── config.py           ← pydantic-settings from .env
    ├── database.py         ← SQLAlchemy engine + session + init_db()
    ├── cli.py              ← Typer CLI entrypoint
    │
    ├── models/             ← SQLAlchemy ORM models
    │   ├── __init__.py     ← IMPORTANT: imports all models (mapper registration)
    │   ├── channel.py      ← Channel (판매채널)
    │   ├── brand.py        ← Brand
    │   ├── channel_brand.py ← Channel↔Brand N:M join table
    │   ├── product.py      ← Product
    │   ├── price_history.py ← PriceHistory
    │   └── category.py     ← Category (hierarchical, parent_id)
    │
    ├── crawler/
    │   ├── base.py         ← BaseCrawler (Playwright context manager)
    │   ├── url_normalizer.py ← product URL → homepage URL
    │   └── brand_crawler.py  ← extract brand list per channel
    │
    ├── services/
    │   ├── channel_service.py  ← DB queries for channels
    │   └── brand_service.py    ← DB queries for brands
    │
    └── api/
        ├── main.py         ← FastAPI app + lifespan
        ├── schemas.py      ← Pydantic response schemas
        ├── channels.py     ← /channels routes
        └── brands.py       ← /brands routes
```

---

## Database Schema

```
channels:       id, name, url (homepage, UNIQUE), original_url, channel_type,
                country, description, is_active, created_at, updated_at

brands:         id, name, slug (UNIQUE), name_ko, origin_country,
                description, official_url, created_at

channel_brands: channel_id FK, brand_id FK  [composite PK]
                crawled_at

categories:     id, name, name_en, slug (UNIQUE), parent_id (self-ref FK),
                level (0=top, 1=mid, 2=leaf), created_at

products:       id, channel_id FK, brand_id FK, category_id FK,
                name, sku, url (UNIQUE), image_url, description,
                is_active, is_new, is_sale, created_at, updated_at

price_history:  id, product_id FK, price, original_price, currency,
                is_sale, discount_rate, crawled_at
```

**Critical:** Always import `fashion_engine.models` (the package) before running
any SQLAlchemy queries to ensure all mappers are registered. See `database.py:init_db()`.

---

## Key API Endpoints

```
GET  /                          → health + version
GET  /channels/                 → list all active channels
GET  /channels/{id}             → channel detail
GET  /channels/{id}/brands      → brands carried by this channel
GET  /brands/                   → list all brands
GET  /brands/search?q=          → search brands by name (Korean/English)
GET  /brands/{slug}             → brand detail
GET  /brands/{slug}/channels    → channels that carry this brand ← CORE FEATURE
GET  /health
```

---

## Development Workflow

### Setup
```bash
# 1. Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env

# 2. Install dependencies + Python 3.12
uv sync
uv run playwright install chromium

# 3. Copy .env
cp .env.example .env

# 4. (Optional) PostgreSQL via Docker
docker-compose up -d
# Then update .env: DATABASE_URL=postgresql+asyncpg://fashion:password@localhost:5432/fashion_db
```

### Data Pipeline (run in order)
```bash
# Step 1: preprocess raw channel URLs
uv run python scripts/preprocess_channels.py
# → data/channels_cleaned.csv (154 channels as of 2026-02)

# Step 2: load into DB
uv run python scripts/seed_channels.py

# Step 3: crawl brands per channel
uv run python scripts/crawl_brands.py --limit 5   # test first
uv run python scripts/crawl_brands.py             # full run
```

### Run API
```bash
uv run uvicorn fashion_engine.api.main:app --reload
# Swagger UI: http://localhost:8000/docs
```

### CLI
```bash
uv run python -m fashion_engine.cli channels
uv run python -m fashion_engine.cli brands
uv run python -m fashion_engine.cli brand <slug>
uv run python -m fashion_engine.cli search <query>
```

### Run Tests
```bash
uv run pytest
```

---

## Coding Conventions

1. **Async-first**: all DB operations and crawler methods are `async`
2. **Services layer**: DB logic lives in `services/`, not in routes or scripts
3. **Models `__init__.py`**: always add new models to the imports list there
4. **URL normalization**: always use `url_normalizer.normalize_to_homepage()` when storing channel URLs
5. **Brand slugs**: always use `python-slugify` for slug generation — never hand-roll
6. **Rate limiting**: `BaseCrawler` handles delays; do not add extra `sleep()` calls outside it
7. **No docstrings on unchanged code**: only add comments where logic is non-obvious

---

## Current Status (2026-02-26)

### Done ✅
- Project scaffolding (uv, pyproject.toml, docker-compose)
- Channel preprocessing pipeline (URL normalization, dedup, flag filtering)
- SQLAlchemy models: Channel, Brand, ChannelBrand, Category, Product, PriceHistory, **BrandCollaboration**, **FashionNews**
- Brand model extended: `tier` (high-end/premium/street/sports/spa), `description_ko`
- Alembic migrations configured (`alembic.ini`, `alembic/env.py`, `alembic/versions/`)
- FastAPI REST API with channel/brand query endpoints
  - `GET /brands/?tier=` — tier 필터 지원
  - `GET /brands/landscape` — 시각화용 노드/엣지 데이터
  - `GET /collabs/` — 협업 목록 (hype_score 정렬)
  - `GET /collabs/hype-by-category` — 카테고리별 하입 집계
- Playwright-based brand crawler (Shopify API + Cafe24 + generic)
- CLI tool (Typer + Rich)
- 154 channels loaded into DB (75 brand-store, 75 edit-shop, 4 others)
- Channel data curated: names, country codes, channel_type for all 154 channels

### Pending (Codex Issues)
- **CODEX_ISSUE_01**: Cafe24 strategy refinement + full 75 edit-shop crawl
- **CODEX_ISSUE_02**: Brand tier seed CSV + `scripts/classify_brands.py`
- **CODEX_ISSUE_03**: BrandCollaboration seed data + hype_score auto-calculation
- **CODEX_ISSUE_04**: Full crawl completion + 0-result channel custom strategies

### Phase 2 (Price tracking)
- [ ] Product crawler (price, image, SKU per product page)
- [ ] Price history recording
- [ ] Sale / new arrival detection
- [ ] Crawl scheduler (APScheduler)

### Phase 3 (Frontend + AI)
- [ ] Next.js frontend (brand/channel search, price comparison UI)
- [ ] AI virtual try-on lookbook (Stable Diffusion or external API)
- [ ] Category tree auto-generation from crawled product data

---

## Important Notes for Agents

- **Do not commit `data/fashion.db`** (gitignored — it's local state)
- **Do not commit `.env`** (gitignored — contains secrets)
- **Do not modify `data/channels_input.csv`** without user confirmation
- When adding new crawler strategies to `brand_crawler.py::CHANNEL_STRATEGIES`,
  test with `--limit 1` before running on all channels
- The `spigen.co.kr` and `mercari.com` entries in `channels_cleaned.csv` are
  flagged as `non-fashion` / `secondhand-marketplace` — handle appropriately
