# Fashion Data Engine — 실시간 정보전 플랫폼 전환 계획

> 핵심 명제: 패션 쇼핑은 정보전이다.
> 옷은 팔리면 끝이다. 재고·재입고가 없다. 따라서 "가격 추이"보다 "지금 살 수 있는가, 지금 싸게 살 수 있는가"가 전부다.

---

## 현재 문제

| 문제 | 영향 |
|------|------|
| price_history 구조 — 가격 추이 저장에 최적화 | DB 낭비, 조인 복잡도 증가, 실시간성 없음 |
| 크롤 주기 12시간+ | 세일 시작 후 반나절 뒤에야 반영 |
| "지금 세일 중" vs "방금 세일 시작" 구분 없음 | 유저 입장에서 긴박감 없음 |
| 정보 소스 = 크롤링 단독 | 브랜드 SNS/뉴스레터/Shopify 이벤트 미활용 |

---

## 전략 전환: 추이 추적 → 실시간 감시

### 핵심 변경 원칙

- **"지금 상태"만 중요하다.** 어제 얼마였는지는 패션에서 의미 없다.
- **최초 감지 시각이 곧 가치다.** 세일을 10분 먼저 알면 원하는 사이즈를 살 수 있다.
- **소스를 다양화해야 크롤 공백을 메울 수 있다.**

---

## Phase A — DB 구조 단순화 (T-081~T-083)

### T-081: price_history → current_price 컬럼으로 흡수

products 테이블에 현재 가격을 직접 저장. price_history는 "최신 1건 캐시" 역할로만 유지하거나 완전 제거.

```sql
-- products 테이블에 추가
price_krw          INTEGER          -- 현재 가격 (KRW)
original_price_krw INTEGER          -- 원가 (KRW)
discount_rate      SMALLINT         -- 현재 할인율
currency           VARCHAR(3)       -- 원본 통화
raw_price          NUMERIC(12,2)    -- 원본 가격
price_updated_at   TIMESTAMP        -- 마지막 가격 갱신 시각

-- 새로운 이벤트 타임스탬프
sale_started_at    TIMESTAMP        -- 세일 최초 감지 시각
first_seen_at      TIMESTAMP        -- 제품 최초 감지 시각 (= created_at)
sold_out_at        TIMESTAMP        -- 품절 감지 시각 (nullable)
```

**효과:**
- price_history 테이블 완전 삭제 → DB 상시 경량 유지
- JOIN 없이 단일 테이블 조회 → API 응답 2-3배 빠름
- sale_started_at으로 "방금 세일 시작" 정렬 가능

### T-082: 프론트엔드 가격 히스토리 그래프 제거

제거 대상:
- `/compare/[key]` 페이지의 가격 히스토리 차트
- `/products/price-history/*` API 엔드포인트
- `getPriceHistory`, `getPriceBadge` API 함수

대체:
- compare 페이지 → "채널별 현재가 비교" 테이블만 남김 (이미 더 유용)
- 가격 추이 없이도 "지금 어디서 제일 싸게 살 수 있나"는 충분히 표현 가능

### T-083: 실시간 피드 데이터 모델

```sql
CREATE TABLE activity_feed (
    id            BIGSERIAL PRIMARY KEY,
    event_type    VARCHAR(30) NOT NULL,  -- 'sale_start' | 'new_drop' | 'price_cut' | 'sold_out'
    product_id    INTEGER REFERENCES products(id),
    channel_id    INTEGER REFERENCES channels(id),
    brand_id      INTEGER REFERENCES brands(id),
    metadata      JSONB,                 -- { discount_rate, price_krw, size_info, ... }
    detected_at   TIMESTAMP NOT NULL DEFAULT now(),
    notified      BOOLEAN DEFAULT false
);
CREATE INDEX ON activity_feed (detected_at DESC);
CREATE INDEX ON activity_feed (event_type, detected_at DESC);
```

---

## Phase B — 실시간 감시 에이전트 (T-084~T-088)

### T-084: 크롤 주기 세분화

| 대상 | 현재 주기 | 목표 주기 |
|------|-----------|-----------|
| 전체 채널 | 24시간 1회 | 6시간 1회 |
| 세일 감지 전용 (빠른 순회) | 없음 | 2시간마다, 상위 50개 채널만 |
| 신제품 페이지 | 없음 | 1시간마다 (Shopify /products/new.json) |
| 방금 세일 시작한 채널 재확인 | 없음 | 감지 후 30분 내 재크롤 (재고 확인) |

### T-085: 실시간 감시 에이전트 (scripts/watch_agent.py)

```
WatchAgent
├── FastPoller — 상위 채널 2시간 순회, 변경 감지 시 activity_feed 기록
├── NewProductDetector — Shopify /products/new.json 1시간 폴링
├── SaleStartDetector — is_sale 변경 감지 → sale_started_at 기록 + feed 추가
└── AlertDispatcher — Discord/웹훅 실시간 발송 (critical 이벤트만)
```

**감지 로직:**
- `is_sale` False → True : `sale_start` 이벤트
- `price_krw` 10%+ 하락 : `price_cut` 이벤트
- 신규 product_key 첫 등장 : `new_drop` 이벤트
- 재고 정보 있는 채널에서 variants 소진 : `sold_out` 이벤트

### T-086: 정보 소스 확장

#### Shopify Webhook 수신 (가능한 브랜드만)
```
POST /webhooks/shopify/{channel_slug}
→ products/create, products/update 이벤트 수신
→ 크롤 없이 즉시 DB 반영
```
일부 브랜드는 Shopify 웹훅을 외부에 설정 가능. 이 경우 크롤 불필요, 실시간 반영.

#### 브랜드 뉴스레터 모니터링
- 주요 브랜드 메일링리스트 구독 (수동)
- 메일 수신 → GPT로 세일/신제품 파싱 → activity_feed 기록

#### SNS/커뮤니티 신호
- 브랜드 인스타그램 새 포스팅 감지 (Instagram Graph API, 공개 계정)
- DCinside 스트릿패션 갤러리 핫글 모니터링 (특정 브랜드 언급 감지)

### T-087: 프론트엔드 실시간 피드 페이지 (/feed)

```
┌────────────────────────────────────────────────┐
│ 실시간 피드                           [필터▼]  │
│                                                 │
│ [세일시작] Palace — Box Logo Tee                │
│  3분 전 · ₩89,000 → ₩62,300 · 30% OFF        │
│  palace-london.com                 [바로 보기]  │
│                                                 │
│ [신제품] Stüssy — SS26 Spring Drop             │
│  12분 전 · ₩148,000                            │
│  stussy.com/kr                     [바로 보기]  │
│                                                 │
│ [가격인하] Stone Island — Nylon Metal Jacket   │
│  1시간 전 · ₩520,000 → ₩364,000 · 30% OFF    │
│  mrporter.com                      [바로 보기]  │
└────────────────────────────────────────────────┘
```

기능:
- 이벤트 타입별 필터 (세일시작 / 신제품 / 가격인하 / 품절)
- 브랜드/채널 필터
- 자동 새로고침 (30초 폴링 또는 SSE)
- 각 피드 아이템에서 바로 구매 링크로

### T-088: 웹 푸시 알림 (PWA)

- `/feed` 페이지를 PWA로 구성 (manifest.json + service worker)
- 사용자가 특정 브랜드 구독 → 해당 브랜드 이벤트 발생 시 푸시
- 알림 형식: "Palace 30% 세일 시작 — Box Logo Tee ₩62,300"

---

## Phase C — 랭킹 재정의 (T-089~T-090)

### T-089: 랭킹 기준 전환 — "인기도"에서 "정보 가치"로

| 현재 | 변경 |
|------|------|
| 세일 HOT = 할인율 높은 순 | 세일 HOT = 방금 세일 시작 + 할인율 높은 순 |
| 가격 급락 = price_history 비교 | 가격 급락 = price_cut 이벤트 최근 순 |
| 브랜드 랭킹 = 세일 제품 수 | 브랜드 랭킹 = 활성도 (최근 72시간 이벤트 수) |

**"방금 세일 시작" 점수 공식:**
```
urgency_score = discount_rate * (1 / hours_since_sale_start + 1)
```
세일 시작 직후 점수 최대, 시간이 지날수록 자연 하락.

### T-090: "지금 사야 하는 이유" 배지 시스템

각 제품 카드에 컨텍스트 배지:
- `방금 세일` — sale_started_at 기준 24시간 이내
- `한정판` — intel_events에서 drops/collab 태그
- `멀티채널` — 3개 이상 채널에서 동시 판매
- `재입고` — sold_out 후 다시 in-stock 감지

---

## Phase D — GPT 에이전트 통합 (T-091~T-093)

> GPT Pro 토큰은 실시간 모니터링보다 "크롤러가 못 하는 것"을 보완하는 데 ROI가 높다.
> 실시간성 = 크롤러, 지능형 파싱·발굴 = GPT.

### T-091: GPT-4o 파서 에이전트 — 비정형 사이트 fallback

현재 크롤러는 Shopify / WooCommerce / Cafe24 전용이다. 독립 쇼핑몰, 아카이브 편집샵 등
비정형 HTML은 수집 불가. GPT-4o mini를 fallback 파서로 투입한다.

```python
# scripts/gpt_parser_agent.py
async def parse_channel_with_gpt(url: str, html: str) -> list[ProductInfo]:
    """
    크롤러가 실패한 채널에 GPT-4o mini fallback 파싱.
    비용: 사이트당 ~$0.001 (GPT-4o mini input 토큰 기준)
    """
    prompt = f"""
    다음 HTML에서 판매 중인 제품 목록을 추출하라.
    각 제품: name, price, currency, original_price, url, image_url, is_sale
    JSON array로 반환.
    URL: {url}
    HTML: {html[:8000]}
    """
    # OpenAI API 호출 → 구조화된 제품 리스트 반환
```

**트리거 조건:**
- `crawl_products.py`가 0개 제품을 반환한 채널 → GPT fallback 자동 실행
- 신규 채널 첫 크롤 시 전략 미확인 → GPT로 사이트 구조 분석 후 전략 결정

**효과:** 현재 수집 불가 독립 편집샵 30-50곳 커버 가능 (추정)

### T-092: Custom GPT + Actions — 수동 인텔 수집 도구

GPT Pro에서 Custom GPT를 만들고, OAuth2로 우리 API에 인증하여 발견한 정보를 자동으로
피드에 기록하는 "인텔 수집 비서" 구성.

**Custom GPT 역할:**
- "오늘 Supreme 드롭 뭐야?" → 브라우징 → `/intel/events` POST
- "이번 주 일본 편집샵 세일 정리해줘" → 브라우징 → `activity_feed` 기록
- 브랜드 인스타그램 캡처 업로드 → 세일 공지 파싱 → feed 등록

**Actions 정의 (openapi.yaml):**
```yaml
POST /feed/ingest
  body:
    event_type: sale_start | new_drop | price_cut
    brand_slug: string
    product_name: string
    price_krw: integer
    source_url: string
    detected_at: datetime
```

**OAuth2 흐름:**
- GPT에서 Actions 실행 → 우리 API OAuth 엔드포인트로 인증 → Bearer 토큰 발급
- GPT Pro 사용자(본인)만 사용 가능 → 내부 도구로 충분

**포지셔닝:** 자동화 도구가 아닌 "지능형 수동 인텔 수집" 도구.
크롤러가 커버 못 하는 SNS/뉴스레터/커뮤니티 정보를 GPT가 브라우징해서 DB에 기록.

### T-093: AI 채널 발굴 에이전트

현재 채널 추가는 전적으로 수동. GPT에게 신규 채널 발굴을 위임.

```python
# scripts/discover_channels.py
async def discover_channels(query: str) -> list[ChannelCandidate]:
    """
    GPT-4o가 패션 쇼핑몰 목록을 생성 → 자동으로 channel_probe 실행

    예시 쿼리:
    - "한국인이 많이 구매하는 일본 스트릿 편집샵"
    - "유럽 아카이브 세일 전문 쇼핑몰"
    - "Supreme 공식 외 리셀 구조 없는 한정 드롭 채널"
    """
    # 1. GPT가 URL 목록 생성
    # 2. channel_probe.py로 자동 접근성 테스트
    # 3. 통과한 채널 → channels 테이블 draft 상태로 삽입
    # 4. 관리자 승인 후 활성화
```

**예상 효과:** 현재 137개 → 분기별 20-30개 신규 채널 자동 발굴

---

## 제거 목록 (DB/코드 정리)

| 항목 | 이유 |
|------|------|
| `price_history` 테이블 (T-081 완료 후) | products에 흡수 |
| `/products/price-history/*` API | 사용처 없음 |
| `/products/price-badge/*` API | 사용처 없음 |
| compare 페이지 가격 차트 컴포넌트 | 의미 없음 |
| `getPriceHistory`, `getPriceBadge` 함수 | 사용처 없음 |

---

## 우선순위 및 순서

```
T-081 (DB 구조) → T-083 (activity_feed) → T-085 (WatchAgent)
     ↓                                            ↓
T-082 (프론트 가격차트 제거)              T-087 (피드 페이지)
     ↓                                            ↓
T-089 (랭킹 재정의)               T-086 (소스 확장) → T-088 (푸시)
```

**즉시 시작 가능 (DB 마이그레이션 불필요):**
- T-082: 프론트 가격 히스토리 차트 제거 (1-2시간)
- T-087: 피드 페이지 UI 스켈레톤 (activity_feed 없이 기존 intel_events로 임시 구현)
- T-093: AI 채널 발굴 스크립트 (독립 실행 가능)

**핵심 경로 (1-2주):**
- T-081 → T-083 → T-085 → T-087 → T-089

**GPT 에이전트 경로 (병렬 진행 가능):**
- T-091 (GPT 파서) → T-093 (채널 발굴) → T-092 (Custom GPT Actions)

---

## 기대 효과

| 지표 | 현재 | 목표 |
|------|------|------|
| 세일 감지 지연 | 12-24시간 | 1-2시간 (FastPoller) / 즉시 (Webhook) |
| DB 크기 증가율 | 월 30MB+ | 월 5MB 이하 (price_history 제거) |
| 랭킹 페이지 실시간성 | 어젯밤 크롤 기준 | 2시간 이내 |
| 유저 행동 | 가격 그래프 보기 | 피드 구독 → 세일 즉시 구매 |
