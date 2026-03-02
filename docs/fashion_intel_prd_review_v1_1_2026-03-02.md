# Fashion Intel Hub PRD 평가 및 보완안 (v1.1)

- 기준 문서: `FASHION_INTEL_HUB_PRD_2026-03-02.md` (v1.0)
- 참고 레퍼런스: `koala73/worldmonitor` (지도 + 레이어 토글 + 시간축 탐색 + “빠르게 보여주고(instant render) 나중에 정교화” 철학)

> 목적: 현재 PRD의 **강점은 유지**하면서, 실제 구현/운영 단계에서 막히기 쉬운 **빈 구멍(데이터 소스/정의/지오/중복/성능/운영/보안)** 을 메우는 “실행 가능한” 보완안을 제시한다.

---

## 0. 결론 요약

현재 PRD는 **“Intel 탭 하나로 이벤트를 지도+타임라인+레이어로 탐색한다”**는 방향성이 명확하고, 데이터 모델(`intel_events`)과 API 스펙도 비교적 구체적이다.

다만, 다음 6가지가 보완되지 않으면 **실제 출시에서 품질/속도/운영이 흔들릴 가능성**이 크다.

1. **레이어별 데이터 소스/생성 규칙이 불명확** (drops/collabs는 가능하지만, sales_spike/restock/sold_out/brand_posts는 규칙·임계치·근거가 필요)
2. **‘뉴스’ 이벤트가 레이어에서 누락** (문서 목적이 “뉴스성 탭 통합”인데 RSS News를 Intel로 가져오는 정의가 없음)
3. **지오(위치) 데이터의 현실성 부족** (브랜드/채널에 city/lat/lng가 없는 상태에서 map UX가 “글로벌 핀 난사”가 될 위험)
4. **Dedup(중복 제거) 설계가 1단계 수준** (dedup_key 1개로는 소스/언어/시간차 중복을 다루기 어려움)
5. **운영/품질(ingest run, 오류 분류, 소스 freshness) 관측 체계가 부족** (크롤러처럼 “실패 유형/성공률/신선도”가 있어야 운영 가능)
6. **성능 스펙이 더 필요** (피드 무한스크롤, 맵 포인트 대량 렌더링, 타임라인 집계는 병목이 쉽게 생김)

아래 보완안을 적용하면, v1은 “작동하는 Intel”을 빠르게 만들고, v2에서 고도화(정교한 지오/AI 요약/추론)를 안전하게 확장할 수 있다.

---

## 1) PRD 강점 평가 (유지할 점)

### 1.1 제품 방향성
- 단일 허브: 지도(공간) + 시간축(시계열) + 레이어(주제) 조합은 worldmonitor의 핵심 성공 패턴과 일치
- “탐색 → 비교 → 액션(관심등록/구매)” 전환을 목표로 둔 점이 Fashion Data Engine의 강점(가격 비교/세일 시그널)과 잘 맞음

### 1.2 기술 설계
- `intel_events` 단일 테이블로 시작하는 방향은 v1에 적합
- API를 `events / map-points / timeline / highlights`로 분리한 것은 payload 절약 및 성능에 유리
- confidence/severity 개념 도입은 운영/품질에서 매우 중요

---

## 2) 가장 큰 결손: “레이어별 정의”와 “생성 규칙”

현재 PRD는 레이어를 나열했지만, 실제 시스템에서는 **“이벤트 생성 규칙이 곧 제품 품질”**이다.

### 2.1 레이어(=UI 토글)와 이벤트 타입(=도메인 의미) 분리 제안

- `event_type`: 도메인 의미(드롭/협업/세일시작/세일스파이크/품절/재입고/뉴스/소셜)
- `layer`: UI 토글을 위한 분류 (event_type과 1:1이 아니어도 됨)

**v1.1 추천 event_type**
- `drop` (예정/발매/리스트업)
- `collab` (협업)
- `sale_start` (세일 시작: is_sale False→True)
- `sales_spike` (세일 급증: “상품 수/할인폭/채널 수” 급격 변화)
- `restock` (재입고)
- `sold_out` (품절)
- `news` (RSS 뉴스)
- `brand_post` (공식 계정/공식 사이트 공지/소셜 신호)

> PRD 목적이 “뉴스성 탭 통합(인스타/드랍/협업/뉴스)”이므로, `news`는 v1 레이어에 포함하는 편이 자연스럽다.

---

## 3) 레이어별 “데이터 소스 + 이벤트 생성 규칙” (v1 현실형)

아래는 Fashion Data Engine이 **이미 보유한 테이블/크롤러**를 최대 활용해 “추가 의존성 없이” 만들 수 있는 규칙 중심 제안이다.

### 3.1 drop
**소스**
- 기존 `drops` 테이블 (drop_crawler 결과) 또는 `/drops` API

**생성 규칙**
- `drops.status`가 `upcoming|released|sold_out`으로 바뀌는 시점에 이벤트 생성/업데이트
- `event_time`은 `release_date`(있으면) + 없으면 `detected_at`

**기본 severity**
- upcoming: medium
- released: high
- sold_out: high (단, 저가/비인기 브랜드는 medium)

### 3.2 collab
**소스**
- 기존 `brand_collaborations` 테이블

**생성 규칙**
- 협업 추가 시점: event 생성
- `release_year`만 있고 날짜가 없으면 `event_time`은 `source_published_at` 또는 `detected_at`, `geo_precision=global` 권장

**severity/impact 스코어(권장)**
- `hype_score`를 severity로 매핑 (예: 0–30 low, 31–60 medium, 61–80 high, 81–100 critical)

### 3.3 sale_start (추천: sales_spike와 분리)
**소스**
- 기존 크롤러가 이미 감지하는 `is_sale` 전환 로직(Discord 알림과 동일한 조건)

**생성 규칙**
- 동일 `product_key` 또는 `normalized_key` 단위로:
  - `is_sale`이 `False → True`로 바뀐 경우 이벤트 생성
- `details_json`: `{discount_rate, price_krw, original_price_krw, channel_id}`

**severity**
- discount_rate ≥ 30%: high
- discount_rate ≥ 50%: critical
- 그 외: medium

### 3.4 sales_spike (“세일이 갑자기 많아졌다”)
**문제**
- 단일 제품 세일(sale_start)과 채널/브랜드 단위의 “스파이크”는 성격이 다름  
- 스파이크는 “상품 수/세일 비중/평균 할인율”이 급격히 변할 때 의미가 있음

**소스**
- `products`, `price_history`, `product_catalog`(가능하면) 기반 파생

**생성 규칙(현실형 v1)**
- 채널 단위(또는 브랜드 단위)로 48시간 롤링 윈도우에서:
  - `sale_count_48h` (is_sale=True 제품 수)
  - `sale_ratio_48h` (sale_count / active_count)
  - `avg_discount_48h` (discount_rate 평균)
- 기준선(baseline)은 간단히:
  - 지난 14일의 같은 요일 평균 또는 지난 7일 평균
- 트리거 예시:
  - `sale_count_48h >= 30` AND `sale_ratio_48h`가 baseline 대비 +15%p 이상
  - 또는 `avg_discount_48h`가 baseline 대비 +10%p 이상

**severity**
- delta가 클수록 high/critical
- “단일 채널”보다 “다수 채널에서 동시 발생”이면 severity 상향(컨버전스 개념)

> worldmonitor는 시계열 이상탐지(온라인 평균/분산, z-score) 같은 패턴을 사용한다. v2에서 고급 이상탐지로 확장 가능하지만, v1은 임계치 기반으로 빠르게 시작하는 것이 좋다.

### 3.5 sold_out
**소스**
- `products.archived_at` 또는 `is_active` 전환

**생성 규칙**
- “이전 크롤에서는 있었는데, 이번 크롤에서 사라짐”이 즉시 sold_out을 의미하진 않음(일시적 실패 가능)
- **안전한 v1 규칙**:
  - 동일 product 기준으로 `archived_at`이 NULL → NOT NULL 된 경우에만 sold_out 이벤트
  - 또는 “N회 연속 미발견(예: 3회)” 후 sold_out 처리 (CrawlChannelLog 기반으로 판단)

**severity**
- listing_count(판매 채널 수) 많을수록 상향
- 브랜드 tier가 높을수록 상향

### 3.6 restock
**소스**
- `archived_at` NOT NULL → NULL로 되돌아오는 경우(가능 시)
- 또는 “품절 상태였던 제품이 다시 발견” (N회 미발견 후 재등장)

**생성 규칙**
- (권장) sold_out과 “쌍”으로 관리: 같은 product_key/normalized_key에 대해 restock이 들어오면 sold_out 이벤트의 `is_active`를 false 처리하거나 group으로 묶음

### 3.7 news (PRD에 누락 — 보완 강력 권장)
**소스**
- 기존 RSS 수집 결과(`fashion_news`)를 Intel로 미러링
- 기존의 `crawl_news.py`의 feed(예: hypebeast, highsnobiety, sneakernews 등)를 그대로 사용

**생성 규칙**
- 새 news row가 들어오면 intel event 생성
- geo는 기본적으로 `global` 또는 “브랜드/채널이 매핑될 때만 country”로 제한

**confidence**
- source가 media면 기본 medium, 공식 press release면 high로 상향

### 3.8 brand_post (인스타/공식 게시물)
**현실 체크**
- Instagram은 공식 API/권한/정책/크롤링 제한이 큼 (약관/robots 준수 필요)
- v1에서 “인스타 크롤러”를 넣으면 리스크가 커지고 품질이 흔들릴 수 있음

**권장 v1 접근**
- v1: “공식 사이트 공지 / newsletter RSS / YouTube/Blog RSS” 등 **정식 피드 기반** 중심 + 운영자가 수동 입력(POST /admin)
- v2: 정책 준수 가능한 방식(공식 API, 제휴 데이터 등) 검토 후 확장

---

## 4) 데이터 모델 보완: “단일 테이블”을 유지하면서 운영 가능하게

PRD의 `intel_events`는 좋다. 다만 실제 운영을 위해 2가지가 더 필요하다.

1) **소스 다중화(한 이벤트가 여러 출처를 가질 수 있음)**  
2) **Ingest 관측(몇 개 만들었고, 얼마나 실패했는지)**

### 4.1 최소 확장안 A: `intel_events`에 sources 배열만 추가 (가벼움)
- `sources_json` (JSONB): `[{source_url, source_domain, source_type, source_published_at}]`
- 장점: 마이그레이션 가벼움, 구현 빠름
- 단점: 소스별 검색/통계/중복 확인이 불편

### 4.2 권장 확장안 B: `intel_event_sources` 테이블 추가 (정석)
- `intel_events`는 “canonical event”
- `intel_event_sources`는 “원천 레코드(다수 가능)”

**intel_event_sources (권장)**
- `id` (PK)
- `event_id` (FK → intel_events.id)
- `source_url` (UNIQUE 또는 event_id+source_url UNIQUE)
- `source_domain`, `source_type`, `source_published_at`
- `raw_title`, `raw_summary`, `raw_json`(옵션)
- `ingested_at`

> 이렇게 하면 dedup 이후에도 “왜 이 이벤트가 존재하는지(근거)”를 잃지 않는다.

### 4.3 운영 테이블: `intel_ingest_runs` / `intel_ingest_logs`
크롤러에 `CrawlRun/CrawlChannelLog`가 있듯이 Intel에도 “잡 단위” 기록이 있어야 한다.

**intel_ingest_runs**
- `id`, `job_name`(news/drops/collabs/derived)
- `started_at`, `finished_at`
- `status`(running/done/failed)
- `events_created`, `events_updated`, `sources_ingested`, `dedup_merged`
- `error_count`

**intel_ingest_logs**
- `run_id`, `source_type`, `source_url`
- `status`(success/failed/skipped)
- `error_type`(http_4xx, parse_error, mapping_error …)
- `duration_ms`

---

## 5) 지오(위치) 설계: “정확도(precision)”를 전제로 단계적 구축

PRD는 `geo_precision(global|country|city|point)`를 제안했는데, 실제로 이게 핵심이다.  
v1은 “완벽한 위도경도”가 아니라, **정확도 레벨을 사용자에게 솔직하게 보여주는 것**이 중요하다.

### 5.1 v1 위치 채우기 우선순위(현실형)

1. `channel_id`가 있으면 → `channels.country`를 활용해 country centroid로 핀 표시 (precision=country)
2. `brand_id`만 있으면 → `brand.origin_country` 또는 `official_url TLD` 기반 추정 (precision=country 또는 global)
3. `product_key`만 있으면 → 연결된 채널로 역추적 가능하면 (1)로
4. 아무것도 없으면 → global(지도 중앙 집계 카드로만 노출)

### 5.2 채널/브랜드에 “위치 필드”가 없다면?
- 가장 쉬운 방법: `channels` 테이블에 `geo_city`, `geo_lat`, `geo_lng`를 추가하고 수동/반자동 채움
- 더 정석: `channel_locations`(1:n) 테이블로 확장(멀티 지점 운영 채널 대비)

### 5.3 (옵션) PostGIS 도입 여부
- v1: float lat/lng + B-Tree 인덱스 + bbox 필터로도 충분
- v2: 포인트/폴리곤/거리 쿼리가 필요하면 PostGIS + GiST 인덱스 고려

---

## 6) Dedup(중복 제거) “2단계”로 강화

PRD의 `dedup_key`는 좋은 시작이지만, 현실에서는 아래 중복이 빈번하다.

- 같은 사건이 시간차로 여러 번 들어옴(티저/발매/품절/재입고)
- 같은 뉴스가 여러 매체/언어로 반복
- 제목이 약간 다름(“Drop” vs “Release”)

### 6.1 1차(Deterministic) dedup_key
예시:
`{event_type}:{brand_id|na}:{channel_id|na}:{product_key|na}:{date_bucket}:{title_hash}`

- date_bucket은 `YYYY-MM-DD` 또는 `YYYY-WW`(주차)
- title_hash는 “정규화된 title(소문자/공백 정리/불용어 제거)” 기반

### 6.2 2차(Fuzzy) merge: 유사도 + 시간 창
- 동일 `event_type` + 동일 brand 또는 동일 product_key 그룹 내에서
- 24~72시간 window 안에
- 토큰 기반 유사도(Jaccard) 또는 간단한 Levenshtein 임계치로 병합

### 6.3 “이벤트 그룹” 개념(선택)
- `intel_event_groups`를 두고 canonical을 지정하거나
- `intel_events.group_id`만 추가해 “같은 사건”을 묶을 수도 있음  
→ 지도에서는 group 단위로 클러스터링 가능

---

## 7) confidence / severity 규칙을 “계량”으로 바꾸기

PRD는 개념을 제시했지만, 운영에서는 규칙이 숫자로 내려와야 튜닝이 가능하다.

### 7.1 confidence 점수(0~100) → label로 매핑
- 기본: `source_type` 가중치
  - official: +50
  - crawler(내부 데이터): +40
  - media: +30
  - social: +20
- 추가:
  - brand/channel/product 매핑 성공: +10
  - sources >= 2 (교차 확인): +15
  - 지오 precision이 point/city: +5
- label:
  - 80+: high
  - 50–79: medium
  - <50: low

### 7.2 severity(상업적 영향도) 스코어(0~100)
- drop/release: brand tier + listing_count + price_band
- sale_start: discount_rate + 브랜드/채널 가중치
- sales_spike: delta_sale_count + delta_ratio + 다채널 동시성(convergence)
- sold_out/restock: 제품/채널 수 기반 + “발매 직후(예: 48h)”면 상향

---

## 8) API/쿼리 보완: 대량 데이터에서 무너지지 않게

### 8.1 피드 API: offset pagination → cursor pagination 권장
- `/intel/events?limit=50&cursor=<event_time,id>`
- 정렬: `(event_time DESC NULLS LAST, detected_at DESC, id DESC)`  
→ 안정적인 “무한스크롤” 가능

### 8.2 map-points: bbox/zoom 파라미터
- `/intel/map-points?layers=...&start=...&end=...&bbox=minLng,minLat,maxLng,maxLat&zoom=...`
- 응답:
  - 저줌: cluster points (count 포함)
  - 고줌: raw points

### 8.3 timeline: granularity 제공
- `granularity=hour|day|week`
- stacked(레이어별) + total을 같이 내려서 프론트 계산 최소화

### 8.4 highlights: “정렬 기준” 명시
- score = recency_weight + severity_weight + confidence_weight  
→ 운영자가 튜닝 가능한 가중치 구조로

---

## 9) 성능/캐시/장애 대응: worldmonitor에서 배울 점을 Intel에 이식

worldmonitor의 핵심 철학은 “사용자를 기다리게 하지 않는다”와 “상류(데이터 소스) 장애를 가정한다”이다.

### 9.1 UX 성능 원칙 (즉시 적용)
- **Instant render**: 초기에는 “가벼운 리스트”를 즉시 렌더, 이후 비동기 정교화(클러스터링/NER/유사도 등)
- **Virtual scrolling**: 피드 리스트는 가상 스크롤로 DOM 최소화
- “맵/피드/타임라인”을 한 번에 다 불러오지 말고,
  - 최초: highlights + map-points(요약)만
  - 이후: feed/timeline lazy-load

### 9.2 캐시 원칙
- 짧은 TTL 캐시(30~120초)는 PRD대로 유지하되,
- **stale-on-error**(업스트림 실패 시 이전 캐시를 반환) 전략을 추가하면 운영 안정성이 급상승
- **negative caching**: 특정 소스가 실패하면 5분 정도 재시도 간격을 늘려 “망가진 소스를 계속 두드리는” 문제를 방지

### 9.3 “데이터 신선도(Freshness) + Gap” 표시(운영 UI)
- 레이어별(또는 소스별) `fresh / stale / error / disabled` 상태를 계산해 admin에 노출
- worldmonitor처럼 “현재 무엇을 못 보고 있는지(인텔 갭)”를 보여주면 운영 판단이 쉬움

---

## 10) 운영/보안/법적: PRD에 추가하면 좋은 항목

### 10.1 운영 플로우
- low confidence 이벤트는 “검수 큐”로 보내고,
- 운영자가 `is_verified`를 켜면 노출 우선순위를 올림(또는 high severity만 노출)

### 10.2 보안
- Intel admin API는 기존 `ADMIN_BEARER_TOKEN`으로 보호하되,
- public API에 rate limit(기본: IP당 분당 N회) 적용 권장

### 10.3 저작권/콘텐츠 저장
- 원문 전문 저장은 최소화(요약/헤드라인 수준)
- `source_url` 중심 링크 아웃

---

## 11) 로드맵 보강: “선행 조건”을 Sprint 0로 명시

Intel Hub는 결국 **정기 ingest(크롤/파생/뉴스 수집)**가 필요하다.  
현재 자동화(Worker)가 없으면 “탭은 있는데 데이터가 안 움직이는” 상태가 된다.

### Sprint 0 (필수 선행)
- Railway Worker(스케줄러) 서비스 세팅
- Intel 관련 환경변수/크론 스케줄 확정
- Next.js 버전/지도 라이브러리 선택 확정 (Maplibre/Leaflet 중)

### Sprint 1 (1주)
- `intel_events` + (권장) `intel_event_sources` + ingest_runs 마이그레이션
- `/intel/events`, `/intel/map-points` 최소 동작
- drops/collabs/news 미러링 ingest(내부 데이터 기반)

### Sprint 2 (1주)
- Intel 페이지 기본 UI: 레이어 토글 + 타임레인지 + 피드(가상 스크롤) + 맵
- URL 쿼리로 상태 공유(deep link)

### Sprint 3 (1주)
- sale_start, sold_out, restock 파생 로직
- sales_spike 1차(임계치 기반) 도입
- highlights / timeline 완성

### Sprint 4 (1주)
- 운영 대시보드(ingest 성공률/중복률/신선도) + 검수 플로우
- 성능 튜닝(쿼리/인덱스/캐시) + QA/E2E

---

## 12) Definition of Done (v1)

v1 출시 기준을 “명확히” 잡아두면 scope creep을 막을 수 있다.

- Intel 탭에서 4개 레이어는 반드시 제공: `drops`, `collabs`, `news`, `sale_start`
- 지도는 `country precision`까지만 보장해도 OK (city/point는 v2)
- 이벤트 상세에서 **반드시** 1개 이상의 액션 제공:
  - compare 이동 / watchlist 추가 / brand 상세 / channel 상세 중 1개
- 운영자가 “이벤트가 왜 안 들어오는지”를 볼 수 있어야 함:
  - ingest run 로그 + 소스 freshness 상태

---

## 13) PRD 문서에 바로 추가할 “결손 섹션” 목록

원본 PRD(v1.0)에 아래 섹션을 추가하면 기획서가 “개발 가능한 수준”으로 올라간다.

1. **Non-goals / Out of scope** (예: 인스타 크롤링 v1 제외)
2. **Layer별 데이터 소스 + 생성 규칙 + 임계치** (표 형태 권장)
3. **뉴스 레이어 포함 여부 결정**
4. **지오 데이터 확보 계획** (country만 할지, city/point까지 할지)
5. **Dedup 2단계 설계(Deterministic + Fuzzy)**
6. **Ingest run/오류 분류/신선도(ops) 설계**
7. **API 페이징/쿼리 스펙(cursor, bbox, granularity)**

---

## 14) 참고 (레퍼런스)

- WorldMonitor repo: https://github.com/koala73/worldmonitor
- WorldMonitor app: https://worldmonitor.app

