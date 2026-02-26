# Agent Task Directive

Single source of truth for PM/developer task control.

- PM role: `claude-pm`
- Dev role: `codex-dev`
- DB role: `codex-dev` (gemini-db paused as of 2026-02-27)
- Auto-archive trigger: when this file exceeds 220 lines.
- Auto-archive target: reduce to 170 lines by moving oldest completed tasks.

## Active Tasks
<!-- ACTIVE_TASKS_START -->
- [ ] T-20260227-003 | FRONTEND_02: 대시보드 검색 브랜드 자동완성 드롭다운 | owner:codex-dev | priority:P1 | status:active | created:2026-02-27 | details:검색창 타이핑 시 brands/search API 호출 → 드롭다운 표시. SearchDropdown.tsx 신규 컴포넌트. GitHub Issue 참고.
- [ ] T-20260227-004 | FRONTEND_03: 브랜드/채널 페이지 클라이언트 사이드 검색 필터 | owner:codex-dev | priority:P1 | status:active | created:2026-02-27 | details:brands/page.tsx + channels/page.tsx에 검색 입력창 추가 (클라이언트 필터, 추가 API 호출 없음). GitHub Issue 참고.
- [ ] T-20260227-001 | DB crawl quality audit and completion strategy | owner:codex-dev | priority:P1 | status:active | created:2026-02-27 | details:Reassigned from gemini-db (paused). See agents/TASK_BRIEF_GEMINI_DB_SPRINT1.md.
- [ ] T-20260227-002 | DB production readiness sprint (coverage + integrity + performance) | owner:codex-dev | priority:P2 | status:active | created:2026-02-27 | details:Reassigned from gemini-db (paused). See agents/TASK_BRIEF_GEMINI_DB_SPRINT2.md.
<!-- ACTIVE_TASKS_END -->

## Completed Tasks (Recent)
<!-- COMPLETED_TASKS_START -->
- [x] T-20260226-006 | Smoke test task | owner:codex-dev | priority:P2 | status:done | created:2026-02-26 | completed:2026-02-26 | details:Validated add-task/complete-task flow and log updates
- [x] T-20260226-001 | Issue 01 crawler quality improvement and full crawl run | owner:codex-dev | priority:P1 | status:done | created:2026-02-26 | completed:2026-02-26 | details:CODEX_ISSUE_01 and report completed
- [x] T-20260226-002 | Issue 02 brand tier classification pipeline | owner:codex-dev | priority:P1 | status:done | created:2026-02-26 | completed:2026-02-26 | details:data/brand_tiers.csv and scripts/classify_brands.py
- [x] T-20260226-003 | Issue 03 collaboration seed and hype scoring | owner:codex-dev | priority:P1 | status:done | created:2026-02-26 | completed:2026-02-26 | details:data/brand_collabs.csv and seed/recalculate scripts
- [x] T-20260226-004 | Issue 04 landscape API and quality report support | owner:codex-dev | priority:P1 | status:done | created:2026-02-26 | completed:2026-02-26 | details:channels landscape endpoint and data quality reporting
<!-- COMPLETED_TASKS_END -->
