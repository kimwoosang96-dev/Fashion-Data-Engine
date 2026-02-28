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
- [ ] T-20260301-045 | DATA_AUDIT_01: Railway DB 전수 데이터 품질 감사 + 보고서 | owner:codex-dev | priority:P1 | status:todo | created:2026-03-01

  **목표**: Railway PostgreSQL DB를 전수 조사하여 현재 데이터 품질을 수치로 측정하고, 문제 항목과 개선 우선순위를 보고서로 출력한다.

  **산출물**: `scripts/data_audit.py` — dry-run 전용 리포트 스크립트 (DB를 수정하지 않음)

  ```
  사용법:
    uv run python scripts/data_audit.py                      # 로컬 SQLite
    DATABASE_URL=postgresql+asyncpg://... uv run python scripts/data_audit.py  # Railway
  ```

  **측정 항목 (전부 stdout에 섹션별 출력)**

  **[1] 채널 현황**
  - 전체 채널 수 / is_active=True 채널 수
  - 채널별 제품 수 (상위 20개 + 제품 0개인 채널 목록 전부)
  - 마지막 크롤 시각 (products.created_at 기준 채널별 MAX)
  - 7일 이상 미크롤 채널 목록

  **[2] 브랜드 매핑 품질**
  - 전체 제품 수 / brand_id NULL 제품 수 + 비율
  - channel_type별 brand_id NULL 현황 (edit-shop vs brand-store 분리)
  - brand_id NULL 상위 10개 채널 (제품 수 기준)
  - brand_id가 있는 브랜드 중 실제 products가 0개인 브랜드 수 (유령 브랜드)

  **[3] 가격 품질**
  - price_krw = 0 또는 NULL 제품 수
  - price_krw > 50,000,000 (5천만원 초과) 이상값 제품 수 + 샘플 5개
  - 통화(currency)별 제품 수 — 환율 미등록 통화 사용 현황 체크
    (exchange_rates 테이블과 조인하여 rate=NULL인 통화 목록 출력)
  - original_price_krw가 있는데 price_krw보다 낮은 역전 이상값 수

  **[4] 세일 / 신상품 현황**
  - is_sale=True 제품 수 + 비율
  - discount_rate 분포 (10%대, 20%대, 30%대, 40%+, NULL 각 수)
  - is_new=True 제품 수 + 비율
  - is_sale=True인데 discount_rate=NULL인 제품 수 (데이터 불일치)

  **[5] 활성/품절 현황**
  - is_active=True / False 수
  - archived_at IS NOT NULL 수 (정식 아카이브)
  - is_active=False인데 archived_at=NULL인 수 (누락 타임스탬프)

  **[6] PriceHistory 품질**
  - PriceHistory 총 레코드 수
  - PriceHistory가 0건인 제품 수 (크롤은 됐지만 이력 없음)
  - 제품당 평균 PriceHistory 레코드 수
  - 가장 오래된 PriceHistory 날짜 / 최신 날짜

  **[7] 환율 현황**
  - exchange_rates 테이블 전체 목록 (통화, rate, fetched_at)
  - products.currency 중 exchange_rates에 없는 통화 목록 + 해당 제품 수

  **[8] 전체 요약 (Summary)**
  - 총점 산정: 각 항목을 OK / WARNING / ERROR로 분류
  - WARNING/ERROR 항목 우선순위 목록 출력
  - AGENTS.md의 기준값 대비 수치 비교:
    - 채널: 159개 기준
    - 브랜드: ~2,561개 기준
    - 제품: ~26,000개 기준
    - brand_directors: 109개 기준 (Railway)

  **스크립트 구조 요건**
  - `AGENTS.md 스크립트 DB 접근 절대 규칙` 준수 (AsyncSessionLocal + init_db())
  - 섹션별 Rich 테이블로 출력 (rich.table.Table)
  - 실행 시간 측정 + 출력
  - 에러 발생 시 해당 섹션 SKIP하고 계속 진행 (전체 실패 방지)
  - 스크립트 종료 시 WARNING/ERROR 총 개수 반환 (exit code = 0 항상)

  **실행 후 보고 방법**
  - 스크립트 실행 결과 전체를 `WORK_LOG.md`에 append
  - 발견된 주요 문제점을 `agents/WORK_LOG.md`에 요약 기록

  **DoD**
  - [ ] `scripts/data_audit.py --help` 정상 동작
  - [ ] Railway DB 대상 실행 완료 (8개 섹션 전부 출력)
  - [ ] WARNING/ERROR 항목 목록 Summary 출력
  - [ ] WORK_LOG.md에 실행 결과 요약 기록
<!-- ACTIVE_TASKS_END -->

## 최근 완료 작업
<!-- COMPLETED_TASKS_START -->
- [x] T-20260301-044 | DIRECTOR_PAGE_01: 디렉터 페이지 브랜드 중심 UI 재구성 | owner:codex-dev | priority:P2 | status:done | created:2026-03-01 | completed:2026-03-01 | details:`GET /directors/by-brand` 엔드포인트 및 `DirectorsByBrand` 스키마 추가, 프론트 `/directors`를 브랜드 섹션 중심 UI로 재구성(현행 디렉터 우선/현재 배지/브랜드 헤더 링크/브랜드·디렉터 검색 필터). `getDirectorsByBrand()` API/타입 연동 완료.
- [x] T-20260301-043 | FIX_MULTI_CHANNEL_01: 경쟁 제품 페이지 결과 부족 원인 수정 | owner:codex-dev | priority:P1 | status:done | created:2026-03-01 | completed:2026-03-01 | details:`get_multi_channel_products()`를 latest 가격 `LEFT JOIN` 집계로 변경해 PriceHistory 일부 누락으로 인한 product_key 탈락을 완화. `channel_count/min_price_krw/max_price_krw/price_spread_krw` 유지 검증, 로컬 기준 `min_channels=2` 조회 결과 200건 확인.
- [x] T-20260301-042 | FIX_CURRENCY_01: 미지원 통화 환율 보완 + Hamcus HKD 감지 수정 | owner:codex-dev | priority:P1 | status:done | created:2026-03-01 | completed:2026-03-01 | details:`update_exchange_rates.py` 통화 확대(DKK/SEK/SGD/CAD/AUD/TWD/CNY), `product_crawler.py`에 hk/sg/ca 서브도메인 통화 매핑 및 unknown→USD warning 추가, `get_rate_to_krw()` 미등록 통화 warning 추가, `docs/DEPLOYMENT.md`에 초기 배포 후 환율 갱신 섹션 반영. 실행 검증 시 추가 통화 환율 저장 및 Hamcus=HKD 감지 확인.
- [x] T-20260301-041 | CHANNEL_STRATEGY_01: 편집샵 크롤 전략 + product_key→brand_id 재매핑 | owner:codex-dev | priority:P1 | status:done | created:2026-03-01 | completed:2026-03-01 | details:GH#41 완료: `scripts/remap_product_brands.py` 추가(dry-run/apply) 및 적용으로 edit-shop NULL `brand_id` 2,423건 복구(13,642→11,219). `products.vendor` 컬럼 Alembic(`a7c9d1e3f5b7_add_vendor_to_products`) 추가 후 `upsert_product()`에서 vendor 저장 반영, Makefile `remap-product-brands`/`remap-product-brands-apply` 타깃 추가.
- [x] T-20260228-039 | FAKE_BRAND_PURGE_01: 브랜드 테이블 가짜 항목 정리 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#40 완료: `scripts/purge_fake_brands.py` 추가(dry-run/apply), `brand_crawler.py`에 `is_fake_brand()` 필터 추가, Makefile `purge-fake-brands`/`purge-fake-brands-apply` 타겟 추가. 적용 결과 fake 416건 삭제, channel_brands 397건 삭제, products.brand_id NULL 402건 처리(Archive id=1199 포함).
- [x] T-20260228-038 | ENRICH_01: 브랜드 인리치먼트 — description_ko, origin_country, 디렉터 이름 정정 | owner:codex-dev | priority:P2 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#39 완료: `brand_directors.csv` 실명 정정 + `source_url/verified_at` 컬럼 반영, `seed_brands_luxury.py`로 누락 럭셔리 9개 시드 적용, `brand_enrichment.csv`(24행) + `enrich_brands.py`로 브랜드 소개/국가/공식/인스타 인리치 적용, Makefile `seed-brands-luxury`/`enrich-brands` 계열 타겟 추가 및 검증.
- [x] T-20260228-037 | BRAND_DIRECTOR_SEED_01: 주요 브랜드 크리에이티브 디렉터 CSV 시드 | owner:codex-dev | priority:P2 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#38 완료: `data/brand_directors.csv`(32행) 추가, `scripts/seed_directors.py`(dry-run/apply) 구현, `make seed-directors`/`seed-directors-apply` 타겟 추가. 로컬 DB apply 결과 21건 생성(미존재 slug 11건 스킵) 확인.
- [x] T-20260228-036 | SCHEDULER_WORKER_01: Railway Worker 자동 크롤 설정 + Makefile 정비 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#37 완료: Makefile Python 실행을 `uv run python`으로 정리, `crawl/crawl-news/update-rates/scheduler-dry/scheduler` 타겟 추가, `docs/DEPLOYMENT.md`에 Railway Worker 설정 문서화, `make scheduler-dry` 정상 검증.
- [x] T-20260228-034 | CLOUD_MIGRATION_01: Railway + Vercel 클라우드 전환 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#36 완료: Alembic DB URL을 settings 기반으로 정렬, CORS origin 환경변수화, `/health` 200 검증, `railway.json`/`frontend/vercel.json` 추가, `scripts/migrate_sqlite_to_pg.py` 추가(시드 only, products 재크롤 전제), `.env.example` 갱신.
- [x] T-20260228-033 | COMPETE_PAGE_01: 멀티채널 경쟁 제품 페이지 | owner:codex-dev | priority:P2 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#35 완료: `get_multi_channel_products()` + `GET /products/multi-channel` API 연결, `frontend/src/app/compete/page.tsx` 신규 페이지 구현, Nav "경쟁" 메뉴 추가.
- [x] T-20260228-032 | ARCHIVE_01: 품절 제품 아카이브 처리 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#34 완료: `products.archived_at` 마이그레이션 추가, `upsert_product()` 품절 전환/복구 시 `archived_at` 반영, 주요 제품 목록 쿼리에 `is_active==True` 필터 적용, `GET /products/archive` 엔드포인트 추가.
- [x] T-20260228-030 | OFFICIAL_CHANNEL_01: 비교 페이지 공식 채널 구분 배지 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#33 완료: `get_price_comparison()`에 Brand LEFT JOIN 추가, `is_official`/`channel_type` 필드 응답 확장, Compare 페이지에 "공식" 배지 및 채널 타입 표시 UI 반영.
- [x] T-20260228-029 | FIX_NULL_BRAND_ID_01: brand_id NULL 제품 13,874개 채널 기반 재매핑 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#32 완료: `scripts/fix_null_brand_id.py` 추가(dry-run/apply). brand-store↔brand 매칭 31쌍(보수적 ambiguous 해소 1건) 기준으로 NULL brand_id 재매핑 지원. `make fix-null-brands` 추가.
- [x] T-20260228-028 | FIX_CHANNEL_BRANDS_01: 편집숍(edit-shop)이 brands 테이블에 잘못 분류된 21개 항목 수정 | owner:codex-dev | priority:P1 | status:done | created:2026-02-28 | completed:2026-02-28 | details:GH#31 완료: `cleanup_mixed_brand_channel.py`에 `--apply-with-products` 플래그 추가(①products.brand_id=NULL ②channel_brands 삭제 ③brands 삭제), `make fix-brands` 추가.
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
