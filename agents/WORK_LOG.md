# 에이전트 작업 로그

추가 전용 실행 로그. 모든 에이전트가 기록합니다.

> **언어 규칙**: message 필드는 **한국어**로 작성합니다.

형식:
- `YYYY-MM-DD HH:MM:SS | agent:<에이전트ID> | task:<태스크ID|-> | action:<액션> | message:<요약>`

## 기록

- 2026-03-08 22:35:00 | agent:codex-dev | task:T-20260308-134 | action:complete | message:FEED_WEBSOCKET_01 완료: `/ws/feed` WebSocket, `/internal/broadcast`, crawler/watch_agent/feed ingest 브로드캐스트 클라이언트, `/feed` 페이지 재연결 로직을 추가했다. `compileall`, `next build`, 라우트 등록 확인(`/ws/feed`, `/internal/broadcast`)까지 마쳤다.
- 2026-03-08 22:36:00 | agent:codex-dev | task:T-20260308-135 | action:complete | message:BRAND_SALE_INTEL_API_01 완료: `/api/v2/brands/{slug}/sale-intel`를 추가해 현재 세일 수, 최대 할인율, 세일 채널 목록, 월별 세일 이력, typical sale months를 제공하도록 구현했다.
- 2026-03-08 22:37:00 | agent:codex-dev | task:T-20260308-130 | action:log | message:SEMANTIC_SEARCH_01 코드 반영: `/api/v2/search?mode=semantic`, `search_service_v2.py`, `generate_embeddings.py`, Alembic `4b5c6d7e8f9a`를 추가했다. 남은 것은 Railway PostgreSQL vector 확장과 sentence-transformers 설치/임베딩 백필 운영 검증이다.
- 2026-03-08 22:38:00 | agent:codex-dev | task:T-20260308-131 | action:log | message:REDIS_CACHE_LAYER_01 코드 반영: `cache.py`, `/api/v2/*`, `/products/sales` TTL 캐시, 크롤 post-commit cache prefix invalidation을 추가했다. Redis 서비스/패키지 설치와 실측 검증은 남아 active로 유지한다.
- 2026-03-08 22:39:00 | agent:codex-dev | task:T-20260308-132 | action:log | message:CROSS_CHANNEL_PRICE_HISTORY_UI_01 부분 반영: `/api/v2/price-history/{product_key}` 백엔드와 프론트 타입/api 함수는 추가했다. compare 페이지 차트 UI는 다음 리뷰 후 이어서 붙인다.
- 2026-03-08 22:40:00 | agent:codex-dev | task:T-20260308-133 | action:log | message:MCP_HARDENING_01 코드 반영: `/mcp` 인증, 메모리 rate limit, resources, `get_brand_sale_status` tool, `mcp.json`을 추가했다. 실제 Claude Desktop 연결 및 transport 정합성 검증은 남아 active로 유지한다.
- 2026-03-08 22:41:00 | agent:codex-dev | task:T-20260308-122 | action:log | message:Claude 리뷰 반영: `scripts/reactivate_channels.py`에 script 디렉터리 sys.path 삽입을 추가해 Railway 실행 경로에 따라 `channel_probe` import가 깨질 수 있는 문제를 수정했다.
- 2026-03-08 15:05:00 | agent:codex-dev | task:T-20260308-117 | action:complete | message:CHANNEL_YIELD_MONITOR_01 완료: `channel_crawl_stats` 모델과 Alembic revision `3a4b5c6d7e8f`를 추가하고, `crawl_products.py`가 채널별 yield와 parse method를 크롤 직후 기록하도록 연결했다. `scripts/auto_switch_parser.py` 및 scheduler 일요일 09:30 잡까지 반영했다.
- 2026-03-08 15:06:00 | agent:codex-dev | task:T-20260308-118 | action:complete | message:SALE_DETECTION_FIX_01 완료: WooCommerce `regular_price > price` 세일 판정을 재확인하고, Cafe24의 추가 CSS selector 및 정가/소비자가 텍스트 파싱을 반영했다. `scripts/verify_sale_detection.py`로 플랫폼별 세일 감지 수를 점검할 수 있다.
- 2026-03-08 15:07:00 | agent:codex-dev | task:T-20260308-119 | action:complete | message:NORMALIZED_KEY_REFRESH_01 완료: normalized key 생성 시 시즌 코드/색상/불용어를 제거하고 유사도 기반 confidence를 재계산하도록 개선했다. `product_catalog.channel_count` 집계를 추가하고 `scripts/improve_normalized_key.py`로 저신뢰 제품 재처리 경로를 구현했다.
- 2026-03-08 15:08:00 | agent:codex-dev | task:T-20260308-120 | action:complete | message:IMAGE_URL_VERIFY_01 완료: `products.image_verified_at` 컬럼과 `scripts/verify_image_urls.py`를 추가해 HEAD/GET 기반 이미지 검증, broken image NULL 처리, 30일 재검증, 재크롤 대상 출력 경로를 구현했다. scheduler 토요일 05:00 잡도 연결했다.
- 2026-03-08 15:09:00 | agent:codex-dev | task:T-20260308-121 | action:complete | message:SHOPIFY_CATALOG_ENRICH_01 완료: Shopify `/collections.json` 힌트와 tag/title/product_type 분석을 이용해 `gender/subcategory/is_new` 추론을 강화했다. `scripts/reclassify_from_shopify_tags.py`로 기존 Shopify 상품 재분류 배치도 추가했다.
- 2026-03-08 15:10:00 | agent:codex-dev | task:T-20260308-122 | action:complete | message:CHANNEL_REACTIVATION_01 완료: `channels.last_probe_at` 컬럼과 `scripts/reactivate_channels.py`를 추가해 비활성 채널 재probe 후 자동 복구 흐름을 만들고, Discord 복구 알림과 scheduler 화요일 04:00 잡을 연결했다.
- 2026-03-08 14:20:00 | agent:codex-dev | task:T-20260308-111 | action:complete | message:SEARCH_AUTOCOMPLETE_01 완료: `/products/search/suggestions` API와 대시보드 자동완성 드롭다운을 debounce/키보드 탐색 방식으로 구현하고 프론트 빌드 검증을 마쳤다.
- 2026-03-08 14:21:00 | agent:codex-dev | task:T-20260308-112 | action:complete | message:DROPS_CALENDAR_01 완료: `/drops/calendar` API와 `/drops/calendar` 페이지를 추가해 intel drops/new_drop 이벤트를 월별 달력과 모바일 목록으로 시각화했다.
- 2026-03-08 14:22:00 | agent:codex-dev | task:T-20260308-113 | action:complete | message:BRAND_SALE_HEATMAP_01 완료: `/brands/heatmap` API와 히트맵 페이지를 추가하고 티어/국가 필터, hover 툴팁, 상위 30×20 제한을 반영했다.
- 2026-03-08 14:23:00 | agent:codex-dev | task:T-20260308-114 | action:complete | message:ADMIN_INTEL_DASHBOARD_01 완료: `/admin/intel-status`와 `/admin/crawl-runs`를 확장해 activity_feed/GPT/OAuth 지표를 추가하고 Admin UI에 카드와 분포 막대를 반영했다.
- 2026-03-08 14:24:00 | agent:codex-dev | task:T-20260308-115 | action:complete | message:COVERAGE_REPORT_01 완료: `scripts/coverage_report.py`, Discord 리포트 포맷, scheduler 주간 잡을 추가했다. `scheduler.py --dry-run` 검증은 성공했고 로컬 SQLite smoke test는 기존 DB lock 때문에 제한됐다.
- 2026-03-08 14:25:00 | agent:codex-dev | task:T-20260308-110 | action:log | message:GPT_ACTIONS_OAUTH_VERIFY_01은 코드 준비 완료 상태다. Custom GPT Actions UI와 Railway 운영 주소에서 실제 승인/토큰 교환/ingest 기록 생성은 수동 검증이 남아 active로 유지한다.
- 2026-03-08 14:26:00 | agent:codex-dev | task:T-20260308-116 | action:log | message:PRODUCT_PRICE_ALERT_01은 제품별 target_price와 웹 푸시 실수신 검증이 필요하다. 현재 PWA_PUSH_01 실브라우저 검증이 선행되어야 하므로 이번 턴에는 착수하지 않고 의존성 상태로 남긴다.
- 2026-03-08 02:24:00 | agent:codex-dev | task:T-20260308-105 | action:log | message:PWA_PUSH_01 구현분 반영: pywebpush 의존성, push_subscriptions 모델/API, service worker/manifest, /feed 구독 UI, watch_agent 푸시 발송 경로 추가. 브라우저 실수신 검증은 VAPID 키 설정 후 남음.
- 2026-03-08 01:12:00 | agent:codex-dev | task:T-20260308-104 | action:complete | message:WEBHOOK_COMMUNITY_01 완료: Shopify webhook HMAC 검증 엔드포인트와 채널별 webhook secret 저장 경로를 추가하고, DCinside HTML 파서 기반 커뮤니티 수집 스크립트를 구현했다.
- 2026-03-08 00:56:00 | agent:codex-dev | task:T-20260308-103 | action:complete | message:FAST_POLL_SCHEDULER_01 완료: channels.poll_priority 컬럼, crawl_products `--fast-poll/--new-only/--dry-run`, scheduler 2시간/1시간 주기, admin 우선순위 조정 UI/API를 추가하고 dry-run/build 검증을 마쳤다.
- 2026-03-08 11:35:00 | agent:codex-dev | task:T-20260308-100 | action:complete | message:PRODUCT_PRICE_SNAPSHOT_01 완료: products 현재가 스냅샷 컬럼과 백필 Alembic 추가, 크롤 저장 및 세일/비교/랭킹 조회를 products.price_* 기준으로 전환.
- 2026-03-08 11:35:00 | agent:codex-dev | task:T-20260308-101 | action:complete | message:ACTIVITY_FEED_01 완료: activity_feed 모델/마이그레이션 추가, `/feed` API를 activity_feed 실데이터 기반으로 전환.
- 2026-03-08 11:35:00 | agent:codex-dev | task:T-20260308-102 | action:complete | message:WATCH_AGENT_01 완료: watch_agent를 추가해 채널 크롤 직후 sale_start/new_drop/price_cut 이벤트를 activity_feed에 자동 적재하고 `--no-watch` 플래그를 연결.
- 2026-02-26 23:30:00 | agent:codex-dev | task:T-20260226-001 | action:complete | message:Issue 01 완료 및 보고서 작성
- 2026-02-26 23:30:30 | agent:codex-dev | task:T-20260226-002 | action:complete | message:Issue 02 완료 및 검증
- 2026-02-26 23:31:00 | agent:codex-dev | task:T-20260226-003 | action:complete | message:Issue 03 완료 및 검증
- 2026-02-26 23:31:30 | agent:codex-dev | task:T-20260226-004 | action:complete | message:Issue 04 완료 및 보고서 업데이트

- 2026-02-26 23:39:37 | agent:claude-pm | task:T-20260226-005 | action:add-task | message:태스크 생성: PM-개발자 핸드셰이크 프로토콜 정의

- 2026-02-26 23:39:53 | agent:codex-dev | task:T-20260226-006 | action:add-task | message:태스크 생성: 스모크 테스트

- 2026-02-26 23:40:02 | agent:codex-dev | task:T-20260226-005 | action:log | message:협업 시스템 스캐폴드 완료, PM 검토 대기

- 2026-02-26 23:40:02 | agent:codex-dev | task:T-20260226-006 | action:complete | message:add-task/complete-task 흐름 및 로그 업데이트 검증 완료

- 2026-02-26 23:44:52 | agent:codex-dev | task:T-20260226-005 | action:log | message:Codex 이슈 문서를 agents 아카이브로 정리, 연관검색어 기능 추가 (API + 대시보드 칩)

- 2026-02-26 23:59:26 | agent:codex-dev | task:T-20260226-005 | action:log | message:대시보드 통계 카드 클릭 가능하도록 구현 (/sales, /channels, /brands 연결), 세일율/신상품 하이라이트 API 추가

- 2026-02-27 00:04:47 | agent:codex-dev | task:T-20260226-005 | action:log | message:크롤 파이프라인에 브랜드-채널 혼재 방지 로직 추가, 혼재 브랜드 3행 안전 삭제 완료

- 2026-02-27 00:09:12 | agent:claude-pm | task:T-20260227-001 | action:log | message:Gemini DB 역할 배정 및 DB 감사 태스크 브리핑 발행

- 2026-02-27 00:10:58 | agent:claude-pm | task:T-20260227-001 | action:log | message:Gemini DB Sprint1 실행 과업지시서 발행 (DoD 및 결과물 포함)

- 2026-02-27 00:18:33 | agent:claude-pm | task:T-20260227-002 | action:add-task | message:태스크 생성: DB 운영 준비 스프린트 (커버리지 + 정합성 + 성능)

- 2026-02-27 00:18:59 | agent:claude-pm | task:T-20260227-002 | action:log | message:Gemini DB Sprint2 과업지시서 발행 (ETA, 결과물, DoD 포함)

- 2026-02-27 00:22:29 | agent:claude-pm | task:T-20260227-002 | action:log | message:gemini-db 일시 중단, DB 태스크 codex-dev로 재배정

- 2026-02-27 00:22:29 | agent:codex-dev | task:T-20260227-001 | action:log | message:브랜드-채널 혼재 정책 업데이트: 자체 판매페이지 보유 브랜드 유지, 현재 채널 기준으로 충돌 필터 범위 축소

- 2026-02-27 00:47:58 | agent:codex-dev | task:T-20260227-001 | action:log | message:edit-shop 전체 재크롤 완료 (80개 채널). DNS/SSL 실패만 남음. channel_brand 링크 갱신 및 혼재 정제 후보 재확인

- 2026-02-27 01:15:50 | agent:codex-dev | task:T-20260227-001 | action:log | message:Dover/Kerouac/Tune 채널별 fallback URL 추가, Shopify API 실패 처리 강화. 전체 재크롤 오류 없이 완료

- 2026-02-27 01:57:17 | agent:codex-dev | task:T-20260227-003 | action:log | message:FRONTEND_02 완료: 대시보드 통합 검색 드롭다운 (브랜드/제품 병렬 호출, 외부 클릭 닫기)

- 2026-02-27 01:57:17 | agent:codex-dev | task:T-20260227-004 | action:log | message:FRONTEND_03 완료: 브랜드/채널 페이지 클라이언트사이드 필터 (검색어+티어, 검색어+세일만)

- 2026-02-27 01:57:17 | agent:codex-dev | task:T-20260228-003 | action:log | message:FRONTEND_05 완료: 가격 히스토리 API + 가격비교 페이지 추이 차트 (7/30/전체 범위)

- 2026-02-27 01:57:17 | agent:codex-dev | task:T-20260228-002 | action:log | message:FRONTEND_04 완료: 브랜드 상세 페이지 /brands/[slug] (통계, 세일만 토글, 제품 그리드)

- 2026-02-27 01:57:17 | agent:codex-dev | task:T-20260228-004 | action:log | message:FRONTEND_06 완료: /sales 무한스크롤 + 세일 제품 총 수 헤더

- 2026-02-27 01:57:17 | agent:codex-dev | task:T-20260227-001 | action:log | message:DB_01 보고서 업데이트 완료: 0결과 채널 100% 라벨링, 인덱스 제안 문서화

- 2026-02-27 01:57:17 | agent:codex-dev | task:T-20260228-001 | action:log | message:CRAWLER_01 완료: APScheduler 기반 일별 스케줄러 스크립트 추가, dry-run 검증 완료

- 2026-02-27 02:35:40 | agent:codex-dev | task:T-20260227-002 | action:complete | message:DB_02 완료: Alembic revision 7b6619f9d1ad로 6개 쿼리 인덱스 적용, DB head로 업그레이드

- 2026-02-27 02:35:40 | agent:codex-dev | task:T-20260228-005 | action:complete | message:CRAWLER_02 완료: 커스텀 전략 결과 0건 시 제네릭 전략 fallback 적용. 재크롤 결과 개선 (BIZZARE 35, ECRU 103, Kasina 199, EFFORTLESS 1, THEXSHOP 1)

- 2026-02-27 02:35:59 | agent:codex-dev | task:T-20260227-002 | action:complete | message:DB_02 완료: Alembic revision 7b6619f9d1ad로 6개 쿼리 인덱스 적용, DB head로 업그레이드

- 2026-02-28 06:47:52 | agent:codex-dev | task:T-20260227-006 | action:complete | message:GH#10 완료: EFFORTLESS/THEXSHOP 브랜드 셀렉터 업데이트 및 전체 재크롤 검증 (EFFORTLESS 19개, THEXSHOP 193개)
- 2026-02-28 07:03:09 | agent:codex-dev | task:T-20260228-006 | action:complete | message:GH#11 완료: products.gender/subcategory 마이그레이션, 크롤러 자동분류, products API 필터 추가.
- 2026-02-28 07:03:09 | agent:codex-dev | task:T-20260228-007 | action:complete | message:GH#12 완료: /sales 성별/카테고리/가격대 필터 바 + 필터 연동 무한스크롤 반영.
- 2026-02-28 07:03:09 | agent:codex-dev | task:T-20260228-008 | action:complete | message:GH#13 완료: UA 회전, ProductCrawler retry(3), stealth hook, Bodega/SEVENSTORE shopify-vendors 전략 추가.
- 2026-02-28 07:03:09 | agent:codex-dev | task:T-20260228-009 | action:complete | message:GH#14 완료: Bearer 인증 admin API + /admin 운영관리 페이지(현황/헬스/크롤제어/환율).
- 2026-02-28 07:03:09 | agent:codex-dev | task:T-20260228-010 | action:complete | message:GH#15 완료: /map 세계지도(국가 마커, 세일 채널 빨간 마커, 클릭 사이드패널).

- 2026-02-28 07:10:00 | agent:claude-pm | task:T-20260228-011 | action:add-task | message:태스크 생성: DEVEX_01 원클릭 실행 환경 (GH#16)
- 2026-02-28 07:10:00 | agent:claude-pm | task:T-20260228-012 | action:add-task | message:태스크 생성: NEWS_01 패션 뉴스 RSS 크롤러 + 백엔드 API (GH#17)
- 2026-02-28 07:10:00 | agent:claude-pm | task:T-20260228-013 | action:add-task | message:태스크 생성: NEWS_02 브랜드 소식 피드 프론트엔드 (GH#18)
- 2026-02-28 07:10:00 | agent:claude-pm | task:T-20260228-014 | action:add-task | message:태스크 생성: COLLAB_01 협업 페이지 /collabs 타임라인 (GH#19)
- 2026-02-28 07:23:43 | agent:codex-dev | task:T-20260228-011 | action:complete | message:GH#16 완료: 원클릭 실행 스크립트(`scripts/dev_oneclick.sh`)와 `Makefile` 추가, README 실행 가이드 반영.
- 2026-02-28 07:23:43 | agent:codex-dev | task:T-20260228-012 | action:complete | message:GH#17 완료: RSS 뉴스 수집 스크립트(`scripts/crawl_news.py`)와 `/news` 백엔드 API 추가.
- 2026-02-28 07:23:43 | agent:codex-dev | task:T-20260228-013 | action:complete | message:GH#18 완료: 브랜드 상세 페이지에 브랜드 소식 피드 섹션 추가 및 뉴스 API 연동.
- 2026-02-28 07:23:43 | agent:codex-dev | task:T-20260228-014 | action:complete | message:GH#19 완료: `/collabs` 타임라인 페이지 구현(카테고리 필터/하입 요약/타임라인 카드).

- 2026-02-28 07:30:00 | agent:claude-pm | task:T-20260228-011 | action:log | message:Phase 6 리뷰 완료. 스케줄러 뉴스 등록(08:00) + /news 전체 페이지 + Nav 메뉴 PM 직접 보완
- 2026-02-28 07:30:00 | agent:claude-pm | task:T-20260228-015 | action:add-task | message:태스크 생성: DIRECTOR_01 크리에이티브 디렉터 DB + Admin (GH#20)
- 2026-02-28 07:30:00 | agent:claude-pm | task:T-20260228-016 | action:add-task | message:태스크 생성: DIRECTOR_02 디렉터 프론트엔드 (GH#21)
- 2026-02-28 07:30:00 | agent:claude-pm | task:T-20260228-017 | action:add-task | message:태스크 생성: INSTAGRAM_01 인스타그램 URL 컬럼 + Admin (GH#22)
- 2026-02-28 07:30:00 | agent:claude-pm | task:T-20260228-018 | action:add-task | message:태스크 생성: BRAND_DETAIL_01 브랜드 상세 통합 뷰 (GH#23)

- 2026-02-28 08:00:00 | agent:claude-pm | task:T-20260228-019 | action:add-task | message:태스크 생성: SALE_DEDUP_01 세일 최저가 중복 제거 (GH#24)
- 2026-02-28 08:00:00 | agent:claude-pm | task:T-20260228-020 | action:add-task | message:태스크 생성: NAV_BACK_01 compare 뒤로가기 개선 (GH#25)
- 2026-02-28 08:00:00 | agent:claude-pm | task:T-20260228-021 | action:add-task | message:태스크 생성: COLLAB_ADMIN_01 Admin 협업 관리 (GH#26)
- 2026-02-28 08:00:00 | agent:claude-pm | task:T-20260228-022 | action:add-task | message:태스크 생성: CHANNEL_BRAND_AUDIT_01 채널-브랜드 혼재 감사 (GH#27)
- 2026-02-28 07:48:05 | agent:codex-dev | task:T-20260228-015 | action:complete | message:GH#20 완료: BrandDirector 모델/마이그레이션, Admin 디렉터 CRUD API, /admin 디렉터 관리 UI 구현.
- 2026-02-28 07:48:05 | agent:codex-dev | task:T-20260228-016 | action:complete | message:GH#21 완료: /directors 페이지 및 Nav 메뉴 추가, 브랜드 상세 디렉터 섹션 연동.
- 2026-02-28 07:48:05 | agent:codex-dev | task:T-20260228-017 | action:complete | message:GH#22 완료: brands/channels instagram_url 컬럼 + Admin PATCH API + Admin 입력 UI + 프론트 인스타 링크 표시.
- 2026-02-28 07:48:05 | agent:codex-dev | task:T-20260228-018 | action:complete | message:GH#23 완료: /brands/{slug}/collabs API 및 브랜드 상세 통합 뷰(협업/디렉터/인스타/뉴스) 완성.
- 2026-02-28 08:07:15 | agent:codex-dev | task:T-20260228-019 | action:complete | message:GH#24 완료: sales-highlights를 product_key 최저가 dedup으로 개선하고 total_channels/최저가 배지 반영.
- 2026-02-28 08:07:15 | agent:codex-dev | task:T-20260228-020 | action:complete | message:GH#25 완료: compare 페이지 상단 이동을 브라우저 히스토리 기반 router.back()으로 변경.
- 2026-02-28 08:07:15 | agent:codex-dev | task:T-20260228-021 | action:complete | message:GH#26 완료: Admin 협업 관리 API(GET/POST/DELETE /admin/collabs) 및 관리자 UI 추가.
- 2026-02-28 08:07:15 | agent:codex-dev | task:T-20260228-022 | action:complete | message:GH#27 완료: 채널-브랜드 혼재 감사 API(/admin/brand-channel-audit) 및 관리자 감사 UI 추가.
- 2026-02-28 08:21:45 | agent:codex-dev | task:T-20260228-025 | action:complete | message:GH#28 완료: products 재분류 스크립트(reclassify_products) 추가, classify_gender_and_subcategory 재사용, make reclassify 타깃 반영.
- 2026-02-28 08:21:45 | agent:codex-dev | task:T-20260228-026 | action:complete | message:GH#29 완료: 대시보드 기본 세일 데이터 소스를 sales-highlights로 전환해 최저가 dedup 목록 기반으로 노출.
- 2026-02-28 08:21:45 | agent:codex-dev | task:T-20260228-027 | action:complete | message:GH#30 완료: 브랜드 MECE 정제 스크립트(fix_brand_mece) 추가, 기본 dry-run 및 suspicion=high/안전삭제 후보 출력.
- 2026-02-28 13:34:29 | agent:codex-dev | task:T-20260228-028 | action:complete | message:GH#31 완료: cleanup_mixed_brand_channel에 --apply-with-products 추가(제품 brand_id NULL→링크 삭제→브랜드 삭제) 및 make fix-brands 반영.
- 2026-02-28 13:34:29 | agent:codex-dev | task:T-20260228-029 | action:complete | message:GH#32 완료: fix_null_brand_id 스크립트 추가(dry-run/apply), brand-store 매칭 31쌍 기준 NULL brand_id 재매핑 및 make fix-null-brands 반영.
- 2026-02-28 13:41:25 | agent:codex-dev | task:T-20260228-028 | action:log | message:실데이터 적용 실행: --apply-with-products 결과 brands 21건 삭제, channel_brands 7건 삭제, products brand_id NULL 9005건 처리.
- 2026-02-28 13:41:25 | agent:codex-dev | task:T-20260228-029 | action:log | message:실데이터 적용 실행: fix_null_brand_id --apply 결과 1896건 재매핑, 후속 dry-run remap_candidates=0 확인.
- 2026-02-28 13:42:50 | agent:codex-dev | task:T-20260228-030 | action:complete | message:GH#33 완료: 가격비교 API 응답에 is_official/channel_type 추가, Compare 페이지 공식 배지 및 채널타입 UI 반영.
- 2026-02-28 14:00:46 | agent:codex-dev | task:T-20260228-032 | action:complete | message:GH#34 완료: products.archived_at 마이그레이션, upsert_product 품절 전환 타임스탬프 반영, 목록 API 활성 제품 필터링, /products/archive 엔드포인트 추가.
- 2026-02-28 14:00:46 | agent:codex-dev | task:T-20260228-033 | action:complete | message:GH#35 완료: 멀티채널 경쟁 제품 집계 API(/products/multi-channel)와 /compete 페이지, Nav 경쟁 메뉴 구현.
- 2026-02-28 15:12:48 | agent:codex-dev | task:T-20260228-034 | action:complete | message:GH#36 완료: Alembic settings DB URL 연동, CORS 환경변수화, Railway/Vercel 설정 파일 추가, SQLite→PG 시드 마이그레이션 스크립트 및 dry-run 검증 완료.
- 2026-02-28 22:56:53 | agent:codex-dev | task:T-20260228-036 | action:complete | message:GH#37 완료: Makefile 실행 커맨드를 uv run python으로 정비하고 crawl/crawl-news/update-rates/scheduler-dry 타겟 추가, Railway Worker 배포 가이드 문서화, scheduler dry-run 검증 완료.
- 2026-02-28 22:56:53 | agent:codex-dev | task:T-20260228-037 | action:complete | message:GH#38 완료: brand_directors.csv(32행)와 seed_directors 스크립트(dry-run/apply) 추가, make seed-directors 타겟 반영, 로컬 DB 시드 적용(21건 생성) 확인.
- 2026-02-28 23:21:59 | agent:codex-dev | task:T-20260228-038 | action:complete | message:GH#39 완료: 브랜드 인리치 CSV/스크립트 및 누락 럭셔리 브랜드 시드 스크립트 추가, 디렉터 CSV 실명/검증 메타 반영, make enrich-brands/seed-brands-luxury/seed-directors 검증 및 DB 적용 완료.
- 2026-02-28 23:31:55 | agent:codex-dev | task:T-20260228-039 | action:complete | message:GH#40 완료: 가짜 브랜드 정리 스크립트/Makefile 타겟/크롤러 필터 추가 후 apply 실행. fake 416건 삭제, channel_brands 397건 삭제, products.brand_id NULL 402건 처리.
- 2026-03-01 00:00:00 | agent:claude-pm | task:T-20260301-041 | action:add-task | message:GH#41 등록: 편집샵 크롤 전략 + product_key→brand_id 재매핑. 조사 결과: ①Goodhood slug 매핑 가능 2,155개(brands 테이블 114/157종 매칭), ②FASCINATE vendor=채널명(product_key로 브랜드 추출 불가) → vendor 컬럼 신설 필요, ③47개 미크롤 채널 분류: Bodega Shopify OK/SEVENSTORE 403/HBX+DSM+HIP 비Shopify/Kasina Cafe24/일본PaaS/Shopline 등.
- 2026-03-01 00:06:38 | agent:codex-dev | task:T-20260228-038 | action:log | message:브랜드 디렉터 리서치 CSV(109행) 반영 및 seed_directors apply 수행(created 100, duplicate 9, missing 0).
- 2026-03-01 00:13:04 | agent:codex-dev | task:T-20260301-041 | action:complete | message:GH#41 완료: products.vendor 컬럼 마이그레이션(a7c9d1e3f5b7), upsert vendor 저장, remap_product_brands apply로 edit-shop brand_id NULL 2,423건 복구(13,642→11,219).
- 2026-03-01 01:19:34 | agent:codex-dev | task:T-20260301-042 | action:complete | message:FIX_CURRENCY_01 완료: 환율 통화 확대(DKK/SEK/SGD/CAD/AUD/TWD/CNY), HK/SG/CA 서브도메인 통화감지 보강, 미등록 통화 fallback warning 추가, update-rates 실행 검증 완료.
- 2026-03-01 01:22:38 | agent:codex-dev | task:T-20260301-043 | action:complete | message:FIX_MULTI_CHANNEL_01 완료: multi-channel 집계를 latest price LEFT JOIN 방식으로 변경, min_channels=2 기준 200건 조회 확인.
- 2026-03-01 01:22:38 | agent:codex-dev | task:T-20260301-044 | action:complete | message:DIRECTOR_PAGE_01 완료: /directors/by-brand API+스키마 추가, 프론트 브랜드 섹션 UI(현행 우선/현재 배지/헤더 링크/검색 필터) 반영.
- 2026-03-01 01:39:18 | agent:codex-dev | task:T-20260301-045 | action:log | message:data_audit 실행 완료(local sqlite). 요약: ERROR 1 / WARNING 3 (brand_id NULL 비율 23.67%, 제품0 채널 78, 7일+ 미크롤 78).

- 2026-03-03 01:56:00 | agent:codex-dev | task:T-20260303-072 | action:complete | message:INTEL_HUB_SPRINT0_01 완료: intel 라우터 스텁/메인 등록, .env.example Intel 변수 4개, scheduler Intel 잡 스텁, /intel/events 200 검증 완료. (npm registry DNS 제한으로 maplibre/pmtiles 설치는 세션 내 미완료)
- 2026-03-03 01:56:00 | agent:codex-dev | task:T-20260303-073 | action:complete | message:INTEL_HUB_DATA_MODEL_01 완료: intel 4개 테이블 마이그레이션(f1a2b3c4d5e6), ingest_intel_events mirror 구현/실행(inserted=34), /intel/events|map-points|timeline|highlights|events/{id} API 구현, Makefile ingest-intel 추가.
- 2026-03-03 01:56:00 | agent:codex-dev | task:T-20260303-074 | action:complete | message:INTEL_HUB_FRONTEND_01 완료: /intel 페이지(레이어 토글, 시간 필터, URL deep link, 가상 스크롤 피드, stacked 타임라인, 상세 드로어/watchlist) 구현, IntelMap(Maplibre CDN) 및 Nav Intel 메뉴 반영.
- 2026-03-03 01:56:00 | agent:codex-dev | task:T-20260303-075 | action:complete | message:INTEL_HUB_DERIVED_EVENTS_01 완료: sale_start/sold_out/restock 파생 이벤트 후크(crawl_products+upsert_product) 및 derived_spike 배치(job=derived_spike, inserted=500) 반영, scheduler intel_ingest_0730 활성화, /admin/intel-status API+Admin UI 섹션 추가.
- 2026-03-03 02:06:00 | agent:codex-dev | task:T-20260303-076 | action:complete | message:INTEL_HUB_DERIVED_EVENTS_FIX_01 완료: sales_spike 후보 선정 로직을 48h/7d baseline delta 조건으로 강화(sale_count>=15 + ratio/discount delta), sale_start severity를 discount_rate 기반으로 정교화, upsert_derived_product_event geo_precision(country/global) 명시, calc_confidence_score 유틸 추가, crawl_products sale_start details에 discount_rate 전달. derived_spike 배치 재실행 성공(errors=0).
- 2026-03-03 20:58:00 | agent:codex-dev | task:T-20260303-077 | action:complete | message:INTEL_NEWS_REALTIME_01 완료: crawl_news RSS 소스(영문+한국 8개) 확장, feedparser bozo 스킵 처리 추가, scheduler 뉴스/Intel 잡을 4회/일로 재구성(news_4x_daily, intel_mirror_4x_daily, intel_spike_4x_daily), 기존 intel_ingest_0730 제거. crawl_news --per-feed 5 실행에서 bozo 스킵 로그와 inserted=15 확인.
- 2026-03-03 20:58:00 | agent:codex-dev | task:T-20260303-078 | action:complete | message:INTEL_CRAWL_AUTO_TRIGGER_01 완료: crawl_products에 --no-intel 플래그 추가, 크롤 완료 후 total_upserted>0일 때 derived_spike→mirror 자동 실행(예외 격리) 구현. --no-intel 실행 시 스킵 로그, 기본 실행 시 자동 트리거 실행 로그 확인.
- 2026-03-03 20:58:00 | agent:codex-dev | task:T-20260303-079 | action:complete | message:INTEL_SHOPIFY_DROP_DETECT_01 완료: ingest_intel_events에 COMING_SOON_TAGS 및 _ingest_shopify_drops 구현(brand-store+shopify+recent7d+tags), mirror 분기 포함 및 --job shopify_drops 단독 실행 지원. 검증 실행 성공(errors=0).
- 2026-03-03 20:58:00 | agent:codex-dev | task:T-20260303-080 | action:complete | message:INTEL_DISCORD_ALERT_01 완료: intel_service notify_discord_if_warranted 구현(critical/high만 전송), config/.env.example에 INTEL_DISCORD_WEBHOOK_URL 추가, ingest/_upsert_event 및 upsert_derived_product_event 신규 이벤트 생성 시 Discord 알림 훅 연결(실패 시 warning, 이벤트 생성 유지).
- 2026-03-03 21:30:00 | agent:claude-pm | task:- | action:log | message:crawl_news.py PostgreSQL timezone 버그 수정 (parsedate_to_datetime → UTC naive 변환). Railway DB intel 최신화 완료(mirror inserted=47, spike inserted=4). Railway Worker 서비스 등록 완료 — scheduler.py 자동 스케줄 운영 시작(뉴스4회/intel4회/제품크롤1회/일). INTEL_INGEST_ENABLED=true 설정. 현재 Railway DB intel_events 591건.

## 2026-03-01 01:39:18 data_audit 출력 전문
```text
Fashion Data Audit
DB Target: sqlite+aiosqlite:///...
Started At (UTC): 2026-02-28T16:38:44.741403+00:00

──────────────────────────────── [1] 채널 현황 ─────────────────────────────────
  채널 기본 통계   
┏━━━━━━━━━━━┳━━━━━┓
┃ 항목      ┃  값 ┃
┡━━━━━━━━━━━╇━━━━━┩
│ 전체 채널 │ 159 │
│ 활성 채널 │ 159 │
└───────────┴─────┘
     채널별 제품 수 상위      
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ 채널             ┃ 제품 수 ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ 082plus          │    4000 │
│ Goodhood         │    4000 │
│ H. Lorenzo       │    4000 │
│ NUBIAN           │    4000 │
│ THE NATURES      │    4000 │
│ cocorozashi      │    4000 │
│ unexpected store │    4000 │
│ JACK in the NET  │    3999 │
│ Limited Edt      │    3999 │
│ FASCINATE        │    3993 │
│ Slam Jam         │    3990 │
│ Slam Jam         │    3990 │
│ ADDICTED         │    2698 │
│ COVERCHORD       │    2374 │
│ SOUTH STORE      │    2054 │
│ Family 3.0       │    2027 │
│ Tree and Branch  │    1221 │
│ ANNMS Shop       │    1215 │
│ CHERRY LA        │    1200 │
│ NOMAD            │    1086 │
└──────────────────┴─────────┘
                         제품 0개 채널 목록                         
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 채널                     ┃ URL                                   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 8DIVISION                │ https://www.8division.com             │
│ ACRMTSM                  │ https://www.acrmtsm.jp                │
│ ADEKUVER                 │ https://www.adekuver.com              │
│ APPLIXY                  │ https://www.applixy.com               │
│ ARKnets                  │ https://www.arknets.co.jp             │
│ AXEL ARIGATO             │ https://www.axelarigato.com           │
│ Alfred                   │ https://www.thegreatalfred.com        │
│ BAYCREW'S                │ https://www.baycrews.jp               │
│ BIZZARE                  │ https://www.bizzare.co.kr             │
│ Bodega                   │ https://bdgastore.com                 │
│ CAYL                     │ https://www.cayl.co.kr                │
│ CLESSTE                  │ https://www.clesste.com               │
│ COEVO                    │ https://www.coevo.com                 │
│ Camperlab                │ https://www.camperlab.com             │
│ Casestudy                │ https://www.casestudystore.co.kr      │
│ Dover Street Market      │ https://store.doverstreetmarket.com   │
│ ECRU Online              │ https://www.ecru.co.kr                │
│ EFFORTLESS               │ https://www.effortless-store.com      │
│ ETC SEOUL                │ https://www.etcseoul.com              │
│ F/CE                     │ https://www.fce-store.com             │
│ GOOUTSTORE               │ https://gooutstore.cafe24.com         │
│ Goldwin                  │ https://www.goldwin-global.com        │
│ HBX                      │ https://hbx.com                       │
│ HIP                      │ https://www.thehipstore.co.uk         │
│ Harrods                  │ https://www.harrods.com               │
│ Joe Freshgoods           │ https://www.joefreshgoods.com         │
│ KA-YO                    │ https://www.ka-yo.com                 │
│ Kasina                   │ https://www.kasina.co.kr              │
│ Kerouac                  │ https://www.kerouac.okinawa           │
│ LTTT                     │ https://www.lttt.life                 │
│ Laid back                │ https://laidback0918.shop-pro.jp      │
│ MODE MAN                 │ https://www.mode-man.com              │
│ MaisonShunIshizawa store │ https://www.maisonshunishizawa.online │
│ Meclads                  │ https://www.meclads.com               │
│ Mercari (메루카리)       │ https://jp.mercari.com                │
│ MusterWerk               │ https://www.musterwerk-sud.com        │
│ NOCLAIM                  │ https://www.noclaim.co.kr             │
│ Openershop               │ https://www.openershop.co.kr          │
│ PALACE SKATEBOARDS       │ https://shop.palaceskateboards.com    │
│ PARLOUR                  │ https://www.parlour.kr                │
│ Pherrow's                │ https://www.pherrows.tokyo            │
│ ROOM ONLINE STORE        │ https://www.room-onlinestore.jp       │
│ Rino Store               │ https://www.rinostore.co.kr           │
│ Rogues                   │ https://www.rogues.co.jp              │
│ SCULP STORE              │ https://www.sculpstore.com            │
│ SEVENSTORE               │ https://www.sevenstore.com            │
│ SHRED                    │ https://www.srd-osaka.com             │
│ SOMEIT                   │ https://someit.stores.jp              │
│ Stone Island             │ https://www.stoneisland.com           │
│ Sun Chamber Society      │ https://www.sunchambersociety.com     │
│ Séfr                     │ https://www.sefr-online.com           │
│ THEXSHOP                 │ https://www.thexshop.co.kr            │
│ TIGHTBOOTH               │ https://shop.tightbooth.com           │
│ TINY OSAKA               │ https://www.tinyworld.jp              │
│ TITY                     │ https://tity.ocnk.net                 │
│ TTTMSW                   │ https://www.tttmsw.jp                 │
│ TUNE.KR                  │ https://www.tune.kr                   │
│ The Real McCoy's         │ https://www.therealmccoys.jp          │
│ The Trilogy Tapes        │ https://www.thetrilogytapes.com       │
│ UNDERCOVER Kanazawa      │ https://undercoverk.theshop.jp        │
│ Unipair                  │ https://www.unipair.com               │
│ VINAVAST                 │ https://www.vinavast.co               │
│ Warren Lotas             │ https://www.warrenlotas.com           │
│ a.dresser                │ https://www.adressershop.com          │
│ and wander               │ https://www.andwander.co.kr           │
│ browniegift              │ https://www.brownieonline.jp          │
│ elephant TRIBAL fabrics  │ https://elephab.buyshop.jp            │
│ empty                    │ https://www.empty.seoul.kr            │
│ grds                     │ https://www.grds.com                  │
│ heritagefloss            │ https://www.heritagefloss.com         │
│ nightwaks                │ https://www.nightwaks.com             │
│ obscura                  │ https://www.obscura-store.com         │
│ thisisneverthat          │ https://www.thisisneverthat.com       │
│ wegenk                   │ https://www.wegenk.com                │
│ 브레슈 (Breche)          │ https://www.breche-online.com         │
│ 블루스맨 (Bluesman)      │ https://www.bluesman.co.kr            │
│ 슈피겐                   │ https://www.spigen.co.kr              │
│ 앤드헵 (Pheb)            │ https://shop.pheb.jp                  │
└──────────────────────────┴───────────────────────────────────────┘
           7일 이상 미크롤 채널           
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ 채널                     ┃ 마지막 크롤 ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Alfred                   │ never       │
│ Meclads                  │ never       │
│ Openershop               │ never       │
│ KA-YO                    │ never       │
│ empty                    │ never       │
│ 8DIVISION                │ never       │
│ ACRMTSM                  │ never       │
│ Goldwin                  │ never       │
│ VINAVAST                 │ never       │
│ thisisneverthat          │ never       │
│ a.dresser                │ never       │
│ obscura                  │ never       │
│ MODE MAN                 │ never       │
│ THEXSHOP                 │ never       │
│ Rogues                   │ never       │
│ CAYL                     │ never       │
│ SCULP STORE              │ never       │
│ BIZZARE                  │ never       │
│ elephant TRIBAL fabrics  │ never       │
│ MaisonShunIshizawa store │ never       │
│ 브레슈 (Breche)          │ never       │
│ Kerouac                  │ never       │
│ CLESSTE                  │ never       │
│ and wander               │ never       │
│ HIP                      │ never       │
│ grds                     │ never       │
│ heritagefloss            │ never       │
│ AXEL ARIGATO             │ never       │
│ Harrods                  │ never       │
│ LTTT                     │ never       │
│ ETC SEOUL                │ never       │
│ ECRU Online              │ never       │
│ 앤드헵 (Pheb)            │ never       │
│ Rino Store               │ never       │
│ COEVO                    │ never       │
│ Sun Chamber Society      │ never       │
│ GOOUTSTORE               │ never       │
│ MusterWerk               │ never       │
│ Unipair                  │ never       │
│ ADEKUVER                 │ never       │
│ TITY                     │ never       │
│ TTTMSW                   │ never       │
│ browniegift              │ never       │
│ PARLOUR                  │ never       │
│ SOMEIT                   │ never       │
│ Pherrow's                │ never       │
│ The Trilogy Tapes        │ never       │
│ Joe Freshgoods           │ never       │
│ Warren Lotas             │ never       │
│ 블루스맨 (Bluesman)      │ never       │
│ EFFORTLESS               │ never       │
│ SHRED                    │ never       │
│ TIGHTBOOTH               │ never       │
│ Séfr                     │ never       │
│ ROOM ONLINE STORE        │ never       │
│ wegenk                   │ never       │
│ Kasina                   │ never       │
│ SEVENSTORE               │ never       │
│ NOCLAIM                  │ never       │
│ Laid back                │ never       │
│ nightwaks                │ never       │
│ Mercari (메루카리)       │ never       │
│ Casestudy                │ never       │
│ APPLIXY                  │ never       │
│ Stone Island             │ never       │
│ PALACE SKATEBOARDS       │ never       │
│ ARKnets                  │ never       │
│ The Real McCoy's         │ never       │
│ UNDERCOVER Kanazawa      │ never       │
│ TINY OSAKA               │ never       │
│ TUNE.KR                  │ never       │
│ BAYCREW'S                │ never       │
│ F/CE                     │ never       │
│ Camperlab                │ never       │
│ 슈피겐                   │ never       │
│ Dover Street Market      │ never       │
│ HBX                      │ never       │
│ Bodega                   │ never       │
└──────────────────────────┴─────────────┘
───────────────────────────── [2] 브랜드 매핑 품질 ─────────────────────────────
         브랜드 매핑 요약         
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ 항목          ┃             값 ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ 전체 제품     │          80096 │
│ brand_id NULL │ 18962 (23.67%) │
└───────────────┴────────────────┘
 channel_type별 brand_id NULL  
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ channel_type ┃ NULL 제품 수 ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ edit-shop    │        11219 │
│ brand-store  │         7743 │
└──────────────┴──────────────┘
   brand_id NULL 상위 10개 채널   
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ 채널            ┃ NULL 제품 수 ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ FASCINATE       │         3991 │
│ SOUTH STORE     │         2054 │
│ 082plus         │         1088 │
│ HAMCUS          │          911 │
│ Tree and Branch │          746 │
│ CHERRY LA       │          738 │
│ Velour Garments │          586 │
│ PAN KANAZAWA    │          575 │
│ MARKAWARE       │          569 │
│ NƏW LIGHT       │          532 │
└─────────────────┴──────────────┘
         유령 브랜드          
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┓
┃ 항목                ┃   값 ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━┩
│ products 0개 브랜드 │ 1159 │
└─────────────────────┴──────┘
──────────────────────────────── [3] 가격 품질 ─────────────────────────────────
       가격 이상치        
┏━━━━━━━━━━━━━━━━━━━┳━━━━┓
┃ 항목              ┃ 값 ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━┩
│ price=0 또는 NULL │  0 │
│ price>50,000,000  │  0 │
└───────────────────┴────┘
         고가 이상값 샘플          
┏━━━━━━━━━━━━┳━━━━━━┳━━━━━━━┳━━━━━┓
┃ product_id ┃ name ┃ price ┃ url ┃
┡━━━━━━━━━━━━╇━━━━━━╇━━━━━━━╇━━━━━┩
└────────────┴──────┴───────┴─────┘
 통화별 제품 수(최신  
      가격 기준)      
┏━━━━━━━━━━┳━━━━━━━━━┓
┃ currency ┃ 제품 수 ┃
┡━━━━━━━━━━╇━━━━━━━━━┩
│ KRW      │   80096 │
└──────────┴─────────┘
환율 미등록 통화 사용 
         현황         
┏━━━━━━━━━━┳━━━━━━━━━┓
┃ currency ┃ 제품 수 ┃
┡━━━━━━━━━━╇━━━━━━━━━┩
└──────────┴─────────┘
          역전 이상값          
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━┓
┃ 항목                   ┃ 값 ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━┩
│ original_price < price │  0 │
└────────────────────────┴────┘
──────────────────────────── [4] 세일 / 신상품 현황 ────────────────────────────
        세일/신상품 요약         
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ 항목         ┃             값 ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ is_sale=True │ 19997 (24.97%) │
│ is_new=True  │       0 (0.0%) │
└──────────────┴────────────────┘
  discount_rate  
분포(is_sale=True
   최신 기준)    
┏━━━━━━━┳━━━━━━━┓
┃ 구간  ┃    수 ┃
┡━━━━━━━╇━━━━━━━┩
│ 40%+  │ 15646 │
│ 30%대 │  2671 │
│ 20%대 │  1426 │
│ 10%대 │   244 │
│ <10%  │    10 │
└───────┴───────┘
            세일 데이터 불일치             
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━┓
┃ 항목                               ┃ 값 ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━┩
│ is_sale=True && discount_rate=NULL │  0 │
└────────────────────────────────────┴────┘
────────────────────────────── [5] 활성/품절 현황 ──────────────────────────────
                활성/품절 통계                 
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ 항목                                ┃    값 ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ is_active=True                      │ 80096 │
│ is_active=False                     │     0 │
│ archived_at IS NOT NULL             │     0 │
│ is_active=False && archived_at NULL │     0 │
└─────────────────────────────────────┴───────┘
──────────────────────────── [6] PriceHistory 품질 ─────────────────────────────
                  PriceHistory 요약                   
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 항목                  ┃                         값 ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 총 레코드             │                      81892 │
│ PriceHistory 0건 제품 │                          0 │
│ 제품당 평균 레코드    │                      1.022 │
│ 가장 오래된 날짜      │ 2026-02-26 12:10:36.766741 │
│ 최신 날짜             │ 2026-02-26 13:25:42.230063 │
└───────────────────────┴────────────────────────────┘
──────────────────────────────── [7] 환율 현황 ─────────────────────────────────
                  exchange_rates 목록                  
┏━━━━━━┳━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ from ┃ to  ┃      rate ┃ fetched_at                 ┃
┡━━━━━━╇━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ AUD  │ KRW │ 1024.5902 │ 2026-02-28 16:19:00.597118 │
│ CAD  │ KRW │ 1054.8523 │ 2026-02-28 16:19:00.597118 │
│ CNY  │ KRW │  207.8138 │ 2026-02-28 16:19:00.597118 │
│ DKK  │ KRW │  227.9982 │ 2026-02-28 16:19:00.597118 │
│ EUR  │ KRW │ 1700.6803 │ 2026-02-28 16:19:00.597118 │
│ GBP  │ KRW │ 1941.7476 │ 2026-02-28 16:19:00.597118 │
│ HKD  │ KRW │  184.1282 │ 2026-02-28 16:19:00.597118 │
│ JPY  │ KRW │    9.2305 │ 2026-02-28 16:19:00.597118 │
│ SEK  │ KRW │  159.3625 │ 2026-02-28 16:19:00.597118 │
│ SGD  │ KRW │ 1138.9522 │ 2026-02-28 16:19:00.597118 │
│ TWD  │ KRW │   45.9031 │ 2026-02-28 16:19:00.597118 │
│ USD  │ KRW │ 1440.9222 │ 2026-02-28 16:19:00.597118 │
└──────┴─────┴───────────┴────────────────────────────┘
 products(최신 가격)  
기준 환율 미등록 통화 
┏━━━━━━━━━━┳━━━━━━━━━┓
┃ currency ┃ 제품 수 ┃
┡━━━━━━━━━━╇━━━━━━━━━┩
└──────────┴─────────┘
─────────────────────────── [8] 전체 요약 (Summary) ────────────────────────────
                              품질 결과                               
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 상태    ┃ 섹션                   ┃ 메시지                          ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ WARNING │ [1] 채널 현황          │ 제품 0개 채널 78개              │
│ WARNING │ [1] 채널 현황          │ 7일 이상 미크롤 채널 78개       │
│ ERROR   │ [2] 브랜드 매핑 품질   │ brand_id NULL 비율 높음: 23.67% │
│ WARNING │ [2] 브랜드 매핑 품질   │ 유령 브랜드 1159개              │
│ OK      │ [3] 가격 품질          │ 고가 이상값 없음                │
│ OK      │ [3] 가격 품질          │ 환율 미등록 통화 없음           │
│ OK      │ [3] 가격 품질          │ 가격 역전 이상값 없음           │
│ OK      │ [4] 세일 / 신상품 현황 │ 세일 데이터 일치                │
│ OK      │ [5] 활성/품절 현황     │ 품절 타임스탬프 누락 없음       │
│ OK      │ [6] PriceHistory 품질  │ 모든 제품에 PriceHistory 존재   │
│ OK      │ [7] 환율 현황          │ 환율 미등록 통화 없음           │
└─────────┴────────────────────────┴─────────────────────────────────┘
      요약 카운트       
┏━━━━━━━━━━━━━━━┳━━━━━━┓
┃ 항목          ┃   값 ┃
┡━━━━━━━━━━━━━━━╇━━━━━━┩
│ OK            │    7 │
│ WARNING       │    3 │
│ ERROR         │    1 │
│ 총 점검 항목  │   11 │
│ 실행 시간(초) │ 0.85 │
└───────────────┴──────┘
             AGENTS 기준값 비교              
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 항목            ┃                      값 ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ channels_total  │     기준 159 / 현재 159 │
│ brands_total    │   기준 2561 / 현재 2570 │
│ products_total  │ 기준 26000 / 현재 80096 │
│ directors_total │     기준 109 / 현재 125 │
└─────────────────┴─────────────────────────┘
[RESULT] ERROR 1개, WARNING 3개

WARNING 총 3개 / ERROR 총 1개
```
- 2026-03-01 01:39:46 | agent:codex-dev | task:T-20260301-045 | action:complete | message:DATA_AUDIT_01 완료: scripts/data_audit.py 구현(8개 섹션+Summary), --help/실행 검증 및 WORK_LOG 출력 전문 append. 현 환경 DATABASE_URL=sqlite라 Railway 실행 커맨드만 제공.
- 2026-03-01 02:02:58 | agent:codex-dev | task:T-20260301-046 | action:complete | message:fix_null_brand_id.py를 async SQLAlchemy 기반으로 재작성(PostgreSQL 호환), name/slug match 출력 및 --limit 추가, make fix-null-brands-dry/apply 추가. 로컬 dry-run 검증 완료.
- 2026-03-01 02:02:58 | agent:codex-dev | task:T-20260301-046 | action:log | message:RAILWAY_DATABASE_URL 미설정으로 Railway dry-run/apply 실실행은 미수행. 준비 커맨드: DATABASE_URL=postgresql+asyncpg://... uv run python scripts/fix_null_brand_id.py --dry-run
- 2026-03-01 02:02:58 | agent:codex-dev | task:T-20260301-047 | action:complete | message:Admin crawl-status API 및 단일 채널 크롤 트리거(job=channel&channel_id) 추가, Admin 페이지 채널 크롤 현황 테이블/상태필터/행별 실행 버튼 반영.
- 2026-03-01 02:02:58 | agent:codex-dev | task:T-20260301-048 | action:complete | message:scheduler에 audit_weekly_sun_0900 등록, data_audit 결과 객체 반환(run_audit/main), send_audit_alert 추가, make audit/audit-railway 타겟 추가.
- 2026-03-01 06:31:32 | agent:codex-dev | task:T-20260301-049 | action:complete | message:NORMALIZE_BACKFILL_01 완료: scripts/backfill_normalized_key.py 신규(dry-run/--apply/--limit, 100건 progress 로그), Makefile backfill-normalized-key 타깃 추가, dry-run --limit 200 검증(candidates=200) 확인.
- 2026-03-01 06:31:32 | agent:codex-dev | task:T-20260301-050 | action:complete | message:PLATFORM_DETECT_01 완료: crawl_products에서 Shopify 성공 시 channel.platform=shopify 자동 갱신, channel_service.update_platform 추가, scripts/detect_platforms.py 및 Makefile detect-platforms 타깃 추가, /channels platform 필드 노출 확인.
- 2026-03-01 06:32:35 | agent:codex-dev | task:T-20260301-049 | action:log | message:backfill_normalized_key --apply --limit 2000 실행: updated=2000, normalized_key_not_null 0→2000 증가 확인.
- 2026-03-01 06:32:35 | agent:codex-dev | task:T-20260301-050 | action:log | message:detect_platforms --apply --limit 60 실행: detected_shopify=0 (현재 실행 환경에서 외부 채널 접속 기반 감지 미검출).
- 2026-03-01 06:42:24 | agent:codex-dev | task:T-20260301-051 | action:complete | message:products.tags 컬럼+마이그레이션 추가, Shopify tags 문자열 파싱(JSON 저장) 및 upsert 반영, backfill_normalized_key에서 tags JSON 파싱 전달 반영. 샘플 파싱에서 tags 기반 confidence=0.8 확인.
- 2026-03-01 06:42:24 | agent:codex-dev | task:T-20260301-051 | action:log | message:make backfill-normalized-key-apply 실행(실행 시점 DB normalized_key 이미 전체 채움 상태로 scanned=0/updated=0).
- 2026-03-01 06:42:24 | agent:codex-dev | task:T-20260301-052 | action:complete | message:Cafe24 제품 크롤 fallback 구현(_discover_cafe24_brand_categories + _try_cafe24_products), crawl_products의 channel_brands.cate_no 전달 및 platform='cafe24' 자동 갱신 반영, channel_brands.cate_no 스키마/저장 로직 및 make crawl-cafe24 추가.
- 2026-03-01 06:42:24 | agent:codex-dev | task:T-20260301-052 | action:log | message:현 세션 네트워크/DNS 및 Playwright sandbox 제한으로 kasina/8division 실크롤 DoD(100개+)는 로컬 실행 검증 불가.
- 2026-03-01 06:51:14 | agent:codex-dev | task:T-20260301-053 | action:complete | message:backfill_normalized_key에 --force 추가(전체 재계산), confidence_0.8(tags) before/after 통계 출력 추가, Makefile backfill-normalized-key-force 타깃 추가 및 실행 완료.
- 2026-03-01 06:51:14 | agent:codex-dev | task:T-20260301-053 | action:log | message:make backfill-normalized-key-force 실행 결과: scanned=80096, updated=80096, confidence_0.8(tags) 0->0 (tags 데이터 확충 후 재실행 필요).
- 2026-03-01 22:55:31 | agent:codex-dev | task:T-20260301-054 | action:complete | message:PRODUCT_DENYLIST_01 완료: product_crawler에 vendor/title/product_type 거부 목록 상수 추가 및 _parse_product 선제 필터 적용으로 Route·기프트카드·보증성 상품 크롤 차단.
- 2026-03-01 22:55:31 | agent:codex-dev | task:T-20260301-055 | action:complete | message:CHANNEL_TRAFFIC_LIGHT_01 완료: /admin/channel-signals API(최근 5회 성공률·마지막 에러·신호등 판정) 추가, /admin 채널 관리 탭을 신호등/성공률 UI로 전환.
- 2026-03-02 12:16:37 | agent:codex-dev | task:T-20260302-056 | action:complete | message:CHANNEL_PROBE_01 완료: channel_probe 스크립트 추가(제품 0개 채널 비동기 HTTP/Shopify/Cafe24 진단, CSV 출력, --apply platform 반영). dry-run 실행으로 reports/channel_probe_test.csv 생성 확인.
- 2026-03-02 12:16:37 | agent:codex-dev | task:T-20260302-057 | action:complete | message:PRICE_HISTORY_PARTITION_01 완료: PostgreSQL 전용 월별 RANGE 파티셔닝 Alembic(d4e5f6a7b8c9) 추가. SQLite 환경은 안전 스킵, default 파티션/인덱스/데이터 이관/sequence 보정 포함.
- 2026-03-02 12:16:37 | agent:codex-dev | task:T-20260302-058 | action:complete | message:PRODUCT_CATALOG_PIPELINE_01 완료: catalog_service 도입(full/incremental), build_product_catalog 스크립트 --since/--since-last-crawl 지원, crawl_products 종료 후 자동 증분 빌드 및 --skip-catalog 옵션 추가, /admin/catalog-stats API 추가.
- 2026-03-02 12:16:37 | agent:codex-dev | task:T-20260302-059 | action:complete | message:CRAWL_ERROR_TYPE_01 완료: crawl_channel_logs.error_type 컬럼 및 마이그레이션(e5f6a7b8c9d0) 추가, 크롤 실패 유형 분류/저장 적용, channel-signals 및 어드민 UI에 error_type 노출.
- 2026-03-02 14:00:00 | agent:claude-pm | task:CC-1 | action:complete | message:Phase 22 CC-1 완료: cleanup_route_products.py 작성 및 실행 — Route 배송보험·CHERRY LA Package Protection 5개(ID:24936,24938,38679,54305,56304) is_active=False 소프트 삭제.
- 2026-03-02 14:00:01 | agent:claude-pm | task:CC-2 | action:complete | message:Phase 22 CC-2 완료: detect_platforms.py --apply 실행 — 신규 Shopify 감지 0개 (78개 NULL 채널 대부분 비표준 플랫폼 또는 shop.json 차단). T-056 channel_probe.py로 후속 진단 예정.
- 2026-03-02 14:00:02 | agent:claude-pm | task:CC-3 | action:complete | message:Phase 22 CC-3 완료: build_product_catalog.py 실행 — ProductCatalog 64,075개 생성. SQLite 호환을 위해 MODE() → CTE+ROW_NUMBER() 방식으로 수정, NOW() → CURRENT_TIMESTAMP 수정 포함.
- 2026-03-02 14:00:03 | agent:claude-pm | task:CC-4 | action:complete | message:Phase 22 CC-4 완료: T-054(PRODUCT_DENYLIST) 구현 검증(product_crawler.py 66-92행 frozenset denylist 3종 확인), T-055(CHANNEL_TRAFFIC_LIGHT) 구현 검증(admin.py _compute_traffic_light() + /admin/channel-signals 엔드포인트, frontend TrafficLight 컴포넌트 확인).
- 2026-03-02 14:00:04 | agent:claude-pm | task:T-20260302-056 | action:add-task | message:Codex 과업 T-056~T-059 등록 완료: agents/TASK_DIRECTIVE.md 업데이트 + agents/issues/ 4개 지시서 작성(CHANNEL_PROBE_01, PRICE_HISTORY_PARTITION_01, PRODUCT_CATALOG_PIPELINE_01, CRAWL_ERROR_TYPE_01).
- 2026-03-02 14:00:05 | agent:claude-pm | task:- | action:log | message:Phase 22 코드리뷰 완료: T-056~T-059 Codex 구현 검증 — channel_probe.py(SEM=10, /products.json?limit=1, Cafe24 xans-product HTML 감지), catalog_service.py(build_catalog_full/incremental, get_last_done_crawl_finished_at), Alembic d4e5f6a7b8c9(PG RANGE 파티션+SQLite 스킵), e5f6a7b8c9d0(error_type VARCHAR(30)) 모두 사양 준수 확인.
- 2026-03-02 13:59:52 | agent:codex-dev | task:T-20260302-062 | action:complete | message:CRAWL_WOOCOMMERCE_01 완료: ProductCrawler fallback 체인에 WooCommerce REST API 감지/수집/파싱 추가(Shopify→Cafe24→WooCommerce), crawl_products에서 woocommerce-api 성공 시 channel.platform=woocommerce 자동 반영.
- 2026-03-02 13:59:52 | agent:codex-dev | task:T-20260302-063 | action:complete | message:CHANNEL_HEALTH_CLEANUP_01 완료: deactivate_dead_channels 스크립트 추가(연속 실패/HTTP 404·410/NULL platform+제품0+노후 기준, brand-store 제외, dry-run 기본, apply 확인 프롬프트 및 최소 후보 수 안전장치 적용).
- 2026-03-02 16:31:46 | agent:codex-dev | task:T-20260302-064 | action:complete | message:CRAWL_RATE_LIMIT_FIX_01 완료: Shopify 요청 안정화(concurrency 기본 2, 전역 semaphore throttle, 브라우저형 헤더, page limit 100/최대 40페이지, 채널 시작 0~3초 stagger) 적용. crawl_products 저장 단계/로그 기록 예외 보호를 추가해 실패 시에도 CrawlChannelLog 누락 없이 error_type 기록되도록 보강.
- 2026-03-02 16:31:46 | agent:codex-dev | task:T-20260302-065 | action:complete | message:PRICE_CATALOG_AUDIT_01 완료: get_rate_to_krw의 1.0 fallback 제거 및 통화 fallback/None 처리 도입, record_price 비현실 값 guard 추가. audit_price_data/cleanup_price_data 스크립트 신규 작성 및 Makefile 타깃 추가, dry-run 감사 결과 KRW 94,210건 중 의심 7,662건(8.13%) 확인.
- 2026-03-02 17:13:47 | agent:codex-dev | task:T-20260302-066 | action:complete | message:CAFE24_CRAWL_FIX_01 완료: probe_cafe24_channels/seed_cafe24_categories 스크립트 추가, product_crawler Cafe24 병렬 처리(세마포어 5)+429/503 재시도+카테고리 URL 패턴 확장/합산 반영. THEXSHOP 단독 크롤 Run#4 성공(29,485개, duration 277.5s) 및 channel_brands.cate_no 사전 시드 적용 확인.
- 2026-03-02 17:13:47 | agent:codex-dev | task:T-20260302-067 | action:log | message:ZERO_PRODUCT_CHANNEL_STRATEGY_01 진행: channel_probe 확장(URL/HTTP 신호 기반 makeshop/stores-jp/ochanoko 감지, blocked 표기, 플랫폼 요약) 후 --apply로 37개 플랫폼 업데이트. deactivate_inaccessible_channels 스크립트 추가 및 --include-brand-stores --apply로 접근 불가 7개(CLESSTE, Dover Street Market, Kerouac, PALACE SKATEBOARDS, Pherrow's, The Real McCoy's, TUNE.KR) 비활성화. 일본 SaaS 실수집 성공 채널 목표(>=3)는 현재 미달(Laid back/elephant TRIBAL 0개)로 후속 필요.
- 2026-03-02 17:24:30 | agent:codex-dev | task:T-20260302-067 | action:log | message:일본 SaaS 수집률 개선 2차 반영: product_crawler generic 수집기에 entry_paths 다중 순회(/items/all,/collections/all,/shop/goods/search.aspx,/item-list 등)와 JSON-LD Product 폴백 파서 추가. 컴파일 통과 후 Laid back 재시도(Run#8) 했지만 현 환경 DNS/접속 이슈로 0건 지속.
- 2026-03-02 17:42:59 | agent:codex-dev | task:T-20260302-067 | action:log | message:타임스탬프 보정: 동일 작업(일본 SaaS 크롤러 2차 개선 + Run#8 검증) 기록 시각을 17:42:59로 정정.
- 2026-03-02 17:45:31 | agent:codex-dev | task:T-20260302-067 | action:complete | message:ZERO_PRODUCT_CHANNEL_STRATEGY_01 마감: 플랫폼 분류/비활성화/크롤러 보강(일본 SaaS 다중 엔트리+JSON-LD 폴백) 구현 및 실행 반영 완료. 단, 현 세션 DNS 제약으로 일본 SaaS 실수집 >=3채널 검증은 운영 환경 후속 검증 항목으로 남김.
- 2026-03-02 18:26:52 | agent:codex-dev | task:T-20260302-068 | action:complete | message:SHOPIFY_PROBE_RATELIMIT_FIX_01 완료: channel_probe에 --force-retag 추가, 기본 --all에서 기존 platform 설정 채널 스킵(실행 시 119개 스킵 확인), Shopify probe 전용 세마포어 2 적용. deactivate_dead_channels 연속 실패 기준을 error_type=not_supported로 제한(429/timeout 제외), crawl_products 상단에 probe-크롤 동시 실행 위험 가이드 반영.
- 2026-03-02 18:26:52 | agent:codex-dev | task:T-20260302-069 | action:complete | message:CAFE24_SINGLE_BRAND_CRAWL_01 완료: ProductCrawler에 _parse_cafe24_product_list 공통 파서와 _try_cafe24_single_brand(/product/list.html 기반) 추가, crawl_channel에 cafe24-single-brand fallback 연결. 로컬 검증(heritagefloss/Sun Chamber Society/nightwaks)은 현 세션 DNS 제약으로 0건.
- 2026-03-02 18:26:52 | agent:codex-dev | task:T-20260302-070 | action:blocked | message:RAILWAY_CRAWL_VERIFY_01 차단: railway CLI 미설치 및 RAILWAY_DATABASE_URL/DATABASE_URL 미설정으로 Railway 실행 불가. 실행 시도/차단 원인/즉시 실행 명령을 reports/railway_crawl_verify_2026-03-02.md에 기록.
- 2026-03-02 18:26:52 | agent:codex-dev | task:T-20260302-071 | action:complete | message:NULL_PLATFORM_AUDIT_01 완료: channel_probe --force-retag로 NULL/unknown 32개 재탐지(unknown=32), WooCommerce 후보(ARKnets/COEVO/HBX) 수집 시도 0건. 수집 불가/저우선 22개 비활성화 적용으로 활성 NULL platform 32→10 달성. 감사 보고서 reports/null_platform_audit_2026-03-02.md 생성.
- 2026-03-03 00:00:00 | agent:codex-dev | task:T-20260303-072 | action:complete | message:INTEL_HUB_SPRINT0_01 완료: .env.example에 Intel 환경변수 4개 추가, intel.py 라우터/main.py 등록, 스케줄러 스텁 반영. (npm registry DNS 제약으로 maplibre-gl CDN 방식으로 임시 구현)
- 2026-03-03 00:00:00 | agent:codex-dev | task:T-20260303-073 | action:complete | message:INTEL_HUB_DATA_MODEL_01 완료: Alembic f1a2b3c4d5e6으로 intel_events/sources/ingest_runs/logs 4개 테이블 생성. ingest_intel_events.py mirror job(drops/collabs/news, inserted=34). /intel/events,map-points,timeline,highlights,events/{id} API 구현(cursor pagination, bbox, granularity).
- 2026-03-03 00:00:00 | agent:codex-dev | task:T-20260303-074 | action:complete | message:INTEL_HUB_FRONTEND_01 완료: /intel 페이지(레이어 토글, 시간 필터, 검색, URL deep link), 가상 스크롤 피드, stacked 타임라인, IntelMap.tsx(Maplibre), 상세 드로어(compare/watchlist 버튼), Nav에 Intel 메뉴 추가.
- 2026-03-03 00:00:00 | agent:codex-dev | task:T-20260303-075 | action:complete | message:INTEL_HUB_DERIVED_EVENTS_01 완료: upsert_product()에 availability_transition 반환 추가, crawl_products.py에 sale_start/sold_out/restock 파생 이벤트 훅 연결. derived_spike 잡 구현(실행 500건 삽입). scheduler intel_ingest_0730 잡 활성화. /admin/intel-status API + Admin UI 반영.
- 2026-03-03 00:00:00 | agent:codex-dev | task:T-20260303-076 | action:complete | message:INTEL_HUB_DERIVED_EVENTS_FIX_01 완료: _pick_sales_spike_candidates() 7d baseline delta 조건(sale_count>=15, ratio_delta>=0.15 OR discount_delta>=0.10) 추가. _calc_sale_start_severity()(discount_rate 기반 critical/high/medium/low) 및 calc_confidence_score() 유틸 추가. upsert_derived_product_event() geo_precision 명시 설정. crawl_products.py sale_start details에 discount_rate 전달.
- 2026-03-03 00:00:00 | agent:claude-pm | task:- | action:log | message:Phase 26 마무리: IntelMap CDN→npm(maplibre-gl@4.7.1) 전환, intel/page.tsx useSearchParams Suspense 경계 수정, 빌드 검증 완료. CLAUDE.md/MEMORY.md/WORK_LOG.md 전체 최신화.

- 2026-03-07 15:14:01 | agent:codex-dev | task:T-20260307-081 | action:log | message:T-081~T-086 구현 착수: Railway 설정, health DB ping, admin 토큰 가드, init_db 제거, 파티션 자동 생성, heartbeat 알림 반영 시작

- 2026-03-07 15:16:27 | agent:codex-dev | task:T-20260307-081 | action:complete | message:RAILWAY_CONFIG_CODIFY_01 완료: railway.json에 API startCommand/healthcheck 복원, docs/DEPLOYMENT.md에 railway.api.json/railway.worker.json Config File Path 설정 절차와 재배포 방법 반영

- 2026-03-07 15:16:31 | agent:codex-dev | task:T-20260307-082 | action:complete | message:PARTITION_AUTO_CREATE_01 완료: scripts/manage_partitions.py 추가, 다음 해 및 2028 파티션 idempotent 생성 로직 구현, scheduler에 매년 12월 1일 03:30 유지보수 잡과 startup 즉시 실행 반영

- 2026-03-07 15:16:35 | agent:codex-dev | task:T-20260307-083 | action:complete | message:REMOVE_INIT_DB_01 완료: API lifespan에서 init_db 호출 제거, database.py 주석을 로컬 SQLite 전용으로 정리, AGENTS.md와 DEPLOYMENT.md에 alembic upgrade head 선행 실행 가이드 추가

- 2026-03-07 15:16:39 | agent:codex-dev | task:T-20260307-084 | action:complete | message:ADMIN_TOKEN_GUARD_01 완료: admin_bearer_token 기본값을 제거하고, API_DEBUG=false + PostgreSQL 환경에서 change-me 또는 빈 토큰이면 RuntimeError로 서버 시작 차단하도록 model_validator 추가

- 2026-03-07 15:16:42 | agent:codex-dev | task:T-20260307-085 | action:complete | message:SCHEDULER_HEARTBEAT_01 완료: alert_service에 send_heartbeat_alert 추가, scheduler에 매일 09:05 KST heartbeat 잡 등록, 마지막 완료 크롤 시각과 다음 예정 작업 목록을 Discord로 전송하도록 구현

- 2026-03-07 15:16:46 | agent:codex-dev | task:T-20260307-086 | action:complete | message:HEALTH_DB_PING_01 완료: /health 엔드포인트에 AsyncSessionLocal + SELECT 1 DB ping 추가, 연결 실패 시 HTTP 503 database unavailable 반환, 정상 시 status/database 필드 응답

- 2026-03-07 15:16:49 | agent:codex-dev | task:T-20260307-087 | action:log | message:catalog_service.py에 기존 미커밋 변경이 이미 존재해 T-087 구현/커밋을 보류함. 현재 변경 내용 확인 후 사용자 지시가 필요함

- 2026-03-07 15:20:30 | agent:codex-dev | task:T-20260307-087 | action:complete | message:CATALOG_BOOL_OR_DEPLOY_01 완료: catalog_service에 PostgreSQL BOOL_OR + COALESCE 반영, SQLite fallback 및 last-crawl datetime 정규화 보완, build_product_catalog --since-last-crawl dry-run 검증 완료. Railway CLI 부재로 재배포 확인은 이 세션에서 미수행

- 2026-03-07 15:44:07 | agent:codex-dev | task:T-20260307-088 | action:log | message:T-088 착수: JPY 가격 오염 정리(정리 스크립트, 경쟁 페이지 하한 필터, Shopify 실제 통화 조회, MIN_KRW 상향) 구현 시작

- 2026-03-07 15:59:50 | agent:codex-dev | task:T-20260307-089 | action:log | message:T-089 착수: railway.json 공용 최소 설정으로 축소하고 DEPLOYMENT.md에 Config File Path 필수 경고 추가 시작

- 2026-03-07 16:00:19 | agent:codex-dev | task:T-20260307-089 | action:complete | message:SCHEDULER_WORKER_CRASH_FIX_01 완료: railway.json을 공용 기본 설정(builder + restart 정책만 유지)으로 되돌리고, API/Worker startCommand는 railway.api.json/railway.worker.json에만 남기도록 정리. DEPLOYMENT.md에 Config File Path 수동 설정 필수 경고 추가
- 2026-03-07 16:26:00 | agent:codex-dev | task:T-20260307-088 | action:log | message:T-088 진행 업데이트: Railway PostgreSQL에서 이전 세션이 남긴 idle-in-transaction 락 세션 5개 정리 후 DIGAWEL 단일 재검증 Run#18 성공(564개, ProductCatalog updated=510). `crawl_products.py` 저장 경로에 vendor/url/latest-price 일괄 조회 적용 및 `--no-intel` 시 per-product derived intel event 생성을 스킵하도록 정리. JP 전체 재크롤 Run#19 재시작, 현재 12/48 완료(new=9 updated=1841 error=5).
- 2026-03-07 16:44:00 | agent:codex-dev | task:T-20260307-090 | action:complete | message:CRAWL_TX_TIMEOUT_01 완료: `crawl_products.py`에 PostgreSQL 전용 `_apply_crawl_db_timeouts()`(`idle_in_transaction_session_timeout=60s`, `lock_timeout=5s`, `statement_timeout=120s`)와 `_classify_db_error()`를 추가하고, 크롤 세션/로그 갱신/CrawlRun 갱신 세션에 적용. save 단계 DB 예외를 `lock_timeout`/`statement_timeout`으로 분류하도록 수정. Railway PostgreSQL에서 `SHOW`로 timeout 값 검증 및 롤백-only row lock 재현으로 `lock_timeout` 분류 확인.
- 2026-03-07 17:34:00 | agent:codex-dev | task:T-20260307-091 | action:complete | message:CRAWL_BULK_WRITE_01 완료: `crawl_products.py` PostgreSQL 저장 경로를 products bulk upsert + price_history bulk insert로 전환하고, `product_service.py`에 row builder helper를 추가. bind parameter 초과 방지를 위해 제품 500건/price_history 1000건 chunking 반영. Railway 검증: Run#20(DIGAWEL 564), Run#23(NUBIAN 4000), Run#25~30/32~34 재실행으로 대형 JP 채널 저장 성공 확인.
- 2026-03-07 17:34:30 | agent:codex-dev | task:T-20260307-092 | action:complete | message:CRAWL_POST_COMMIT_PIPELINE_01 완료: 채널 저장 함수가 `ChannelPostCommitWork`만 수집하도록 변경하고, catalog 증분 빌드 / 파생 intel event / Discord 알림을 commit 이후 `run_channel_post_commit_pipeline()` 및 `run_post_commit_pipeline()`에서 별도 세션과 try/except로 격리 실행하도록 분리. DIGAWEL/JP 재크롤 검증에서 저장 트랜잭션 내 inline 후처리 제거 확인.
- 2026-03-07 17:35:00 | agent:codex-dev | task:T-20260307-088 | action:complete | message:T-088 완료: JPY 오염 `price_history` 15,757건 삭제, 경쟁 페이지 min_price>=10,000 하한/Shopify 실제 통화 조회/MIN_KRW 1,000 적용 후 JP 재크롤 재검증 마무리. 최신 채널 상태 확인 결과 `unexpected store` Run#32 success(4000개), `NƏW LIGHT` Run#33 success(540개), `fazeone` Run#34 success(502개)로 남은 실패 채널 모두 정상화.
- 2026-03-07 18:05:00 | agent:codex-dev | task:T-20260307-093 | action:complete | message:PRICE_CHART_01 완료: frontend에 `recharts` 설치 후 `PriceHistoryChart` 컴포넌트 추가, `/compare/[key]`를 server wrapper + client chart 구조로 재편, 30일/90일/전체 토글과 채널별 라인/tooltip/역대 최저가 표시 반영. `npm run build` 검증 통과.
- 2026-03-07 18:05:30 | agent:codex-dev | task:T-20260307-094 | action:complete | message:PRICE_BADGE_01 완료: 백엔드 `/products/price-badge/{product_key}` 및 `/products/keys` 추가, 프론트 `PriceBadge` 컴포넌트를 `/sales`, `/compare/[key]`, 대시보드, 브랜드 상세 카드에 적용. Railway PostgreSQL 실데이터 검증에서 sample badge 응답 및 compare summary 정상 확인.
- 2026-03-07 18:06:00 | agent:codex-dev | task:T-20260307-096 | action:complete | message:SEO_01 완료: `/compare/[key]`, `/brands/[slug]` 동적 metadata/OG 반영, compare Product JSON-LD 추가, `sitemap.ts`/`robots.ts` 구현, layout metadataBase 설정. 외부 Google Fonts fetch 제거로 sandbox/CI 환경에서도 `npm run build` 성공하도록 정리.
- 2026-03-07 18:06:30 | agent:codex-dev | task:T-20260307-095 | action:complete | message:RANKING_01 완료: 백엔드 `/products/ranking`(sale_hot/price_drop)와 `/brands/ranking` 구현, 프론트 `/ranking` 탭 UI와 메인 `오늘의 HOT 세일 TOP 10`, Nav `랭킹` 메뉴 추가. Railway PostgreSQL 검증에서 sale_hot/price_drop/brand ranking 샘플 결과 확인.
- 2026-03-08 00:20:00 | agent:codex-dev | task:T-20260308-097 | action:complete | message:REMOVE_PRICE_HISTORY_UI_01 완료: `/products/price-history/*`, `/products/price-badge/*` 및 `product_service`의 대응 함수 제거, compare 페이지를 현재가 비교 테이블 중심으로 단순화. 프론트 `PriceBadge`/`PriceHistoryChart` 제거, 관련 타입/API 호출/`recharts` 의존성 정리 후 `npm run build` 성공 및 FastAPI route 확인(`/feed` 존재, 삭제 경로 미등록).
- 2026-03-08 00:26:00 | agent:codex-dev | task:T-20260308-098 | action:complete | message:FEED_SKELETON_01 완료: 기존 `intel_events`를 임시 activity feed로 매핑하는 `feed_service.py`/`api/feed.py` 추가. 프론트 `/feed` 페이지에 30초 폴링, 이벤트 타입 필터, 더 보기 버튼, compare/source 링크를 구현하고 Nav에 `실시간 피드` 메뉴 추가.
- 2026-03-08 00:31:00 | agent:codex-dev | task:T-20260308-099 | action:complete | message:CHANNEL_DISCOVERY_01 완료: `scripts/discover_channels.py` 추가(OpenAI `gpt-4o` 기반 후보 생성 → `channel_probe.probe_channel()` 검증 → `is_active=False` draft 저장). `/admin/channels?status=draft`, `/admin/channels/{id}/activate` API와 Admin draft 승인 UI 반영. `pyproject.toml`/`uv.lock`에 `openai` 의존성 반영 및 `uv sync` 완료.
- 2026-03-08 01:25:00 | agent:codex-dev | task:T-20260308-106 | action:complete | message:RANKING_SIGNAL_01 완료: `get_product_ranking()` sale_hot을 `sale_started_at` 기반 urgency score 정렬로 재정의하고, `price_drop` 랭킹은 `activity_feed.price_cut` 최신 이벤트를 기준으로 집계하도록 전환. `get_brand_sale_ranking()`도 최근 72시간 이벤트 수 중심으로 재작성하고 `/ranking` 브랜드 탭에 `72h 이벤트` 컬럼 추가. 검증: `uv run python -m compileall src scripts`, `npm run build -- --webpack` 통과.
- 2026-03-08 01:25:30 | agent:codex-dev | task:T-20260308-107 | action:complete | message:URGENCY_BADGES_01 완료: `watch_agent.py`가 feed metadata에 image/가격하락 정보를 함께 기록하도록 확장하고, ranking 응답/프론트 타입에 `badges`, `sale_started_at`, `hours_since_sale_start` 추가. `/ranking`과 홈 HOT 카드에 `방금 세일`/`멀티채널`/`한정판` 배지와 세일 시작 시각 문구 반영.
- 2026-03-08 01:48:00 | agent:codex-dev | task:T-20260308-108 | action:complete | message:GPT_FALLBACK_CRAWLER_01 완료: `crawler/gpt_parser.py` 추가(`gpt-4o-mini` 기반 HTML→제품 JSON), `ProductCrawler.crawl_channel()`에 unknown/use_gpt_parser 채널용 GPT fallback 연결. `channels.use_gpt_parser` 컬럼/Alembic `29c0d1e2f3a4` 추가 및 Admin 채널 관리에 GPT fallback ON/OFF 저장 UI/API 반영. 검증: `uv run python -m compileall src scripts`, `npm run build -- --webpack` 통과. 실 OpenAI 호출은 네트워크 제한으로 미검증.
- 2026-03-08 01:48:30 | agent:codex-dev | task:T-20260308-109 | action:complete | message:GPT_ACTIONS_FEED_01 완료: `FeedIngestIn` + `POST /feed/ingest` 엔드포인트 추가, `GPT_ACTIONS_API_KEY`(`X-API-Key`) 인증 적용, `feed_service.ingest_activity_feed()` 구현, `openapi_gpt_actions.yaml` 생성. 검증: feed router path(`/feed`, `/feed/ingest`) 확인 및 임시 SQLite smoke test에서 feed ingest/sale_hot/price_drop/brand ranking 응답 확인.
