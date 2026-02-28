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
- [ ] T-20260301-042 | FIX_CURRENCY_01: 미지원 통화 환율 보완 + Hamcus HKD 감지 수정 | owner:codex-dev | priority:P1 | status:todo | created:2026-03-01
  **배경**: `update_exchange_rates.py`의 `CURRENCIES = ["USD", "JPY", "EUR", "GBP", "HKD"]`만 업데이트 중. `product_crawler.py`의 `COUNTRY_CURRENCY`에는 DKK/SEK/SGD/CAD/TWD/CNY가 있어서 이 통화로 감지된 제품은 환율 없이 `get_rate_to_krw()` fallback 1.0 반환 → 가격이 원화처럼 취급됨. Hamcus는 HK 채널인데 `SUBDOMAIN_CURRENCY`에 `"hk"` 없어서 USD fallback 가능성 있음.
  **Step 1 — `scripts/update_exchange_rates.py`**
  - `CURRENCIES` 리스트에 추가: `"DKK", "SEK", "SGD", "CAD", "AUD"` (COUNTRY_CURRENCY 전체 커버)
  - TWD, CNY는 선택적 추가 (오픈 API에서 제공 시)
  **Step 2 — `src/fashion_engine/crawler/product_crawler.py`**
  - `SUBDOMAIN_CURRENCY`에 `"hk": "HKD"`, `"sg": "SGD"`, `"ca": "CAD"` 추가
  - `_infer_currency()` fallback이 USD인 경우 logger.warning으로 "알 수 없는 통화 → USD 가정" 로그 추가
  **Step 3 — `src/fashion_engine/services/product_service.py`**
  - `get_rate_to_krw()`에서 `row is None`일 때 `logger.warning(f"환율 미등록: {currency}, fallback 1.0")` 추가
  **Step 4 — Railway 환율 갱신 가이드**
  - `Makefile`에 `update-rates` 타겟 이미 있으면 활용, 없으면 추가
  - `docs/DEPLOYMENT.md`에 "초기 배포 후 환율 업데이트 필수" 섹션 추가
  **DoD**
  - [ ] `update_exchange_rates.py` 실행 후 DKK/SEK/SGD/CAD/AUD 환율도 DB에 저장됨
  - [ ] Hamcus 채널 크롤 시 currency=HKD로 감지 (또는 최소한 USD fallback 시 경고 로그)
  - [ ] 환율 미등록 통화 사용 시 WARNING 로그 출력

- [ ] T-20260301-043 | FIX_MULTI_CHANNEL_01: 경쟁 제품 페이지 결과 부족 원인 수정 | owner:codex-dev | priority:P1 | status:todo | created:2026-03-01
  **배경**: `get_multi_channel_products()` 함수가 `PriceHistory` INNER JOIN 사용 → PriceHistory 레코드가 없는 제품은 집계에서 제외됨. Railway DB에서는 크롤 이후 PriceHistory가 충분히 쌓이지 않은 제품이 많아 경쟁 제품이 3개만 표시됨. `Product.price_krw`는 upsert 시 항상 저장되므로 이를 직접 사용해야 함.
  **현재 코드 문제** (`src/fashion_engine/services/product_service.py`):
  ```python
  # ❌ PriceHistory INNER JOIN → PriceHistory 없는 제품 누락
  latest_sub = select(PriceHistory.product_id, func.max(PriceHistory.crawled_at))...
  .join(latest_sub, Product.id == latest_sub.c.product_id)  # ← INNER JOIN
  .join(PriceHistory, ...)
  ```
  **수정 방향** — PriceHistory JOIN 제거, Product.price_krw 직접 사용:
  ```python
  # ✅ Product 테이블만 사용 — price_krw, original_price_krw 직접 집계
  rows = await db.execute(
      select(
          Product.product_key,
          func.min(Product.name).label("product_name"),
          func.min(Product.image_url).label("image_url"),
          func.count(func.distinct(Product.channel_id)).label("channel_count"),
          func.min(Product.price_krw).label("min_price"),
          func.max(Product.price_krw).label("max_price"),
      )
      .where(
          Product.product_key.isnot(None),
          Product.is_active == True,
          Product.price_krw.isnot(None),
          Product.price_krw > 0,
      )
      .group_by(Product.product_key)
      .having(func.count(func.distinct(Product.channel_id)) >= min_channels)
      .order_by(
          desc(func.count(func.distinct(Product.channel_id))),
          desc(func.max(Product.price_krw) - func.min(Product.price_krw)),
      )
      .limit(limit).offset(offset)
  )
  ```
  **영향 파일**
  - `src/fashion_engine/services/product_service.py` — `get_multi_channel_products()` 수정
  **DoD**
  - [ ] `GET /products/multi-channel` 응답에 30개 이상 제품 포함 (Railway 기준)
  - [ ] `channel_count`, `min_price_krw`, `max_price_krw`, `price_spread_krw` 정상 반환
  - [ ] `/compete` 페이지 정상 표시

- [ ] T-20260301-044 | DIRECTOR_PAGE_01: 디렉터 페이지 브랜드 중심 UI 재구성 | owner:codex-dev | priority:P2 | status:todo | created:2026-03-01
  **배경**: 현재 `/directors` 페이지는 디렉터 개인 카드를 나열 (브랜드 구분 없음). 사용자가 원하는 것은 브랜드별 섹션 구성 + 현행 디렉터(end_year IS NULL) 우선 표시.
  **백엔드 — `src/fashion_engine/api/directors.py`**
  - 신규 엔드포인트 추가: `GET /directors/by-brand`
    - 브랜드별로 그룹핑된 데이터 반환
    - 각 브랜드 내: 현행 디렉터(end_year IS NULL) 먼저, 이후 역임 디렉터(최근 연도순)
    - 응답 스키마:
    ```python
    class DirectorsByBrand(BaseModel):
        brand_slug: str
        brand_name: str
        current_directors: list[BrandDirectorOut]   # end_year IS NULL
        past_directors: list[BrandDirectorOut]       # end_year IS NOT NULL, 최근순
    ```
    - 쿼리: `ORDER BY Brand.name ASC, BrandDirector.end_year DESC NULLS FIRST, BrandDirector.start_year DESC`
  **프론트엔드 — `frontend/src/app/directors/page.tsx`**
  - API 호출: `getDirectorsByBrand()` (신규, `GET /directors/by-brand`)
  - UI 구조:
    ```
    [브랜드 헤더] LOUIS VUITTON
      ├── [현행] Nicolas Ghesquière — Creative Director, 2013~현재
      └── [역임] Marc Jacobs — Creative Director, 1997~2013
    [브랜드 헤더] DIOR
      ├── [현행] Maria Grazia Chiuri — Creative Director, 2016~현재
      └── ...
    ```
    - 현행 디렉터: 진한 텍스트 + "현재" 뱃지 (green)
    - 역임 디렉터: 회색 텍스트, 기본 접히지 않음 (전부 표시)
    - 브랜드 헤더 클릭 → `/brands/[slug]` 이동
    - 검색창: 브랜드명 또는 디렉터명으로 필터 (기존 유지)
  **`frontend/src/lib/api.ts`**
  - `getDirectorsByBrand()` 함수 추가: `GET /directors/by-brand`
  **`frontend/src/lib/types.ts`**
  - `DirectorsByBrand` 타입 추가
  **`src/fashion_engine/api/schemas.py`**
  - `DirectorsByBrand` Pydantic 스키마 추가
  **영향 파일**
  - `src/fashion_engine/api/directors.py` — `/by-brand` 엔드포인트 추가
  - `src/fashion_engine/api/schemas.py` — `DirectorsByBrand` 스키마
  - `frontend/src/app/directors/page.tsx` — 브랜드 섹션 UI로 재구성
  - `frontend/src/lib/api.ts` — `getDirectorsByBrand()` 추가
  - `frontend/src/lib/types.ts` — `DirectorsByBrand` 타입
  **DoD**
  - [ ] `GET /directors/by-brand` 정상 응답 (브랜드별 그룹핑, 현행 먼저)
  - [ ] `/directors` 페이지에서 브랜드 섹션 구조 표시
  - [ ] 현행 디렉터(end_year null)가 각 브랜드 섹션 최상단에 표시
  - [ ] 브랜드 헤더 클릭 → `/brands/[slug]` 이동
  - [ ] `npm run build` 타입 에러 없음
<!-- ACTIVE_TASKS_END -->

## 최근 완료 작업
<!-- COMPLETED_TASKS_START -->
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
