# 에이전트 과업 지시서

PM/개발 작업 통제를 위한 단일 기준 문서입니다.

- PM 역할: `claude-pm`
- 개발 역할: `codex-dev`
- DB 역할: `codex-dev` (`gemini-db`는 2026-02-27부터 일시 중지)
- 자동 아카이브 트리거: 이 파일이 220줄을 초과할 때
- 자동 아카이브 목표: 오래된 완료 작업을 이동해 170줄까지 축소
- 문서 작성 원칙: **앞으로 이 파일의 신규/수정 내용은 한국어로 작성**

## 진행 중 작업
<!-- ACTIVE_TASKS_START -->
<!-- ACTIVE_TASKS_END -->

## 최근 완료 작업
<!-- COMPLETED_TASKS_START -->
- [x] T-20260228-014 | COLLAB_01: 협업 페이지 /collabs 타임라인 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#19 완료: `/collabs` 페이지 추가. 카테고리 필터, 카테고리별 하입 요약, 연도/하입 기반 타임라인 카드 구현.
- [x] T-20260228-013 | NEWS_02: 브랜드 소식 피드 프론트엔드 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#18 완료: 브랜드 상세(`/brands/[slug]`)에 브랜드 소식 피드 섹션 추가, `/news?brand_slug=` API 연동.
- [x] T-20260228-012 | NEWS_01: 패션 뉴스 RSS 크롤러 + 백엔드 API | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#17 완료: `scripts/crawl_news.py` RSS 수집기 추가, `/news` API 라우터 추가, 브랜드/채널 매칭 기반 저장/조회 구현.
- [x] T-20260228-011 | DEVEX_01: 원클릭 실행 환경 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#16 완료: `scripts/dev_oneclick.sh` + `Makefile` 추가, README에 원클릭 실행 가이드 반영.
- [x] T-20260228-010 | MAP_01: 세계지도 채널/브랜드 뷰 | owner:codex-dev | priority:P2 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#15 완료: `/map` 페이지 추가. 국가별 마커, 세일 채널 빨간색 강조, 클릭 사이드패널 구현.
- [x] T-20260228-009 | ADMIN_01: 운영관리 페이지 (백엔드 API + 프론트엔드) | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#14 완료: `/admin` API(`stats/channels-health/crawl-trigger`) + Bearer 인증 + 프론트 운영 대시보드 구성.
- [x] T-20260228-008 | CRAWLER_04: UA 회전 + ProductCrawler retry + playwright-stealth | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#13 완료: UA 풀 회전, ProductCrawler `tenacity` 재시도(3회), BaseCrawler stealth 훅, Bodega/SEVENSTORE `shopify-vendors` 전략 추가.
- [x] T-20260228-007 | CATEGORY_02: 프론트엔드 성별/카테고리/가격대 필터 UI | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#12 완료: `/sales` 필터 바(성별 탭, 카테고리 드롭다운, 최소/최대 가격) + 필터 연동 무한스크롤/카운트 동기화.
- [x] T-20260228-006 | CATEGORY_01: 카테고리·성별 DB 스키마 + 크롤러 자동분류 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#11 완료: `products.gender/subcategory` 마이그레이션 + Shopify `product_type` 키워드 매핑 + 제품 세일 API 필터링 추가.
- [x] T-20260227-006 | CRAWLER_03: EFFORTLESS/THEXSHOP 브랜드 셀렉터 재조사 | owner:codex-dev | priority:P2 | status:done | created:2026-02-27 | completed:2026-02-28 | details:GH#10 완료: 실페이지 기준 URL/셀렉터로 전략 갱신. 전체 재크롤 결과 EFFORTLESS 19개, THEXSHOP 193개(각 5개 이상 충족).
- [x] T-20260227-002 | DB_02: DB 인덱스 실제 적용 | owner:codex-dev | priority:P2 | status:done | created:2026-02-27 | completed:2026-02-27 | details:DB_02 완료: Alembic revision `7b6619f9d1ad`로 쿼리 인덱스 6개 적용 후 DB `head` 업그레이드.
- [x] T-20260228-005 | CRAWLER_02: 9개 selector_mismatch 채널 전략 수정 | owner:codex-dev | priority:P2 | status:done | created:2026-02-28 | completed:2026-02-27 | details:CRAWLER_02 완료: 커스텀 전략 0건 시 generic fallback 적용. 재크롤 개선(BIZZARE 35, ECRU 103, Kasina 199, EFFORTLESS 1, THEXSHOP 1).
- [x] T-20260227-003 | FRONTEND_02: 대시보드 검색 브랜드 자동완성 드롭다운 | owner:codex-dev | priority:P1 | status:done | created:2026-02-27 | completed:2026-02-28 | details:`SearchDropdown.tsx` 추가, `searchBrands()` 병렬 호출, 빌드 통과.
- [x] T-20260227-004 | FRONTEND_03: 브랜드/채널 페이지 클라이언트 사이드 검색 필터 | owner:codex-dev | priority:P1 | status:done | created:2026-02-27 | completed:2026-02-28 | details:`brands/channels` 검색창 + 티어/세일 필터 적용, 빌드 통과.
- [x] T-20260227-001 | DB_01: 0결과 채널 원인 분류 | owner:codex-dev | priority:P1 | status:done | created:2026-02-27 | completed:2026-02-28 | details:33개 채널 100% 라벨링, 인덱스 6개 제안, `agents/archive/crawl_audit/` 보고서 정리.
- [x] T-20260228-001 | CRAWLER_01: 자동 크롤 스케줄러 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:`scripts/scheduler.py`(APScheduler) 추가, 03:00/07:00/07:10 스케줄, `--dry-run` 검증 완료.
- [x] T-20260228-002 | FRONTEND_04: 브랜드 상세 페이지 /brands/[slug] | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:제품 그리드 + 세일 전용 토글, `/brands/{slug}/products` 연동, 빌드 통과.
- [x] T-20260228-003 | FRONTEND_05: 가격 히스토리 차트 | owner:codex-dev | priority:P2 | status:done | created:2026-02-28 | completed:2026-02-28 | details:백엔드 `/products/price-history/{key}` + 커스텀 SVG 라인차트(7일/30일/전체) 추가.
- [x] T-20260228-004 | FRONTEND_06: 세일 페이지 무한스크롤 | owner:codex-dev | priority:P2 | status:done | created:2026-02-28 | completed:2026-02-28 | details:`IntersectionObserver` 기반 60개 단위 추가 로드, 총 19,997개 데이터 대응.
- [x] T-20260226-006 | Smoke test task | owner:codex-dev | priority:P2 | status:done | created:2026-02-26 | completed:2026-02-26 | details:작업 추가/완료/로그 갱신 흐름 검증 완료.
- [x] T-20260226-001 | Issue 01 crawler quality improvement | owner:codex-dev | priority:P1 | status:done | created:2026-02-26 | completed:2026-02-26 | details:CODEX_ISSUE_01 완료.
- [x] T-20260226-002 | Issue 02 brand tier classification | owner:codex-dev | priority:P1 | status:done | created:2026-02-26 | completed:2026-02-26 | details:`brand_tiers.csv` + `classify_brands.py` 완료.
- [x] T-20260226-003 | Issue 03 collaboration seed + hype scoring | owner:codex-dev | priority:P1 | status:done | created:2026-02-26 | completed:2026-02-26 | details:`brand_collabs.csv` + 시드 스크립트 완료.
- [x] T-20260226-004 | Issue 04 landscape API | owner:codex-dev | priority:P1 | status:done | created:2026-02-26 | completed:2026-02-26 | details:채널 landscape API 엔드포인트 완료.
<!-- COMPLETED_TASKS_END -->
