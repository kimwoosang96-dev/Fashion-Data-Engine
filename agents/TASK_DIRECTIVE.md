# Agent Task Directive

Single source of truth for PM/developer task control.

- PM role: `claude-pm`
- Dev role: `codex-dev`
- DB role: `codex-dev` (gemini-db paused as of 2026-02-27)
- Auto-archive trigger: when this file exceeds 220 lines.
- Auto-archive target: reduce to 170 lines by moving oldest completed tasks.

## Active Tasks
<!-- ACTIVE_TASKS_START -->
- [ ] T-20260227-003 | FRONTEND_02: 대시보드 검색 브랜드 자동완성 드롭다운 | owner:codex-dev | priority:P1 | status:active | created:2026-02-27 | details:GH#1. SearchDropdown.tsx 신규. searchBrands() 병렬 호출. 브랜드 클릭→세일 필터링.
- [ ] T-20260227-004 | FRONTEND_03: 브랜드/채널 페이지 클라이언트 사이드 검색 필터 | owner:codex-dev | priority:P1 | status:active | created:2026-02-27 | details:GH#2. brands/page.tsx+channels/page.tsx 검색창+티어/세일 필터.
- [ ] T-20260227-001 | DB_01: 0결과 채널 원인 분류 + 재크롤 전략 | owner:codex-dev | priority:P1 | status:active | created:2026-02-27 | details:GH#3. 32개 편집샵 ssl/bot/selector/empty 분류. cleanup_mixed_brand_channel.py 실행.
- [ ] T-20260228-001 | CRAWLER_01: 자동 크롤 스케줄러 (일 1회) | owner:codex-dev | priority:P1 | status:active | created:2026-02-28 | details:GH#4. APScheduler. 03:00 제품크롤/07:00 환율/07:10 드롭. logs/ 자동 생성.
- [ ] T-20260228-002 | FRONTEND_04: 브랜드 상세 페이지 /brands/[slug] | owner:codex-dev | priority:P1 | status:active | created:2026-02-28 | details:GH#5. 제품 그리드+세일 토글. /brands/{slug}/products 엔드포인트 활용.
- [ ] T-20260228-003 | FRONTEND_05: 가격비교 페이지 가격 히스토리 차트 | owner:codex-dev | priority:P2 | status:active | created:2026-02-28 | details:GH#6. 백엔드 /products/price-history/{key} 신규 + recharts LineChart. 81k 이력 활용.
- [ ] T-20260228-004 | FRONTEND_06: 세일 페이지 무한스크롤 | owner:codex-dev | priority:P2 | status:active | created:2026-02-28 | details:GH#7. IntersectionObserver. 19,997개 세일 대응. offset 기반 추가 로드.
- [ ] T-20260227-002 | DB_02: DB 인덱스 최적화 + 쿼리 개선 | owner:codex-dev | priority:P2 | status:active | created:2026-02-27 | details:TASK_BRIEF_GEMINI_DB_SPRINT2.md. 4개 API 병목 인덱스 5개 이상 제안.
<!-- ACTIVE_TASKS_END -->

## Completed Tasks (Recent)
<!-- COMPLETED_TASKS_START -->
- [x] T-20260226-006 | Smoke test task | owner:codex-dev | priority:P2 | status:done | created:2026-02-26 | completed:2026-02-26 | details:Validated add-task/complete-task flow and log updates
- [x] T-20260226-001 | Issue 01 crawler quality improvement and full crawl run | owner:codex-dev | priority:P1 | status:done | created:2026-02-26 | completed:2026-02-26 | details:CODEX_ISSUE_01 and report completed
- [x] T-20260226-002 | Issue 02 brand tier classification pipeline | owner:codex-dev | priority:P1 | status:done | created:2026-02-26 | completed:2026-02-26 | details:data/brand_tiers.csv and scripts/classify_brands.py
- [x] T-20260226-003 | Issue 03 collaboration seed and hype scoring | owner:codex-dev | priority:P1 | status:done | created:2026-02-26 | completed:2026-02-26 | details:data/brand_collabs.csv and seed/recalculate scripts
- [x] T-20260226-004 | Issue 04 landscape API and quality report support | owner:codex-dev | priority:P1 | status:done | created:2026-02-26 | completed:2026-02-26 | details:channels landscape endpoint and data quality reporting
<!-- COMPLETED_TASKS_END -->
