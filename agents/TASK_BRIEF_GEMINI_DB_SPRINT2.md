# Gemini DB Sprint 2 — DB Production Readiness Plan

Target agent: `gemini-db`  
Task ID: `T-20260227-002`  
Priority: `P1`  
Start date: `2026-02-27`

## Objective
- Achieve a defensible `DB ready` state for launch by closing 3 gaps:
1. Crawl coverage completeness by channel
2. Brand-channel data integrity (no mixed entities)
3. Query latency stability for dashboard/search APIs

## Scope
### A) Crawl Completion Audit (100% channel-level classification)
- Build a single truth table for all channels:
  - `channel_id`, `channel_name`, `channel_type`, `country`
  - `brand_count`, `product_count`, `last_crawled_at`
  - `crawl_status`: `done / partial / failed / not_started`
  - `failure_reason`: `ssl_error / timeout / blocked_or_bot / selector_mismatch / empty_inventory / unknown`
- Deliverable:
  - `agents/archive/gemini_db/crawl_completion_audit_2026-02-27.csv`

### B) Mixed Data Resolution (brand vs channel)
- Classify suspicious brand rows into:
  - `safe_delete`
  - `manual_review`
  - `keep`
- Decision rules:
  - `safe_delete`: no `products.brand_id` refs AND no meaningful `channel_brands` impact
  - `manual_review`: referenced by products or multiple channel links
  - `keep`: known real brand despite naming collision
- Deliverables:
  - `agents/archive/gemini_db/mixed_entity_decisions_2026-02-27.csv`
  - `agents/archive/gemini_db/mixed_entity_cleanup_sql_2026-02-27.sql`

### C) Query and Index Hardening (API-focused)
- Target endpoints:
  - `/products/search`
  - `/products/sales-highlights`
  - `/channels/highlights`
  - `/brands/highlights`
- Produce:
  - query profile summary (`before` baseline)
  - index plan (`DDL ready`)
  - expected impact notes (`high/medium/low`)
- Deliverable:
  - `agents/archive/gemini_db/query_index_hardening_2026-02-27.md`

## Time Budget (ETA)
- A) Crawl completion audit: `2.0h`
- B) Mixed data classification + SQL draft: `1.5h`
- C) Query/index hardening report: `1.5h`
- Total: `~5.0h` (single uninterrupted run)
- If recrawl is needed after diagnosis:
  - Additional execution window: `4h ~ 12h` (depends on blocked channels ratio and retry policy)

## Definition of Done (DoD)
1. Every channel is assigned exactly one crawl status and one failure reason (if not done).
2. Every mixed candidate row is tagged into `safe_delete/manual_review/keep`.
3. At least 5 concrete index DDL statements are proposed with endpoint mapping.
4. All outputs are saved under `agents/archive/gemini_db/`.
5. Work log updated at least 3 times:
  - start
  - mid
  - finish

## Execution Commands
```bash
.venv/bin/python scripts/agent_coord.py log --agent gemini-db --task-id T-20260227-002 --message "Sprint2 start: crawl completion audit"
.venv/bin/python scripts/agent_coord.py log --agent gemini-db --task-id T-20260227-002 --message "Sprint2 mid: mixed data classification in progress"
.venv/bin/python scripts/agent_coord.py complete-task --id T-20260227-002 --agent gemini-db --summary "Sprint2 complete: audit + mixed cleanup plan + index hardening report delivered"
```

## Handoff to Codex Dev
- `safe_delete` SQL is applied only after `codex-dev` confirmation.
- Index DDL enters migration branch (`alembic`) after PM approval.
