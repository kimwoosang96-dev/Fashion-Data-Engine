# Agent Task Directive

Single source of truth for PM/developer task control.

- PM role: `claude-pm`
- Dev role: `codex-dev`
- DB role: `codex-dev` (gemini-db paused as of 2026-02-27)
- Auto-archive trigger: when this file exceeds 220 lines.
- Auto-archive target: reduce to 170 lines by moving oldest completed tasks.

## Active Tasks
<!-- ACTIVE_TASKS_START -->
<!-- ACTIVE_TASKS_END -->

## Completed Tasks (Recent)
<!-- COMPLETED_TASKS_START -->
- [x] T-20260227-006 | CRAWLER_03: EFFORTLESS/THEXSHOP 브랜드 셀렉터 재조사 | owner:codex-dev | priority:P2 | status:done | created:2026-02-27 | completed:2026-02-28 | details:GH#10 done: strategy URLs/selectors updated to live pages. Full recrawl result EFFORTLESS 19, THEXSHOP 193 (both >=5).
- [x] T-20260227-002 | DB_02: DB 인덱스 실제 적용 | owner:codex-dev | priority:P2 | status:done | created:2026-02-27 | completed:2026-02-27 | details:DB_02 done: applied 6 query indexes via Alembic revision 7b6619f9d1ad and upgraded DB to head.
- [x] T-20260228-005 | CRAWLER_02: 9개 selector_mismatch 채널 전략 수정 | owner:codex-dev | priority:P2 | status:done | created:2026-02-28 | completed:2026-02-27 | details:CRAWLER_02 done: custom strategy now falls back to generic when empty. Recrawl improved selector_mismatch set (BIZZARE 35, ECRU 103, Kasina 199, EFFORTLESS 1, THEXSHOP 1).
- [x] T-20260227-003 | FRONTEND_02: 대시보드 검색 브랜드 자동완성 드롭다운 | owner:codex-dev | priority:P1 | status:done | created:2026-02-27 | completed:2026-02-28 | details:SearchDropdown.tsx 신규. searchBrands() 병렬 호출. 빌드 통과.
- [x] T-20260227-004 | FRONTEND_03: 브랜드/채널 페이지 클라이언트 사이드 검색 필터 | owner:codex-dev | priority:P1 | status:done | created:2026-02-27 | completed:2026-02-28 | details:brands+channels 검색창+티어/세일 필터. 빌드 통과.
- [x] T-20260227-001 | DB_01: 0결과 채널 원인 분류 | owner:codex-dev | priority:P1 | status:done | created:2026-02-27 | completed:2026-02-28 | details:33개 채널 100% 라벨링. 6개 인덱스 제안. agents/archive/crawl_audit/ 보고서.
- [x] T-20260228-001 | CRAWLER_01: 자동 크롤 스케줄러 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:scripts/scheduler.py APScheduler. 03:00/07:00/07:10. --dry-run 검증 완료.
- [x] T-20260228-002 | FRONTEND_04: 브랜드 상세 페이지 /brands/[slug] | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:제품 그리드+세일 토글. /brands/{slug}/products 활용. 빌드 통과.
- [x] T-20260228-003 | FRONTEND_05: 가격 히스토리 차트 | owner:codex-dev | priority:P2 | status:done | created:2026-02-28 | completed:2026-02-28 | details:백엔드 /products/price-history/{key} + 커스텀 SVG LineChart. 7/30/전체 필터.
- [x] T-20260228-004 | FRONTEND_06: 세일 페이지 무한스크롤 | owner:codex-dev | priority:P2 | status:done | created:2026-02-28 | completed:2026-02-28 | details:IntersectionObserver. 60개씩 추가 로드. 총 19,997개 대응.
- [x] T-20260226-006 | Smoke test task | owner:codex-dev | priority:P2 | status:done | created:2026-02-26 | completed:2026-02-26 | details:Validated add-task/complete-task flow and log updates
- [x] T-20260226-001 | Issue 01 crawler quality improvement | owner:codex-dev | priority:P1 | status:done | created:2026-02-26 | completed:2026-02-26 | details:CODEX_ISSUE_01 completed
- [x] T-20260226-002 | Issue 02 brand tier classification | owner:codex-dev | priority:P1 | status:done | created:2026-02-26 | completed:2026-02-26 | details:brand_tiers.csv + classify_brands.py
- [x] T-20260226-003 | Issue 03 collaboration seed + hype scoring | owner:codex-dev | priority:P1 | status:done | created:2026-02-26 | completed:2026-02-26 | details:brand_collabs.csv + seed scripts
- [x] T-20260226-004 | Issue 04 landscape API | owner:codex-dev | priority:P1 | status:done | created:2026-02-26 | completed:2026-02-26 | details:channels landscape endpoint
<!-- COMPLETED_TASKS_END -->
