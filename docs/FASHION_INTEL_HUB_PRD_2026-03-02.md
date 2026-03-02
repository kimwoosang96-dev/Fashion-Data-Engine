# Fashion Intel Hub 통합 기획서 (v1.0)

- 작성일: 2026-03-02
- 작성자: Codex
- 기준 프로젝트: Fashion Data Engine (FastAPI + Next.js 16)
- 참고 레퍼런스: `worldmonitor` (지도 중심 + 레이어 토글 + 시간축 탐색)

---

## 1) 문서 목적

현재 분산된 뉴스성 탭(인스타/드랍/협업/뉴스)을 **단일 인텔리전스 허브(Intel Hub)** 로 통합한다.  
핵심 목표는 다음 3가지다.

1. 패션 이벤트를 한 화면에서 탐색 가능하게 만들기
2. 단순 리스트가 아닌 **지도+타임라인+시그널** 중심으로 인사이트 제공
3. 운영 관점에서 이벤트 적재/정규화/검증 체계를 표준화

---

## 2) 배경 및 문제 정의

### 2.1 현재 문제

1. 정보 분산
- `drops`, `collabs`, 뉴스성 데이터가 탭별로 분리되어 사용자 탐색 비용이 큼

2. 시계열 맥락 부재
- “최근 7일 동안 어떤 지역/브랜드/채널에서 이벤트가 몰렸는지”를 한눈에 보기 어려움

3. 운영 비효율
- 데이터 소스별 포맷 차이로 중복 저장/표준화 이슈 발생

4. 제품 의사결정 연결 부족
- 이벤트 정보와 실제 제품/가격/세일 신호의 연결이 약함

### 2.2 기회

- 기존에 이미 보유한 `products`, `drops`, `brand_collaborations`, `price_history`를 이벤트로 재조합하면
  - “어디서 무엇이 일어났고”
  - “가격/판매 상태에 어떤 영향이 있었는지”
  - “다음 액션(구매/관심등록)이 무엇인지”
  를 즉시 제시할 수 있음.

---

## 3) 벤치마크 요약: worldmonitor에서 가져올 구조

### 3.1 그대로 차용할 요소

1. 단일 허브형 인터랙션
- 지도(공간) + 시간 필터(시계열) + 레이어(주제 분류) 조합

2. 레이어 토글 기반 정보 밀도 제어
- 사용자 관심 레이어만 켜서 노이즈 감소

3. 카드/핀 동기화
- 목록 클릭 시 지도 이동, 지도 클릭 시 상세 카드 오픈

4. 글로벌 뷰 -> 상세 드릴다운
- 전체 상황 -> 브랜드/채널/도시 단위 탐색

### 3.2 패션 도메인에 맞게 변경할 요소

1. 군사/재난 레이어 -> 패션 이벤트 레이어
2. 충돌 강도 -> 이벤트 신뢰도/상업적 영향도
3. 단순 사건 설명 -> 제품 링크/가격 신호/판매 상태 연동

---

## 4) 제품 목표와 KPI

### 4.1 제품 목표

1. 인텔 탭 1개에서 이벤트 탐색 완료
2. 이벤트에서 제품 행동 전환(비교/관심/구매등록) 유도
3. 데이터 운영 자동화(정규화 + 중복제거 + 신뢰도 관리)

### 4.2 KPI (출시 후 4주)

1. 탐색 효율
- `Intel` 탭 평균 체류 시간: +35% 이상
- 세션당 이벤트 상세 진입 수: +40% 이상

2. 행동 전환
- Intel -> `compare/[key]` 이동률: 8% 이상
- Intel -> watchlist 추가율: 5% 이상

3. 데이터 품질
- 이벤트 중복률: 3% 미만
- 소스 파싱 실패율: 5% 미만
- 지오코딩 실패율: 10% 미만

---

## 5) 정보 구조(IA) 및 사용자 시나리오

### 5.1 IA 개편

기존:
- News / Drops / Collabs / (인스타성 피드)

개편:
- `Intel` (통합 허브)
- 기존 탭은 1차 릴리즈에서 유지하되 `Intel`로 교차 링크 제공
- 2차 릴리즈에서 기존 탭 축소 또는 읽기전용 아카이브 전환

### 5.2 주요 사용자 시나리오

1. 바이어
- 최근 7일 `Drops + Sales Spike` 레이어만 켜고, 아시아 지역 이벤트만 확인
- 이벤트 상세에서 채널별 가격 비교로 이동

2. 리셀/컬렉터
- 특정 브랜드 필터 후 `Restock`과 `Sold Out` 이벤트 추적
- 관심 제품을 watchlist에 추가

3. 콘텐츠 운영자
- `Collabs` 레이어에서 신뢰도 높은 이벤트만 추출
- 카드 기반으로 리포트 작성

---

## 6) 레이어 체계 설계

### 6.1 레이어 정의 (v1)

1. `drops`
- 공식/준공식 발매 일정, 출시 이벤트

2. `collabs`
- 브랜드 협업 발표/티저/출시

3. `sales_spike`
- 단기 할인 급증 이벤트 (예: 48시간 내 할인 상품 급증)

4. `restock`
- 품절 상품 재입고 감지

5. `sold_out`
- 출시 직후 또는 특정 기간 내 품절 전환 감지

6. `brand_posts`
- 브랜드 공식 채널(인스타 등)의 중요 게시 신호

### 6.2 이벤트 중요도(Severity) 규칙

- `critical`: 글로벌 협업 발표, 대규모 드롭, 광범위 품절
- `high`: 특정 주요 브랜드의 대형 이벤트
- `medium`: 일반 출시/재입고
- `low`: 보조성 소식

### 6.3 신뢰도(Confidence) 규칙

- `high`: 공식 사이트/API/공식 계정 직접 출처
- `medium`: 다수 신뢰 소스 교차 확인
- `low`: 단일 비공식 출처

---

## 7) 데이터 모델 설계

## 7.1 신규 테이블: `intel_events`

권장 컬럼:

1. 식별/분류
- `id` (PK)
- `event_type` (`drop|collab|sales_spike|restock|sold_out|brand_post`)
- `layer` (UI 토글용, event_type과 동일 또는 세분화)

2. 시간
- `event_time` (실제 사건 시각, nullable)
- `detected_at` (수집 시각)
- `updated_at`

3. 주체
- `brand_id` (nullable)
- `channel_id` (nullable)
- `product_id` (nullable)
- `product_key` (nullable)

4. 위치/지리
- `geo_country` (ISO2)
- `geo_city`
- `geo_lat`
- `geo_lng`
- `geo_precision` (`global|country|city|point`)

5. 콘텐츠
- `title`
- `summary`
- `details_json` (추가 메타)
- `source_url`
- `source_domain`
- `source_type` (`official|media|social|crawler`)
- `source_published_at` (nullable)

6. 품질/상태
- `severity` (`low|medium|high|critical`)
- `confidence` (`low|medium|high`)
- `dedup_key` (UNIQUE 후보)
- `is_active` (기본 true)
- `is_verified` (운영 검수 플래그)

7. 감사
- `created_by` (`system|admin`)
- `ingest_job_id` (nullable)

### 7.2 인덱스 전략

1. `idx_intel_events_time` on (`event_time DESC`, `detected_at DESC`)
2. `idx_intel_events_layer_time` on (`layer`, `event_time DESC`)
3. `idx_intel_events_brand_time` on (`brand_id`, `event_time DESC`)
4. `idx_intel_events_channel_time` on (`channel_id`, `event_time DESC`)
5. `uq_intel_events_dedup_key` unique (`dedup_key`)
6. 좌표 조회 최적화 필요 시 Postgres에서 GIS 인덱스(후속)

### 7.3 기존 테이블과 관계

1. `drops` -> `intel_events`로 미러링(양방향 참조 또는 단방향 파생)
2. `brand_collaborations` -> 이벤트 생성
3. `products`/`price_history` -> `sales_spike`, `restock`, `sold_out` 파생
4. 기존 기능 보존을 위해 당분간 원본 테이블 유지

---

## 8) 이벤트 생성 파이프라인(ETL/ELT)

### 8.1 파이프라인 단계

1. Collect
- 크롤러/API/RSS/SNS 소스 수집

2. Normalize
- 공통 스키마로 매핑(`event_type`, `time`, `brand/channel/product`, `source`)

3. Enrich
- 브랜드/채널 매핑, 지오코딩, 중요도/신뢰도 부여

4. Dedup
- `dedup_key` 기준 병합
- 유사도 기준(제목+시간창+브랜드) 2차 중복 제거

5. Persist
- `intel_events` upsert

6. Serve
- API 캐시(짧은 TTL), 클라이언트 필터 제공

### 8.2 dedup_key 규칙 예시

`{event_type}:{brand_slug_or_na}:{channel_id_or_na}:{normalized_title_hash}:{event_date_bucket}`

### 8.3 실패 처리

1. 파싱 실패: `logs/intel_ingest_failures.log` 적재
2. 지오코딩 실패: 국가 단위 fallback
3. 브랜드 매핑 실패: `brand_id=NULL` 허용 + 후속 매핑 큐 삽입

---

## 9) API 설계 (FastAPI)

### 9.1 신규 엔드포인트

1. `GET /intel/events`
- 쿼리:
  - `layers` (csv)
  - `time_range` (`24h|7d|30d|90d|custom`)
  - `brand_slug`
  - `channel_id`
  - `country`
  - `q`
  - `min_confidence`
  - `limit`, `offset`
- 응답:
  - 이벤트 리스트 + 총계 + 레이어별 카운트

2. `GET /intel/map-points`
- 지도 렌더링 최소 필드 응답(좌표, severity, type, id)

3. `GET /intel/timeline`
- 날짜 버킷별 이벤트 카운트
- 레이어별 stacked 데이터 포함

4. `GET /intel/events/{id}`
- 상세 카드 데이터(연결 제품/브랜드/채널/원문 링크)

5. `GET /intel/highlights`
- 우선순위 상위 이벤트 요약

### 9.2 내부용 엔드포인트 (옵션)

1. `POST /intel/admin/rebuild`
- 기간 재색인

2. `POST /intel/admin/verify/{id}`
- 수동 검증 플래그 처리

---

## 10) 프론트엔드 설계 (Next.js 16)

### 10.1 신규 페이지

- `frontend/src/app/intel/page.tsx`

### 10.2 화면 구성

1. Top Control Bar
- time range
- 레이어 토글
- 브랜드/채널 검색
- confidence/severity 필터

2. Main Layout
- 좌측: Event Feed (가상 스크롤)
- 중앙: World/Region Map
- 하단 또는 우측: Timeline

3. Detail Panel (drawer/modal)
- 이벤트 요약, 출처, 관련 제품, 가격 비교 이동 버튼

### 10.3 컴포넌트 분해

1. `IntelLayerFilter.tsx`
2. `IntelMap.tsx`
3. `IntelTimeline.tsx`
4. `IntelEventFeed.tsx`
5. `IntelEventCard.tsx`
6. `IntelEventDetailDrawer.tsx`

### 10.4 기존 페이지 연동

1. `Nav.tsx`에 `Intel` 추가
2. `drops`, `collabs` 페이지 상단에 “Intel에서 통합 보기” 링크
3. 이벤트 상세에서 `/compare/[key]`, `/brands/[slug]`, `/channels` 이동

---

## 11) 지도 기술 선택안

### 11.1 후보

1. Mapbox GL JS
- 장점: 성능/스타일 우수, 대량 포인트 처리 유리
- 단점: 토큰/비용 관리 필요

2. Leaflet
- 장점: 단순/가벼움, 러닝커브 낮음
- 단점: 대규모 데이터 처리 한계

3. deck.gl + Maplibre
- 장점: 고밀도 시각화/애니메이션 강점
- 단점: 초기 구현 난이도 높음

### 11.2 권장

- v1: `Maplibre + react-map-gl` 또는 `Leaflet`로 빠르게 출시
- v2: 대량 이벤트에서 성능 이슈 발생 시 `deck.gl` 레이어로 고도화

---

## 12) 성능/캐시 전략

### 12.1 백엔드

1. 리스트 API는 필드 최소화
2. `time_range + layers + country` 조합 캐시(30~120초)
3. 타임라인/맵 API 분리로 payload 축소

### 12.2 프론트엔드

1. 초기 로드: highlights + map-points 우선
2. 피드 지연 로딩/무한스크롤
3. URL query 상태 동기화로 공유 가능한 탐색 링크 제공

---

## 13) 운영/품질 관리

### 13.1 운영 대시보드 지표

1. ingestion 성공률
2. 레이어별 이벤트 수
3. 중복 제거율
4. brand/channel 매핑 누락률
5. 소스별 신뢰도 분포

### 13.2 데이터 검수 플로우

1. low confidence 이벤트는 운영 큐로 분리
2. 운영자가 `is_verified=true` 처리 가능
3. 검수 완료 이벤트 우선 노출(옵션)

---

## 14) 보안/법적 고려사항

1. 소셜/외부 콘텐츠는 원문 전문 저장 최소화
2. `source_url` 중심 참조, 저작권 침해 방지
3. robots.txt/약관 위반 크롤링 금지
4. API rate limit/백오프 준수

---

## 15) 구현 로드맵 (4주)

### Sprint 1 (주 1)

1. DB 마이그레이션: `intel_events` 생성
2. 기본 ingest 스크립트 초안
3. `/intel/events`, `/intel/map-points` API
4. 프론트 `Intel` 페이지 기본 레이아웃

산출물:
- Alembic revision
- API 스키마/타입 정의
- 기본 지도+피드 화면

### Sprint 2 (주 2)

1. `drops/collabs` 미러링 파이프라인
2. dedup 규칙 1차
3. 타임라인 API + UI
4. 상세 드로어 + compare 연동

산출물:
- 통합 이벤트 조회 가능
- 기존 탭과 크로스 링크

### Sprint 3 (주 3)

1. sales_spike/restock/sold_out 파생 로직
2. confidence/severity 고도화
3. 캐시/성능 최적화
4. 운영 검수 플로우(내부용)

산출물:
- 상업 신호 레이어 완성
- 운영 안정화

### Sprint 4 (주 4)

1. A/B or staged rollout
2. KPI 측정 대시보드 반영
3. 문서/플레이북 업데이트
4. 기존 분리 탭 축소 계획 확정

산출물:
- 프로덕션 적용 판단 자료
- 최종 운영 가이드

---

## 16) 작업 분해(WBS)

### 16.1 Backend

1. 모델/마이그레이션
2. 이벤트 생성 서비스
3. 검색/필터 API
4. 품질 규칙(dedup/confidence)
5. 운영용 관리 API

### 16.2 Frontend

1. Intel 페이지 라우트
2. 지도 + 클러스터 렌더링
3. 레이어 토글/필터 상태관리
4. 피드/타임라인 동기화
5. 상세 패널 + 액션 버튼

### 16.3 Data Ops

1. 소스 커넥터 유지보수
2. 지오코딩 fallback 룰
3. 실패 로그 모니터링
4. 매핑 누락 정제 작업

---

## 17) QA 및 테스트 전략

### 17.1 백엔드 테스트

1. 이벤트 정규화 단위 테스트
2. dedup_key 충돌/병합 테스트
3. API 필터 조합 테스트
4. 대량 데이터 페이징 테스트

### 17.2 프론트엔드 테스트

1. 레이어 토글 시 맵/피드 동기화
2. 타임레인지 변경 시 API 재요청
3. 카드 클릭 -> 상세 -> compare 이동 경로
4. 모바일 레이아웃/성능 점검

### 17.3 E2E 시나리오

1. 7일 데이터 조회 -> 특정 브랜드 필터 -> 이벤트 상세 -> 가격 비교 이동
2. sold_out 이벤트에서 재입고 이벤트까지 추적

---

## 18) 리스크 및 대응

1. 이벤트 품질 편차
- 대응: confidence 도입 + 운영 검수 큐

2. 지리 정보 부정확
- 대응: 도시 실패 시 국가 단위 fallback + precision 표기

3. 지도 렌더링 성능
- 대응: map-points 전용 API, 클러스터링, 단계적 고도화

4. 소스 정책 변경
- 대응: 커넥터 분리 구조 + 장애 감지 알림

---

## 19) 적용 파일 가이드 (예상)

백엔드:

1. `src/fashion_engine/models/intel_event.py` (신규)
2. `src/fashion_engine/models/__init__.py` (등록)
3. `src/fashion_engine/services/intel_service.py` (신규)
4. `src/fashion_engine/api/intel.py` (신규)
5. `src/fashion_engine/api/main.py` (router 등록)
6. `scripts/ingest_intel_events.py` (신규)
7. `alembic/versions/*_create_intel_events.py`

프론트:

1. `frontend/src/app/intel/page.tsx`
2. `frontend/src/components/intel/*`
3. `frontend/src/lib/types.ts` (intel 타입 추가)
4. `frontend/src/lib/api.ts` (intel API 함수 추가)
5. `frontend/src/components/Nav.tsx` (메뉴 추가)

문서:

1. `docs/FASHION_INTEL_HUB_PRD_2026-03-02.md` (본 문서)
2. `agents/TASK_DIRECTIVE.md` (추가 이슈 등록 시)
3. `agents/WORK_LOG.md` (작업 이력)

---

## 20) 최종 제안

`worldmonitor` 스타일의 강점은 “복잡한 이벤트를 한 화면에서 탐색하게 하는 정보구조”다.  
Fashion Data Engine에서는 이를 다음 원칙으로 구현하는 것이 가장 효과적이다.

1. 데이터 원천은 분리하되, 사용자 경험은 `Intel`로 통합
2. 지도/타임라인/레이어를 표준 인터랙션으로 고정
3. 이벤트를 제품/가격/구매 의사결정으로 반드시 연결
4. 운영 검수 체계를 내장해 데이터 신뢰도 유지

이 방식으로 진행하면, 기존 뉴스성 탭의 단절을 해소하고 플랫폼의 핵심 가치(탐색 -> 비교 -> 액션)를 한 경로로 결합할 수 있다.
