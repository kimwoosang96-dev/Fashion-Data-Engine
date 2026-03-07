# Fashion Data Engine — 과업지시서 (T-081 ~ T-093)

> 실시간 정보전 플랫폼 전환을 위한 상세 구현 지시서.
> 각 태스크는 독립 PR 단위로 구현한다. 선행 태스크가 명시된 경우 반드시 완료 후 시작.

---

## T-081: DB 구조 단순화 — price_history → products 직접 저장

**목표:** price_history 테이블 의존성 제거. 현재 가격을 products 테이블에 직접 저장.

**선행 조건:** 없음 (단, 크롤러가 돌고 있는 동안 마이그레이션 실행 금지)

**작업 내용:**

1. Alembic 마이그레이션 작성 (`alembic/versions/xxxx_add_price_columns_to_products.py`)

```python
# 추가 컬럼
op.add_column('products', sa.Column('price_krw', sa.Integer(), nullable=True))
op.add_column('products', sa.Column('original_price_krw', sa.Integer(), nullable=True))
op.add_column('products', sa.Column('discount_rate', sa.SmallInteger(), nullable=True))
op.add_column('products', sa.Column('currency', sa.String(3), nullable=True))
op.add_column('products', sa.Column('raw_price', sa.Numeric(12, 2), nullable=True))
op.add_column('products', sa.Column('price_updated_at', sa.DateTime(), nullable=True))
op.add_column('products', sa.Column('sale_started_at', sa.DateTime(), nullable=True))

# 인덱스
op.create_index('ix_products_price_krw', 'products', ['price_krw'])
op.create_index('ix_products_sale_started_at', 'products', ['sale_started_at'])
```

2. `src/fashion_engine/models/product.py` — 컬럼 추가

3. `src/fashion_engine/services/product_service.py` — `save_price_history` 함수 수정:
   - price_history INSERT 유지 (하위 호환)
   - products 컬럼도 동시에 UPDATE
   - `is_sale` False → True 전환 시 `sale_started_at = now()` 기록

```python
# product_service.py - upsert_product_price() 수정 예시
async def upsert_product_price(db, product_id, price_info):
    product = await db.get(Product, product_id)
    was_sale = product.is_sale
    now = datetime.utcnow()

    product.price_krw = price_info.price_krw
    product.original_price_krw = price_info.original_price_krw
    product.discount_rate = price_info.discount_rate
    product.currency = price_info.currency
    product.raw_price = price_info.raw_price
    product.price_updated_at = now

    # 세일 시작 감지
    if not was_sale and price_info.is_sale:
        product.sale_started_at = now
    elif not price_info.is_sale:
        product.sale_started_at = None  # 세일 종료 시 초기화

    product.is_sale = price_info.is_sale
    await db.commit()
```

4. 기존 price_history 최신 레코드를 products 컬럼으로 백필:
```sql
UPDATE products p
SET
    price_krw       = ph.price,
    original_price_krw = ph.original_price,
    discount_rate   = ph.discount_rate,
    currency        = 'KRW',
    price_updated_at = ph.crawled_at
FROM (
    SELECT DISTINCT ON (product_id)
        product_id, price, original_price, discount_rate, crawled_at
    FROM price_history
    ORDER BY product_id, crawled_at DESC
) ph
WHERE p.id = ph.product_id;
```

**완료 기준:**
- `SELECT COUNT(*) FROM products WHERE price_krw IS NOT NULL` > 60,000
- 크롤러 실행 후 products.price_krw 갱신 확인

---

## T-082: 프론트엔드 — 가격 히스토리 차트 제거

**목표:** 가격 추이 그래프 관련 UI/API 코드 전부 제거. compare 페이지는 "채널별 현재가 비교 테이블"만 남김.

**선행 조건:** 없음 (독립 실행 가능)

**작업 내용:**

1. `frontend/src/lib/api.ts` — 함수 삭제:
   - `getPriceHistory`
   - `getPriceBadge`

2. `frontend/src/lib/types.ts` — 타입 삭제:
   - `ChannelPriceHistory`
   - `PriceBadge`

3. compare 페이지 (`frontend/src/app/compare/[key]/page.tsx`):
   - 가격 히스토리 차트 컴포넌트 제거
   - "최저가 추이" 섹션 제거
   - 채널별 현재가 비교 테이블만 유지

4. `src/fashion_engine/api/products.py` — 엔드포인트 삭제:
   - `GET /products/price-history/{product_key}`
   - `GET /products/price-badge/{product_key}`

5. `src/fashion_engine/services/product_service.py` — 함수 삭제:
   - `get_price_history()`
   - `get_price_badge()`

**완료 기준:**
- `npm run build` 빌드 성공
- `/compare/*` 페이지 정상 렌더링
- 삭제된 API 엔드포인트 404 반환

---

## T-083: activity_feed 테이블 생성

**목표:** 실시간 이벤트(세일 시작, 신제품, 가격 인하, 품절)를 기록하는 feed 테이블 생성.

**선행 조건:** 없음

**작업 내용:**

1. `src/fashion_engine/models/activity_feed.py` 생성:

```python
class ActivityFeed(Base):
    __tablename__ = "activity_feed"

    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    event_type  = Column(String(30), nullable=False)
    # 'sale_start' | 'new_drop' | 'price_cut' | 'sold_out' | 'restock'
    product_id  = Column(Integer, ForeignKey("products.id"), nullable=True)
    channel_id  = Column(Integer, ForeignKey("channels.id"), nullable=True)
    brand_id    = Column(Integer, ForeignKey("brands.id"), nullable=True)
    product_name = Column(String(500), nullable=True)  # 비정형 소스용 (product_id 없을 때)
    price_krw   = Column(Integer, nullable=True)
    discount_rate = Column(SmallInteger, nullable=True)
    source_url  = Column(String(2000), nullable=True)
    metadata    = Column(JSONB, nullable=True)
    # { "size_info": [...], "image_url": "...", "raw_text": "..." }
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    notified    = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_activity_feed_detected_at", "detected_at"),
        Index("ix_activity_feed_event_type_detected_at", "event_type", "detected_at"),
        Index("ix_activity_feed_brand_id", "brand_id"),
    )
```

2. `src/fashion_engine/models/__init__.py` — import 추가

3. Alembic 마이그레이션 생성

4. `src/fashion_engine/api/schemas.py` — `ActivityFeedOut` 스키마 추가:
```python
class ActivityFeedOut(BaseModel):
    id: int
    event_type: str
    product_name: str | None
    brand_name: str | None
    channel_name: str | None
    price_krw: int | None
    discount_rate: int | None
    source_url: str | None
    image_url: str | None  # metadata에서 추출
    detected_at: datetime
```

5. `GET /feed` API 엔드포인트 추가 (`src/fashion_engine/api/feed.py`):
```python
@router.get("/", response_model=list[ActivityFeedOut])
async def get_feed(
    event_type: str | None = None,
    brand_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    # detected_at DESC 정렬, 필터 지원
```

**완료 기준:**
- `GET /feed` 200 반환 (빈 리스트)
- 수동 INSERT 후 API에서 확인 가능

---

## T-084: 크롤 주기 세분화

**목표:** 전체 크롤 외에 빠른 세일 감지 전용 주기 추가.

**선행 조건:** T-081 완료

**작업 내용:**

1. `scripts/scheduler.py` — 스케줄 추가:

```python
# 기존: 03:00 전체 크롤
# 추가: 2시간마다 상위 채널 빠른 순회
schedule.every(2).hours.do(fast_poll_top_channels)

# 추가: 1시간마다 신제품 페이지 전용 크롤
schedule.every(1).hours.do(crawl_new_products_only)
```

2. `scripts/crawl_products.py` — `--fast-poll` 플래그 추가:
   - 상위 채널 50개만 대상 (활성 채널 중 최근 세일 감지 빈도 높은 순)
   - 제품 목록 전체 수집 생략, 신규/세일 변경 감지에만 집중
   - `--new-only` 플래그: Shopify `/products/new.json` 엔드포인트만 요청

3. `channels` 테이블에 `poll_priority` 컬럼 추가 (1=high, 2=normal, 3=low):
   - fast_poll 대상은 priority=1 채널만
   - 기본값 = 2, 관리자 페이지에서 조정 가능

4. Railway 스케줄 업데이트:

| 시간 | 작업 |
|------|------|
| 03:00 | 전체 크롤 (기존 유지) |
| 매 2시간 | fast_poll (상위 50채널) |
| 매 1시간 | new_products_only |

**완료 기준:**
- `uv run python scripts/crawl_products.py --fast-poll --dry-run` 정상 실행
- Railway Worker 스케줄 반영 확인

---

## T-085: WatchAgent — 실시간 변경 감지 에이전트

**목표:** 크롤 결과를 분석해 세일 시작/신제품/가격 인하를 감지하고 activity_feed에 기록.

**선행 조건:** T-081, T-083 완료

**작업 내용:**

1. `scripts/watch_agent.py` 생성:

```python
"""
WatchAgent: 크롤 완료 후 자동 실행되어 변경 이벤트를 감지하고 activity_feed에 기록.
crawl_products.py가 --watch 플래그로 호출하거나 독립 실행 가능.
"""

class WatchAgent:
    async def detect_sale_start(self, db, channel_id) -> list[ActivityFeedRow]:
        """
        크롤 전/후 is_sale 상태 비교.
        False → True 변경된 product_id → 'sale_start' 이벤트 생성
        """

    async def detect_new_drops(self, db, channel_id, crawl_run_id) -> list[ActivityFeedRow]:
        """
        이번 크롤런에서 처음 등장한 product_id → 'new_drop' 이벤트 생성
        created_at이 현재 크롤런 시작 이후인 제품
        """

    async def detect_price_cut(self, db, channel_id) -> list[ActivityFeedRow]:
        """
        price_krw가 이전 대비 10%+ 하락 → 'price_cut' 이벤트 생성
        (T-081에서 price_updated_at 기준으로 이전값 비교)
        """

    async def run(self, db, channel_id, crawl_run_id):
        events = []
        events += await self.detect_sale_start(db, channel_id)
        events += await self.detect_new_drops(db, channel_id, crawl_run_id)
        events += await self.detect_price_cut(db, channel_id)
        # activity_feed INSERT
        # Discord 알림 (critical severity만)
```

2. `scripts/crawl_products.py` — 채널 크롤 완료 직후 WatchAgent 자동 호출:
```python
# 기존 --no-intel 플래그처럼 --no-watch로 비활성화 가능
await watch_agent.run(db, channel_id=channel.id, crawl_run_id=run.id)
```

**완료 기준:**
- 테스트 채널 크롤 후 activity_feed에 이벤트 기록 확인
- `GET /feed` 에서 실제 이벤트 반환 확인

---

## T-086: 정보 소스 확장

**목표:** 크롤링 외 정보 소스 추가 — Shopify webhook, 커뮤니티 신호.

**선행 조건:** T-083 완료

**작업 내용:**

1. Shopify Webhook 수신 엔드포인트 (`src/fashion_engine/api/webhooks.py`):
```python
@router.post("/webhooks/shopify/{channel_slug}")
async def receive_shopify_webhook(
    channel_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Shopify products/create, products/update 이벤트 수신.
    X-Shopify-Hmac-Sha256 헤더로 서명 검증 후 처리.
    """
    # HMAC 검증
    # 제품 파싱 → products upsert
    # activity_feed INSERT ('new_drop' 또는 'sale_start')
```

2. `channels` 테이블에 `webhook_secret` 컬럼 추가:
   - Shopify webhook 등록 시 채널별 secret 저장

3. DCinside 갤러리 모니터링 (`scripts/crawl_community.py`):
   - 스트릿패션 갤러리 추천글 파싱
   - 브랜드명 키워드 매칭 → `fashion_news` 또는 `activity_feed` 기록

**완료 기준:**
- Shopify webhook 테스트 이벤트 수신 및 DB 반영 확인
- HMAC 검증 실패 시 401 반환

---

## T-087: 프론트엔드 — 실시간 피드 페이지 (/feed)

**목표:** activity_feed 기반 실시간 이벤트 피드 페이지 구현.

**선행 조건:** T-083 완료 (API 존재), T-085 완료 (실제 데이터)

**작업 내용:**

1. `frontend/src/lib/api.ts` — 함수 추가:
```typescript
export const getActivityFeed = (params?: {
  event_type?: string;
  brand_id?: number;
  limit?: number;
  offset?: number;
}) => apiFetch<ActivityFeedItem[]>(`/feed?${new URLSearchParams(params as any)}`);
```

2. `frontend/src/lib/types.ts` — 타입 추가:
```typescript
export type ActivityFeedItem = {
  id: number;
  event_type: 'sale_start' | 'new_drop' | 'price_cut' | 'sold_out' | 'restock';
  product_name: string | null;
  brand_name: string | null;
  channel_name: string | null;
  price_krw: number | null;
  discount_rate: number | null;
  source_url: string | null;
  image_url: string | null;
  detected_at: string;
};
```

3. `frontend/src/app/feed/page.tsx` 생성:

**UI 구성:**
- 상단: 이벤트 타입 필터 탭 (전체 / 세일시작 / 신제품 / 가격인하)
- 피드 아이템 카드:
  - 배지: `[세일시작]` `[신제품]` `[가격인하]` (색상 구분)
  - 제품명, 브랜드, 채널
  - 가격 / 할인율
  - 감지 시각 (N분 전, N시간 전)
  - [바로 보기] 링크
- 자동 새로고침: 30초마다 최신 데이터 폴링 (`useEffect` + `setInterval`)
- 무한 스크롤 또는 [더 보기] 버튼

4. `frontend/src/components/Nav.tsx` — 피드 메뉴 항목 추가

**완료 기준:**
- `/feed` 페이지 정상 렌더링
- 30초 자동 갱신 동작 확인
- 이벤트 타입 필터 동작 확인

---

## T-088: PWA 푸시 알림

**목표:** 브랜드 구독 기반 세일/신제품 웹 푸시 알림.

**선행 조건:** T-087 완료

**작업 내용:**

1. `frontend/public/manifest.json` 생성 (PWA 설정)

2. `frontend/public/sw.js` — Service Worker:
   - Push 이벤트 수신 → 알림 표시
   - 알림 클릭 → 해당 상품 페이지 오픈

3. `frontend/src/app/layout.tsx` — Service Worker 등록 코드 추가

4. 구독 관리 API (`src/fashion_engine/api/push.py`):
```python
POST /push/subscribe   # { endpoint, keys, brand_ids: [] } 저장
DELETE /push/subscribe # 구독 취소
```

5. `scripts/watch_agent.py` — 이벤트 감지 후 구독자에게 Web Push 발송:
   - `pywebpush` 라이브러리 사용
   - 알림 내용: "Palace 30% 세일 — Box Logo Tee ₩62,300"

**완료 기준:**
- 브라우저에서 알림 권한 요청 확인
- 테스트 푸시 발송 및 수신 확인

---

## T-089: 랭킹 로직 재정의

**목표:** 랭킹 기준을 "할인율 높은 순" → "방금 세일 시작 + 긴박감 점수" 조합으로 변경.

**선행 조건:** T-081 완료 (sale_started_at 컬럼 존재)

**작업 내용:**

1. `src/fashion_engine/services/product_service.py` — `get_product_ranking()` 수정:

```python
# 긴박감 점수 공식
# urgency_score = discount_rate * (1 / (hours_since_sale_start + 1))
# 세일 시작 직후 최고점, 시간이 지날수록 자연 하락

urgency_score = (
    Product.discount_rate
    * (1.0 / (
        func.extract('epoch', func.now() - Product.sale_started_at) / 3600 + 1
    ))
)

# sale_hot 정렬: urgency_score DESC
# price_drop 정렬: price_cut 이벤트 최근 순 (activity_feed 기반)
```

2. `src/fashion_engine/api/schemas.py` — `ProductRankingOut`에 `sale_started_at`, `hours_since_sale_start` 필드 추가

3. `frontend/src/app/ranking/page.tsx` — 카드에 "N시간 전 세일 시작" 표시 추가

**완료 기준:**
- 최근 세일 시작 제품이 랭킹 상위에 표시
- 오래된 세일 제품은 자연스럽게 하위로 밀림

---

## T-090: "지금 사야 하는 이유" 배지 시스템

**목표:** 제품 카드에 구매 긴박감을 전달하는 컨텍스트 배지 추가.

**선행 조건:** T-081, T-089 완료

**작업 내용:**

1. `src/fashion_engine/api/schemas.py` — `ProductRankingOut`에 `badges` 필드 추가:
```python
badges: list[str]  # ['방금 세일', '멀티채널', '한정판']
```

2. `src/fashion_engine/services/product_service.py` — 배지 계산 로직:
```python
def compute_badges(product, total_channels, intel_event=None) -> list[str]:
    badges = []
    if product.sale_started_at:
        hours = (datetime.utcnow() - product.sale_started_at).total_seconds() / 3600
        if hours < 24:
            badges.append('방금 세일')
    if total_channels >= 3:
        badges.append('멀티채널')
    if intel_event and intel_event.event_type in ('drops', 'collabs'):
        badges.append('한정판')
    return badges
```

3. `frontend/src/app/ranking/page.tsx` — 배지 UI:
```tsx
{item.badges.map(badge => (
  <span key={badge} className="rounded-full bg-red-600 px-2 py-0.5 text-[10px] font-bold text-white">
    {badge}
  </span>
))}
```

**완료 기준:**
- 24시간 이내 세일 시작 제품에 '방금 세일' 배지 표시
- 3채널 이상 제품에 '멀티채널' 배지 표시

---

## T-091: GPT-4o 파서 에이전트 — 비정형 사이트 fallback

**목표:** Shopify/WooCommerce/Cafe24 외 비정형 쇼핑몰에서 GPT-4o mini로 제품 추출.

**선행 조건:** OpenAI API 키 환경변수 설정 (`OPENAI_API_KEY`)

**작업 내용:**

1. `uv add openai` 의존성 추가

2. `src/fashion_engine/crawler/gpt_parser.py` 생성:
```python
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def parse_products_from_html(url: str, html: str) -> list[dict]:
    """
    비정형 HTML에서 GPT-4o mini로 제품 목록 추출.
    반환: [{ name, price, currency, original_price, url, image_url, is_sale }, ...]
    비용: 약 $0.001/사이트 (8K 토큰 기준)
    """
    # HTML 전처리: script/style 태그 제거, 8000자 truncate
    cleaned_html = clean_html(html)[:8000]

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[{
            "role": "user",
            "content": f"""다음 쇼핑몰 HTML에서 판매 중인 제품 목록을 추출하라.
URL: {url}
결과를 JSON으로: {{"products": [{{"name": str, "price": float, "currency": str,
"original_price": float|null, "url": str, "image_url": str|null, "is_sale": bool}}]}}

HTML:
{cleaned_html}"""
        }]
    )
    data = json.loads(response.choices[0].message.content)
    return data.get("products", [])
```

3. `src/fashion_engine/crawler/brand_crawler.py` — fallback 로직 추가:
```python
# 플랫폼 감지 실패 또는 0개 제품 수집 시
if len(products) == 0 and channel.platform == "unknown":
    logger.info("GPT fallback parser 시도: %s", channel.url)
    products = await gpt_parser.parse_products_from_html(channel.url, html)
```

4. `channels` 테이블에 `use_gpt_parser` Boolean 컬럼 추가:
   - 관리자가 특정 채널에 GPT 파서 강제 지정 가능

**완료 기준:**
- 비정형 테스트 사이트에서 제품 추출 성공
- 비용 로그: 요청당 토큰 수 기록

---

## T-092: Custom GPT + Actions — 수동 인텔 수집 도구

**목표:** GPT Pro에서 Custom GPT가 브라우징으로 발견한 정보를 우리 API에 직접 기록.

**선행 조건:** T-083 완료 (`/feed/ingest` API 필요)

**작업 내용:**

1. `POST /feed/ingest` 엔드포인트 추가 (`src/fashion_engine/api/feed.py`):
```python
@router.post("/ingest", status_code=201)
async def ingest_feed_event(
    payload: FeedIngestIn,
    token: str = Depends(verify_api_key),  # API 키 인증
    db: AsyncSession = Depends(get_db),
):
    """Custom GPT Actions에서 호출. 발견한 세일/신제품을 feed에 기록."""
    # brand_slug로 brand_id 조회
    # activity_feed INSERT
```

2. `src/fashion_engine/api/schemas.py` — `FeedIngestIn` 스키마:
```python
class FeedIngestIn(BaseModel):
    event_type: Literal['sale_start', 'new_drop', 'price_cut', 'sold_out']
    brand_slug: str | None = None
    product_name: str
    price_krw: int | None = None
    discount_rate: int | None = None
    source_url: str
    image_url: str | None = None
    notes: str | None = None
    detected_at: datetime | None = None
```

3. OpenAPI 스펙 파일 생성 (`openapi_gpt_actions.yaml`):
   - Custom GPT Actions에서 임포트 가능한 형식
   - `POST /feed/ingest` 스펙 정의
   - `GET /feed` 스펙 정의 (GPT가 기록 후 확인용)

4. API 키 인증 추가:
   - `.env`에 `GPT_ACTIONS_API_KEY` 추가
   - Custom GPT Actions 설정에서 API 키 입력

5. Custom GPT 설정 (ChatGPT UI):
   - Instructions: "패션 정보 수집 비서. 사이트를 브라우징해서 세일/신제품 발견 시 /feed/ingest로 기록."
   - Actions: openapi_gpt_actions.yaml 임포트

**완료 기준:**
- Custom GPT에서 Actions 호출 → DB에 activity_feed 레코드 생성 확인
- `GET /feed`에서 GPT가 기록한 이벤트 확인

---

## T-093: AI 채널 발굴 에이전트

**목표:** GPT-4o가 신규 패션 쇼핑몰을 자동 발굴 → channel_probe로 접근성 검증 → draft 등록.

**선행 조건:** T-091과 동일 (OpenAI API 키)

**작업 내용:**

1. `scripts/discover_channels.py` 생성:

```python
"""
AI 채널 발굴 에이전트.
사용법: uv run python scripts/discover_channels.py --query "한국인이 많이 구매하는 일본 편집샵"
"""
import asyncio
import argparse
from openai import AsyncOpenAI
from fashion_engine.database import AsyncSessionLocal
from fashion_engine.models.channel import Channel

client = AsyncOpenAI()

async def discover_channels(query: str, count: int = 20) -> list[dict]:
    """GPT-4o로 쇼핑몰 URL 목록 생성."""
    response = await client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[{
            "role": "user",
            "content": f"""패션 쇼핑몰 발굴 작업. 다음 조건에 맞는 실제 운영 중인 쇼핑몰 {count}개를 찾아라.

조건: {query}

결과를 JSON으로:
{{"channels": [{{
  "name": "쇼핑몰 이름",
  "url": "https://...",
  "country": "JP/US/KR/...",
  "description": "간단 설명",
  "estimated_platform": "shopify/woocommerce/cafe24/unknown"
}}]}}

중요: 실제 존재하는 URL만. 리셀/마켓플레이스 제외. 브랜드 공식몰 또는 편집샵만."""
        }]
    )
    data = json.loads(response.choices[0].message.content)
    return data.get("channels", [])

async def run(query: str):
    candidates = await discover_channels(query)
    print(f"GPT 발굴 결과: {len(candidates)}개")

    # channel_probe 실행 (기존 probe 로직 재사용)
    from scripts.channel_probe import probe_channel
    async with AsyncSessionLocal() as db:
        for c in candidates:
            # 이미 등록된 채널인지 확인
            existing = await db.execute(
                select(Channel).where(Channel.url.ilike(f"%{c['url'].split('/')[2]}%"))
            )
            if existing.scalar():
                print(f"  이미 등록됨: {c['name']}")
                continue

            # probe 실행
            result = await probe_channel(c['url'])
            if result.accessible:
                # draft 상태로 삽입
                channel = Channel(
                    name=c['name'],
                    url=c['url'],
                    country=c['country'],
                    description=c['description'],
                    platform=c.get('estimated_platform', 'unknown'),
                    is_active=False,  # draft — 관리자 승인 후 활성화
                )
                db.add(channel)
                print(f"  draft 등록: {c['name']} ({c['url']})")
            else:
                print(f"  접근 불가: {c['name']}")
        await db.commit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True, help="발굴 조건 (자연어)")
    parser.add_argument("--count", type=int, default=20)
    args = parser.parse_args()
    asyncio.run(run(args.query))
```

2. 관리자 페이지에 "draft 채널 승인" UI 추가:
   - `GET /admin/channels?status=draft` 엔드포인트
   - 관리자가 검토 후 `PATCH /admin/channels/{id}/activate`

**완료 기준:**
- `uv run python scripts/discover_channels.py --query "일본 스트릿 편집샵"` 실행
- draft 채널 DB 등록 확인
- 기존 채널 중복 등록 방지 확인

---

## 구현 순서 요약

```
즉시 (독립):
  T-082 (가격 차트 제거)
  T-093 (AI 채널 발굴)

1주차:
  T-081 (DB 컬럼) → T-083 (activity_feed) → T-085 (WatchAgent)

2주차:
  T-087 (피드 페이지) → T-089 (랭킹 재정의) → T-090 (배지)

3주차:
  T-084 (크롤 주기) → T-086 (소스 확장) → T-091 (GPT 파서)

이후:
  T-092 (Custom GPT) → T-088 (PWA 푸시)
```
