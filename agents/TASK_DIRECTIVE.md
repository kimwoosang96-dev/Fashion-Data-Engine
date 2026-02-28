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
- [ ] T-20260228-028 | FIX_CHANNEL_BRANDS_01: 편집숍(edit-shop)이 brands 테이블에 잘못 분류된 21개 항목 수정 | owner:codex-dev | priority:P1 | status:todo | created:2026-02-28 | details:GH#31 — `cleanup_mixed_brand_channel.py`에 `--apply-with-products` 플래그 추가. 3단계: ①제품 brand_id→NULL ②channel_brands 삭제 ③brands 삭제. 대상: FASCINATE(3,991개), SOUTH STORE(2,054개) 등 21건. `make fix-brands` 추가.
- [ ] T-20260228-029 | FIX_NULL_BRAND_ID_01: brand_id NULL 제품 13,874개 채널 기반 재매핑 | owner:codex-dev | priority:P1 | status:todo | created:2026-02-28 | details:GH#32 — 신규 `scripts/fix_null_brand_id.py`. brand-store 채널 ↔ brands 이름 일치 31쌍으로 brand_id 할당. `--dry-run`/`--apply` 지원. GH#31 이후 실행. `make fix-null-brands` 추가.
<!-- ACTIVE_TASKS_END -->

## 최근 완료 작업
<!-- COMPLETED_TASKS_START -->
- [x] T-20260228-027 | BRAND_MECE_FIX_01: 브랜드 데이터 MECE 정제 스크립트 | owner:codex-dev | priority:P2 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#30 완료: `scripts/fix_brand_mece.py` 추가. 기본 dry-run/`--apply` 지원, `suspicion=high` 항목 및 안전 삭제 후보 출력.
- [x] T-20260228-026 | DASHBOARD_DEDUP_01: 대시보드 세일 제품 최저가 dedup 적용 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#29 완료: `/` 대시보드의 기본 세일 데이터 소스를 `getSaleHighlights()`로 전환하고 `SaleHighlight` 타입을 재사용하도록 반영.
- [x] T-20260228-025 | RECLASSIFY_01: 기존 제품 카테고리/성별 일괄 재분류 스크립트 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#28 완료: `scripts/reclassify_products.py` 구현(`classify_gender_and_subcategory()` 재사용, dry-run/apply), `make reclassify` 타깃 추가.
- [x] T-20260228-022 | CHANNEL_BRAND_AUDIT_01: 채널-브랜드 혼재 감사 도구 | owner:codex-dev | priority:P2 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#27 완료: `GET /admin/brand-channel-audit` 추가(유형 불일치/이상치 탐지), `/admin`에 혼재 감사 결과 UI 섹션 반영.
- [x] T-20260228-021 | COLLAB_ADMIN_01: Admin 협업 관리 (추가/삭제) | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#26 완료: `GET/POST/DELETE /admin/collabs` 추가, `/admin`에 협업 등록/삭제 UI 섹션 반영.
- [x] T-20260228-020 | NAV_BACK_01: compare 페이지 뒤로가기 브라우저 히스토리 기반 개선 | owner:codex-dev | priority:P2 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#25 완료: `compare/[key]/page.tsx` 상단 이동을 `router.back()` 기반 버튼으로 교체.
- [x] T-20260228-019 | SALE_DEDUP_01: 세일 제품 product_key 기준 최저가 중복 제거 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#24 완료: `get_sale_highlights()`를 product_key 기준 최저가 dedup으로 변경, `total_channels` 응답 필드와 `/sales`의 "N개 채널 최저가" 배지 반영.
- [x] T-20260228-018 | BRAND_DETAIL_01: 브랜드 상세 통합 뷰 완성 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#23 완료: `/brands/{slug}/collabs` API 추가, 브랜드 상세 페이지에 협업/디렉터/인스타그램/뉴스 통합 섹션 구성.
- [x] T-20260228-017 | INSTAGRAM_01: 브랜드/채널 인스타그램 URL 컬럼 + Admin UI | owner:codex-dev | priority:P2 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#22 완료: brands/channels `instagram_url` 컬럼+마이그레이션, Admin PATCH API, Admin 입력 UI, 브랜드/채널 화면 인스타그램 링크 표시.
- [x] T-20260228-016 | DIRECTOR_02: 크리에이티브 디렉터 프론트엔드 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#21 완료: `/directors` 목록 페이지 추가, Nav 메뉴 추가, `/brands/[slug]` 디렉터 섹션 연동.
- [x] T-20260228-015 | DIRECTOR_01: 크리에이티브 디렉터 DB 모델 + Admin 입력 폼 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#20 완료: `BrandDirector` 모델+Alembic, Admin GET/POST/DELETE API, `/admin` 디렉터 관리 섹션 추가.
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
