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

## 구현 순서 요약 (T-081~T-093)

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

---

# 과업지시서 (T-094 ~ T-100)

> T-081~T-093 완료 후 다음 단계. 사용자 경험 고도화 및 인텔 수집 채널 확장.
> 비용 없이 운영 가능한 것을 우선 배치.

---

## T-094: Custom GPT Actions OAuth 연동 검증

**목표:** 구현된 OAuth2 서버가 Custom GPT Actions와 정상 연동되는지 검증.

> OpenClaw는 2026년 2월 기준 CVE-2026-25253(토큰 탈취), ClawJacked(원격 에이전트 탈취) 등
> 심각한 보안 취약점이 발견됐습니다. 개인 데이터가 있는 맥북에는 설치하지 않습니다.
> 인텔 수집은 Custom GPT Actions만 사용합니다.

**선행 조건:** Railway 배포 완료, `ADMIN_BEARER_TOKEN` 설정됨

**작업 내용:**

1. **Railway 배포 확인:**
   ```bash
   curl "https://fashion-data-engine-production.up.railway.app/oauth/authorize\
?client_id=test&redirect_uri=https://example.com&response_type=code"
   # → HTML 승인 폼 반환 확인
   ```

2. **Custom GPT Actions 설정 (ChatGPT UI):**
   - 내 GPT 만들기 → Actions → `openapi_gpt_actions.yaml` 임포트
   - Authentication: OAuth 선택
   - Client ID: `fashion-data-engine`
   - Client Secret: `ADMIN_BEARER_TOKEN` 값
   - Authorization URL: `https://fashion-data-engine-production.up.railway.app/oauth/authorize`
   - Token URL: `https://fashion-data-engine-production.up.railway.app/oauth/token`
   - Scope: `feed:write`
   - GPT 저장 후 "연결" 버튼 클릭 → 승인 폼에서 토큰 입력 → 연결 완료

3. **Custom GPT Instructions 작성:**
   ```
   너는 패션 정보 수집 비서다. 사용자가 세일, 신제품, 가격 변동 정보를 말하면
   /feed/ingest API를 통해 activity_feed에 자동으로 기록한다.

   기록 시 규칙:
   - event_type: sale_start(세일 시작), new_drop(신제품), price_cut(가격 인하), sold_out(품절)
   - source_url: 반드시 실제 상품 URL 포함
   - brand_slug: 브랜드 영문 slug (palace, stussy, stone-island 등)
   - price_krw: KRW 기준 가격 (외화면 환산)
   - detected_at: 현재 시각 (ISO 8601)

   브라우징으로 직접 확인한 정보만 기록. 추측 금지.
   ```

**완료 기준:**
- Custom GPT에서 `POST /feed/ingest` 호출 → Railway DB `activity_feed` 레코드 생성 확인
- `GET /feed`에서 GPT가 기록한 이벤트 조회 확인

---

## T-095: 검색 자동완성 (Autocomplete) ✅ 완료

**목표:** 검색창에서 타이핑 시 브랜드명·제품명 자동완성 드롭다운 표시.

**선행 조건:** 없음

**작업 내용:**

1. `src/fashion_engine/api/products.py` — 자동완성 엔드포인트 추가:
```python
@router.get("/search/suggestions")
async def search_suggestions(
    q: str = Query(..., min_length=1, max_length=50),
    limit: int = Query(8, le=20),
    db: AsyncSession = Depends(get_db),
):
    """
    브랜드명 + 제품명 조합 자동완성.
    반환: [{ type: 'brand'|'product', label: str, slug?: str, product_key?: str }]
    """
```

2. 쿼리 로직:
   - `q`로 브랜드명 prefix 매칭 (최대 4개)
   - `q`로 제품명 ilike 매칭 (최대 4개)
   - 브랜드 먼저, 제품 후 순서로 반환
   - 응답 캐시: `Cache-Control: max-age=60`

3. `frontend/src/components/SearchBar.tsx` (또는 기존 검색 컴포넌트):
   - 입력 300ms 디바운스 후 `/products/search/suggestions?q=` 호출
   - 드롭다운 렌더링: 브랜드는 아이콘 + 이름, 제품은 이름 + 채널
   - 키보드 탐색 (↑↓ Enter Esc)
   - 선택 시 해당 페이지로 이동 (브랜드 → `/brands/{slug}`, 제품 → 검색결과)

**완료 기준:**
- "pal" 입력 → "Palace", "Palmes" 등 브랜드 자동완성 표시
- "box logo" 입력 → 관련 제품명 자동완성 표시
- 키보드 탐색 동작 확인

---

## T-096: 드롭 캘린더 페이지 (/drops/calendar) ✅ 완료

**목표:** 예정 드롭 및 세일 일정을 캘린더 형태로 시각화. intel_events 기반.

**선행 조건:** intel_events 테이블에 `drops` 레이어 데이터 존재

**작업 내용:**

1. `src/fashion_engine/api/drops.py` — 캘린더 데이터 엔드포인트 추가:
```python
@router.get("/calendar")
async def drops_calendar(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
):
    """
    해당 월의 드롭/세일 이벤트를 날짜별로 그룹화해 반환.
    반환: { "2026-03-15": [{ brand_name, title, event_type, source_url }], ... }
    """
    # intel_events WHERE layer='drops' AND event_date BETWEEN 월 시작~끝
    # activity_feed WHERE event_type='new_drop' AND detected_at BETWEEN 월 시작~끝
```

2. `frontend/src/app/drops/calendar/page.tsx` 생성:
   - 월 달력 그리드 (CSS Grid 7열)
   - 각 날짜 셀에 이벤트 배지 (브랜드명 + 색상)
   - 날짜 클릭 → 해당 날의 드롭 목록 슬라이드 패널
   - 월 이동 (← →) 버튼
   - 모바일: 달력 대신 날짜순 목록으로 fallback

3. `frontend/src/lib/api.ts` — `getDropsCalendar(year, month)` 함수 추가

**완료 기준:**
- `/drops/calendar` 페이지 렌더링
- intel_events drops 레이어 데이터 날짜별 표시 확인
- 월 이동 동작 확인

---

## T-097: 세일 히트맵 (브랜드 × 채널) ✅ 완료

**목표:** 어느 브랜드가 어느 채널에서 세일 중인지 한눈에 파악하는 히트맵 뷰.

**선행 조건:** T-081 완료 (products.discount_rate 존재)

**작업 내용:**

1. `src/fashion_engine/api/brands.py` — 히트맵 데이터 엔드포인트:
```python
@router.get("/heatmap")
async def brands_heatmap(
    tier: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    브랜드 × 채널 세일 히트맵.
    반환: {
      brands: [{ id, name, slug }],
      channels: [{ id, name, country }],
      cells: [{ brand_id, channel_id, discount_rate, product_count }]
    }
    """
    # 세일 중인 products JOIN brands JOIN channels
    # brand × channel 조합별 avg(discount_rate), count(products)
```

2. `frontend/src/app/brands/heatmap/page.tsx` 생성:
   - X축: 채널 (국가별 색상 구분)
   - Y축: 브랜드 (tier 기준 정렬)
   - 셀 색상: 할인율에 따른 그라디언트 (흰색 → 빨간색)
   - 셀 hover: 툴팁 (제품 수, 평균 할인율, [보러가기] 링크)
   - 필터: 티어 선택, 채널 국가 필터

3. 성능 고려:
   - 데이터 양이 많으면 상위 30 브랜드 × 상위 20 채널로 제한
   - `Cache-Control: max-age=300` (5분 캐시)

**완료 기준:**
- `/brands/heatmap` 페이지 렌더링
- 세일 중인 브랜드×채널 조합 시각화 확인
- hover 툴팁 동작 확인

---

## T-098: 가격 알림 — 특정 제품 모니터링

**목표:** 사용자가 특정 제품을 "찜"하면 가격 인하/세일 시작 시 알림 발송.

**선행 조건:** T-088 완료 (웹 푸시 인프라), activity_feed 운영 중

**작업 내용:**

1. `watchlist` 테이블 (이미 존재 여부 확인 후 필요 시 확장):
```sql
-- 기존 watchlist에 target_price 컬럼 추가
ALTER TABLE watchlist ADD COLUMN target_price INTEGER;
-- target_price: 이 가격 이하로 떨어지면 알림 (NULL = 세일 시작만 알림)
```

2. `src/fashion_engine/services/watch_agent.py` — 알림 트리거 로직:
```python
async def notify_watchlist_users(db, product_id: int, event_type: str, price_krw: int):
    """
    특정 제품의 세일 시작/가격 인하 시 해당 제품 watchlist 구독자에게 알림.
    - target_price IS NULL → 세일 시작 이벤트 시 무조건 알림
    - target_price IS NOT NULL → price_krw <= target_price 시에만 알림
    """
```

3. `frontend/src/app/products/[key]/page.tsx` 또는 제품 카드:
   - [알림 설정] 버튼 → 모달
   - "세일 시작 시 알림" 토글
   - "목표 가격 입력" 필드 (선택)
   - 웹 푸시 구독 요청 포함

4. 알림 발송:
   - `scripts/watch_agent.py`에서 `activity_feed` 이벤트 감지 후 watchlist 조회
   - 해당 제품 watchlist에 있는 push 구독자에게 발송
   - 알림 내용: "Palace Box Logo Tee 세일 시작 — ₩62,300 (30% OFF)"

**완료 기준:**
- 제품 watchlist 등록 → 해당 제품 세일 시작 이벤트 발생 → 푸시 알림 수신 확인
- target_price 설정 후 해당 가격 이하 도달 시 알림 확인

---

## T-099: 관리자 대시보드 고도화 ✅ 완료

**목표:** 운영 현황을 한눈에 파악할 수 있는 관리자 대시보드 추가 지표.

**선행 조건:** 없음 (독립 실행 가능)

**작업 내용:**

1. `GET /admin/intel-status` 기존 응답에 추가:
```python
{
  # 기존 필드 유지
  "activity_feed_24h": int,        # 최근 24시간 이벤트 수
  "activity_feed_by_type": dict,   # { sale_start: N, new_drop: N, ... }
  "gpt_parser_usage": {            # GPT 파서 사용 채널 수
    "enabled_channels": int,
    "last_24h_calls": int,
  },
  "oauth_active": bool,            # OAuth 서버 동작 여부
  "top_active_brands": [           # 최근 72시간 activity 많은 브랜드 5개
    { brand_name, event_count }
  ],
}
```

2. `frontend/src/app/admin/page.tsx` — 대시보드 섹션 추가:
   - Activity Feed 현황 (24시간 이벤트 수, 타입별 분포 바 차트)
   - 가장 활발한 브랜드 TOP 5
   - OAuth 연결 상태 표시

3. `GET /admin/crawl-runs` 응답에 `gpt_fallback_count` 추가:
   - 해당 크롤런에서 GPT 파서 fallback 발동 횟수

**완료 기준:**
- `/admin` 페이지에서 새 지표 표시 확인
- activity_feed 통계 정확성 확인

---

## T-100: 채널 커버리지 리포트 자동화 ✅ 완료

**목표:** 크롤 불가 채널·수집률 저조 채널을 자동으로 감지해 관리자에게 보고.

**선행 조건:** 없음

**작업 내용:**

1. `scripts/coverage_report.py` 생성:
```python
"""
채널 커버리지 리포트.
- 최근 7일간 수집 0건 채널 → dead_channels 목록
- 수집률 급감 채널 (이전 7일 대비 50%+ 감소) → degraded_channels 목록
- 신규 채널 후보 (discover_channels 결과 draft 상태) → draft_channels 목록

결과를 Discord로 발송 또는 CSV로 저장.
"""
```

2. `scripts/scheduler.py` — 주 1회 자동 실행 (일요일 09:00 기존 데이터 감사와 통합):
```python
schedule.every().sunday.at("09:00").do(run_coverage_report)
```

3. 리포트 형식:
```
📊 채널 커버리지 리포트 (2026-03-09)
━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ 수집 불가 채널: 3개
  · shop.example.com (7일째 0건)
  · ...

⚠️ 수집률 저하 채널: 5개
  · store.brand.com (이전 120건 → 현재 30건)
  · ...

📋 승인 대기 draft 채널: 8개
```

4. `GET /admin/coverage-report` 엔드포인트 추가 (최신 리포트 JSON 반환)

**완료 기준:**
- `uv run python scripts/coverage_report.py` 실행 → 리포트 출력
- Discord 웹훅으로 자동 발송 확인
- 스케줄러에 등록 확인

---

## 구현 순서 요약 (T-094~T-100)

```
즉시 (독립):
  T-094 (Custom GPT 연동 검증) — 코드 작업 없음, 설정만
  T-095 (검색 자동완성)
  T-099 (관리자 대시보드 고도화)

단기:
  T-096 (드롭 캘린더)
  T-097 (세일 히트맵)
  T-100 (커버리지 리포트)

선행 필요:
  T-098 (가격 알림) — T-088 PWA 푸시 실동작 후
```

---

# 과업지시서 (T-101 ~ T-105) — Phase 2: AI 쿼리 레이어

> 프로젝트 리포지셔닝: "소비자 대면 가격 비교" → "AI 에이전트가 쿼리하는 패션 브랜드 데이터 인프라"
> 핵심 질문: 어디서 살 수 있나? 최저가는? 사이즈 M 재고 있나?

---

## T-101: `/api/v2/availability` — 채널별 실시간 가용성 API ✨핵심

**목표:** 특정 제품의 모든 채널 재고·가격·사이즈 가용성을 한 번에 반환하는 엔드포인트. AI 에이전트가 "지금 어디서 살 수 있나"를 쿼리하는 핵심 API.

**선행 조건:** 없음 (products 테이블에 size_availability, stock_status 컬럼 이미 존재)

**작업 내용:**

### 1. 스키마 추가 (`src/fashion_engine/api/schemas.py`)

```python
class SizeAvailabilityItem(BaseModel):
    size: str
    in_stock: bool

class AvailabilityChannelItem(BaseModel):
    channel_id: int
    channel_name: str
    channel_url: str
    country: str | None
    price_krw: int | None
    original_price_krw: int | None
    discount_rate: int | None
    is_sale: bool
    in_stock: bool
    stock_status: str | None          # "in_stock" | "low_stock" | "sold_out"
    size_availability: list[SizeAvailabilityItem] | None
    product_url: str
    last_updated: datetime | None

class AvailabilityOut(BaseModel):
    product_key: str
    product_name: str
    brand_name: str | None
    image_url: str | None
    channels: list[AvailabilityChannelItem]   # 재고 있는 채널 우선, price_krw ASC 정렬
    cheapest: AvailabilityChannelItem | None  # channels[0]와 동일 (편의용)
    in_stock_count: int                       # 재고 있는 채널 수
    total_channels: int                       # 전체 채널 수
    last_updated: datetime | None
```

### 2. 서비스 함수 추가 (`src/fashion_engine/services/product_service.py`)

```python
async def get_product_availability(db: AsyncSession, product_key: str) -> AvailabilityOut | None:
    """
    normalized_key 또는 product_key로 매칭되는 모든 채널의 제품 가용성 반환.
    - is_active=True 제품만 포함
    - in_stock=True 채널을 price_krw ASC로 우선 정렬, 그 다음 품절 채널
    - channel JOIN으로 channel_name, country, channel_url 포함
    """
```

쿼리 로직:
```python
# normalized_key 우선 매칭, 없으면 product_key prefix 매칭
stmt = (
    select(Product, Channel)
    .join(Channel, Product.channel_id == Channel.id)
    .where(
        Product.is_active == True,
        or_(
            Product.normalized_key == product_key,
            Product.product_key == product_key,
            Product.product_key.like(f"%:{product_key.split(':')[-1]}"),
        )
    )
    .order_by(
        # 재고 있는 채널 먼저
        case((Product.stock_status == "sold_out", 1), else_=0),
        Product.price_krw.asc().nulls_last(),
    )
)
```

### 3. API 엔드포인트 추가 (`src/fashion_engine/api/products.py`)

```python
@router.get("/api/v2/availability/{product_key:path}", response_model=AvailabilityOut)
async def get_availability(
    product_key: str,
    db: AsyncSession = Depends(get_db),
):
    """
    특정 제품의 채널별 실시간 재고·가격·사이즈 가용성.
    product_key: "palace:box-logo-tee" 또는 normalized_key
    """
    result = await product_service.get_product_availability(db, product_key)
    if not result:
        raise HTTPException(status_code=404, detail="product not found")
    return result
```

**참고:** 기존 `/products/compare/{product_key}` (`PriceComparisonOut`)는 유지. v2는 재고·사이즈 정보를 추가로 포함.

**완료 기준:**
```bash
curl "https://fashion-data-engine-production.up.railway.app/api/v2/availability/palace:box-logo-tee"
# → { product_key, channels: [{channel_name, price_krw, in_stock, size_availability, ...}], cheapest, ... }
```

---

## T-102: `/api/v2/search` — AI 친화적 자연어 검색 API

**목표:** 브랜드명 + 제품명 + 사이즈 + 재고 여부를 조합한 구조화 검색. AI 에이전트가 "팔라스 박스로고 M 재고 있는 곳" 같은 쿼리를 파싱해 결과 반환.

**선행 조건:** T-101 완료 (AvailabilityOut 스키마 재사용)

**작업 내용:**

### 1. 스키마 추가 (`src/fashion_engine/api/schemas.py`)

```python
class V2SearchResult(BaseModel):
    product_key: str
    product_name: str
    brand_name: str | None
    image_url: str | None
    cheapest_price_krw: int | None
    cheapest_channel: str | None
    in_stock_count: int
    total_channels: int
    is_sale: bool
    max_discount_rate: int | None
    size_availability_summary: list[str] | None  # ["XS","S","M"] in_stock 사이즈만

class V2SearchOut(BaseModel):
    query: str
    parsed: dict                    # { brand, product, size, in_stock_only }
    results: list[V2SearchResult]
    total: int
```

### 2. 쿼리 파서 (`src/fashion_engine/services/product_service.py`)

```python
def _parse_search_query(q: str) -> dict:
    """
    자연어 쿼리에서 브랜드/제품/사이즈/재고 조건 추출.
    예: "팔라스 박스로고 M 재고" → { brand: "palace", product: "박스로고", size: "M", in_stock_only: True }
    """
    size_pattern = re.compile(r"\b(XS|S|M|L|XL|XXL|[0-9]{2,3})\b", re.IGNORECASE)
    in_stock_keywords = ["재고", "in stock", "available", "있는"]
    # 브랜드 prefix 매칭은 brands 테이블 slug 기준
```

### 3. API 엔드포인트 (`src/fashion_engine/api/products.py`)

```python
@router.get("/api/v2/search", response_model=V2SearchOut)
async def v2_search(
    q: str = Query(..., min_length=1, max_length=200),
    size: str | None = Query(None),          # 사이즈 필터 (M, L, 270 등)
    in_stock_only: bool = Query(False),      # 재고 있는 채널만
    brand_slug: str | None = Query(None),    # 브랜드 slug 직접 지정
    limit: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db),
):
```

쿼리 로직:
- 제품명 ilike `%q%` 또는 브랜드명 ilike `%q%`
- `size` 파라미터 있으면 `size_availability @> '[{"size": "M", "in_stock": true}]'` JSONB 쿼리
- `in_stock_only=True` → `stock_status != 'sold_out'`
- normalized_key 기준으로 채널별 집계 (cheapest_price, in_stock_count)

**완료 기준:**
```bash
curl "https://.../api/v2/search?q=palace+box+logo&size=M&in_stock_only=true"
# → { results: [{ product_name, cheapest_price_krw, in_stock_count, size_availability_summary: ["M"] }] }
```

---

## T-103: `ProductOut` 스키마에 size_availability, stock_status 노출

**목표:** 기존 `/products/sales`, `/products/ranking` 등 모든 제품 API 응답에 사이즈 재고 정보 추가.

**선행 조건:** 없음

**작업 내용:**

### 1. 스키마 수정 (`src/fashion_engine/api/schemas.py`)

```python
class ProductOut(BaseModel):
    # 기존 필드 모두 유지 +
    size_availability: list[dict] | None = None   # [{"size":"M","in_stock":true}, ...]
    stock_status: str | None = None               # "in_stock" | "low_stock" | "sold_out"
```

### 2. `SaleHighlightOut`에도 추가

```python
class SaleHighlightOut(BaseModel):
    # 기존 필드 유지 +
    stock_status: str | None = None
    in_stock_sizes: list[str] | None = None   # size_availability에서 in_stock=True인 사이즈만 추출
```

### 3. 서비스 레이어에서 `in_stock_sizes` 추출

```python
# SaleHighlight 빌드 시
in_stock_sizes = [
    s["size"] for s in (product.size_availability or [])
    if s.get("in_stock")
] or None
```

**완료 기준:**
```bash
curl ".../products/sales" | jq '.[0].size_availability'
# → [{"size":"S","in_stock":false},{"size":"M","in_stock":true},{"size":"L","in_stock":true}]

curl ".../products/sales" | jq '.[0].stock_status'
# → "in_stock"
```

---

## T-104: 프론트엔드 — 사이즈 재고 뱃지 표시

**목표:** 제품 카드 및 세일 페이지에 재고 있는 사이즈를 한눈에 표시.

**선행 조건:** T-103 완료 (API에서 size_availability 반환)

**작업 내용:**

### 1. `SizeChips` 컴포넌트 생성 (`frontend/src/components/SizeChips.tsx`)

```tsx
interface SizeChipsProps {
  sizes: { size: string; in_stock: boolean }[] | null;
  maxShow?: number;   // 기본 5개, 초과시 "+N" 표시
}

export function SizeChips({ sizes, maxShow = 5 }: SizeChipsProps) {
  if (!sizes?.length) return null;
  const inStock = sizes.filter(s => s.in_stock);
  const show = inStock.slice(0, maxShow);
  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {show.map(s => (
        <span key={s.size}
          className="text-[10px] px-1.5 py-0.5 rounded border border-green-500 text-green-700 bg-green-50">
          {s.size}
        </span>
      ))}
      {inStock.length > maxShow && (
        <span className="text-[10px] px-1.5 py-0.5 text-gray-400">+{inStock.length - maxShow}</span>
      )}
    </div>
  );
}
```

### 2. `stock_status` 뱃지 (`StockBadge` 컴포넌트 또는 인라인)

```tsx
// stock_status에 따른 뱃지
const STOCK_LABEL = {
  in_stock: null,                        // 표시 안 함 (기본)
  low_stock: { text: "재고 부족", color: "text-orange-600 bg-orange-50" },
  sold_out:  { text: "품절", color: "text-red-500 bg-red-50 line-through" },
};
```

### 3. `SaleHighlightCard` / `ProductCard` 컴포넌트에 통합

- `SizeChips` 컴포넌트를 제품 카드 하단에 추가
- `stock_status === "sold_out"` 이면 가격에 line-through + 회색 처리
- `stock_status === "low_stock"` 이면 주황색 "재고 부족" 뱃지

### 4. `/compare/{product_key}` 페이지 — 채널별 사이즈 재고 표시

```tsx
// 채널 목록 테이블의 각 행에 SizeChips 추가
<td><SizeChips sizes={listing.size_availability} /></td>
```

**완료 기준:**
- 세일 페이지에서 재고 있는 사이즈 칩 표시 확인
- 품절 제품 회색 처리 확인
- compare 페이지 채널별 사이즈 표시 확인

---

## T-105: MCP 서버 — AI 에이전트 표준 인터페이스 (기초)

**목표:** Claude·ChatGPT·Cursor 등 MCP 클라이언트가 우리 데이터에 직접 접근할 수 있는 MCP 서버 구현. FastAPI 위에 SSE(Server-Sent Events) 기반 MCP 엔드포인트 추가.

**선행 조건:** T-101, T-102 완료

**참고:** MCP 공식 Python SDK — `pip install mcp` (PyPI: `mcp`)

**작업 내용:**

### 1. 의존성 추가

```bash
uv add mcp
```

### 2. MCP 서버 모듈 생성 (`src/fashion_engine/api/mcp_server.py`)

```python
"""
MCP (Model Context Protocol) 서버.
Claude, ChatGPT, Cursor 등 AI 에이전트가 패션 데이터에 직접 접근.
엔드포인트: GET /mcp  (SSE 스트림)
"""
from mcp.server.fastapi import MCPServer
from fashion_engine.services import product_service, brand_service

mcp = MCPServer("fashion-data-engine")

@mcp.tool()
async def search_products(
    query: str,
    size: str | None = None,
    in_stock_only: bool = False,
    brand_slug: str | None = None,
    limit: int = 10,
) -> dict:
    """패션 제품 검색. 브랜드명, 제품명, 사이즈 조건 지원."""
    async with get_db_session() as db:
        return await product_service.v2_search(db, query, size, in_stock_only, brand_slug, limit)

@mcp.tool()
async def get_availability(product_key: str) -> dict:
    """특정 제품의 채널별 재고·가격·사이즈 가용성. 최저가 채널 포함."""
    async with get_db_session() as db:
        result = await product_service.get_product_availability(db, product_key)
        return result.model_dump() if result else {"error": "not found"}

@mcp.tool()
async def get_brand_sale_status(brand_slug: str) -> dict:
    """특정 브랜드의 현재 세일 현황. 세일 중인 제품 수, 최대 할인율, 채널 목록."""
    async with get_db_session() as db:
        return await brand_service.get_brand_sale_status(db, brand_slug)

@mcp.tool()
async def get_new_drops(limit: int = 10) -> list:
    """최근 신제품 드롭 목록. 브랜드, 채널, 가격 포함."""
    async with get_db_session() as db:
        return await product_service.get_new_drops(db, limit)

@mcp.tool()
async def get_sale_highlights(limit: int = 20) -> list:
    """현재 세일 중인 제품 하이라이트. 긴박감 점수 기준 정렬."""
    async with get_db_session() as db:
        return await product_service.get_sale_highlights_v2(db, limit)
```

### 3. FastAPI에 MCP 라우터 마운트 (`src/fashion_engine/api/main.py`)

```python
from fashion_engine.api.mcp_server import mcp
app.mount("/mcp", mcp.get_asgi_app())
```

### 4. MCP 설정 파일 생성 (프로젝트 루트 `mcp.json`)

```json
{
  "mcpServers": {
    "fashion-data-engine": {
      "url": "https://fashion-data-engine-production.up.railway.app/mcp",
      "description": "패션 브랜드 실시간 재고·가격·세일 데이터"
    }
  }
}
```

**완료 기준:**
```bash
# 로컬 테스트
uv run uvicorn fashion_engine.api.main:app --reload
curl -N http://localhost:8000/mcp  # SSE 스트림 연결 확인

# Claude Desktop에서 fashion-data-engine MCP 서버 연결 후:
# "팔라스 박스로고티 M사이즈 재고 있는 채널 알려줘" 쿼리 동작 확인
```

---

## 구현 순서 요약 (T-101~T-105)

```
즉시 (독립, 병렬 가능):
  T-101 — /api/v2/availability (핵심 API, 백엔드만)
  T-103 — ProductOut에 size_availability 노출 (스키마 확장)

T-101 완료 후:
  T-102 — /api/v2/search (AI 자연어 검색)
  T-104 — 프론트엔드 사이즈 뱃지 (T-103 선행)

T-101, T-102 완료 후:
  T-105 — MCP 서버
```

---

# 과업지시서 (T-106 ~ T-140) — Phase 3~8

> AI-쿼리 인프라 포지셔닝을 완성하는 35개 과업.
> Phase 3(데이터 품질) → Phase 4(AI 레이어) → Phase 5(UX) → Phase 6(운영) → Phase 7(BI) → Phase 8(표준화) 순서.

---

## Phase 3 — 데이터 품질 & 커버리지

---

## T-106: 크롤러 yield 자동 모니터링 + GPT fallback 자동 전환

**목표:** 채널별 수집 제품 수(yield)를 크롤런마다 기록하고, 3회 연속 0건인 채널을 GPT 파서로 자동 전환.

**선행 조건:** T-091(GPT 파서) 완료

**작업 내용:**

1. `crawl_runs` 테이블에 per-channel yield 기록:
```python
# 기존 CrawlRun 모델에 컬럼 추가 OR 별도 channel_crawl_stats 테이블
class ChannelCrawlStat(Base):
    __tablename__ = "channel_crawl_stats"
    id            = Column(Integer, primary_key=True)
    crawl_run_id  = Column(Integer, ForeignKey("crawl_runs.id"))
    channel_id    = Column(Integer, ForeignKey("channels.id"))
    products_found = Column(Integer, default=0)
    parse_method  = Column(String(20))  # "shopify" | "cafe24" | "woocommerce" | "gpt"
    error_msg     = Column(Text, nullable=True)
    crawled_at    = Column(DateTime, default=datetime.utcnow)
```

2. `scripts/crawl_products.py` — 채널 크롤 완료 직후 ChannelCrawlStat INSERT

3. `scripts/auto_switch_parser.py` 신규 스크립트:
```python
# 3회 연속 yield=0인 채널 → channels.use_gpt_parser = True 자동 설정
SELECT channel_id FROM channel_crawl_stats
WHERE products_found = 0
GROUP BY channel_id
HAVING COUNT(*) >= 3
  AND MAX(crawled_at) > NOW() - INTERVAL '7 days'
  AND channel_id NOT IN (SELECT channel_id WHERE products_found > 0 AND crawled_at > NOW() - INTERVAL '7 days')
```

4. Railway 스케줄에 `auto_switch_parser.py` 주 1회 실행 추가 (일요일 09:30)

**완료 기준:**
- `channel_crawl_stats` 테이블에 크롤런 후 데이터 자동 기록
- `GET /admin/channel-health` (T-124)에서 yield 트렌드 확인 가능
- 3회 연속 0건 채널에 `use_gpt_parser=True` 자동 설정 확인

---

## T-107: WooCommerce 세일 감지 + Cafe24 HTML 세일 확장

**목표:** WooCommerce `regular_price` 매핑 검증 및 Cafe24 세일 감지 정확도 개선.

**선행 조건:** 없음 (독립 실행)

**작업 내용:**

1. `src/fashion_engine/crawler/product_crawler.py` — WooCommerce 파서 검증:
```python
# WooCommerce API response에서:
# price = 현재가, regular_price = 정가
# regular_price > price → is_sale = True, compare_at_price = regular_price
# 이미 구현되어 있다면 검증만; 아니면 구현
if wc_product.get("regular_price") and wc_product.get("price"):
    reg = float(wc_product["regular_price"])
    cur = float(wc_product["price"])
    if reg > cur > 0:
        compare_at_price = reg
```

2. Cafe24 HTML 파서 확장 — 추가 CSS 선택자:
```python
CAFE24_SALE_SELECTORS = [
    "del", "s", ".consumer-price", ".org_price", ".origin-price",
    ".prd_org_price", ".price_del", "[class*='origin_price']",
    "[class*='org-price']", "[class*='originalPrice']",
    ".price-origin", ".normal-price", ".price_original",
    # 한국어 패턴: "정가", "소비자가"
]
# 정규식 패턴도 추가: r"정가\s*:?\s*[\d,]+원"
```

3. 검증 스크립트 `scripts/verify_sale_detection.py`:
```bash
# 채널 유형별 세일 감지 수 출력
SELECT c.platform, COUNT(*) FILTER (WHERE p.is_sale) as sale_count, COUNT(*) as total
FROM products p JOIN channels c ON p.channel_id = c.id
GROUP BY c.platform ORDER BY sale_count DESC;
```

**완료 기준:**
- WooCommerce 채널에서 `is_sale=True` 제품 수 > 0
- Cafe24 채널 세일 감지 수 기존 대비 증가
- 검증 쿼리에서 플랫폼별 세일 비율 확인

---

## T-108: 교차채널 제품 매칭 고도화 (Catalog 연결 개선)

**목표:** 같은 제품이 여러 채널에 있을 때 `normalized_key`로 묶어 ProductCatalog 신뢰도 개선.

**선행 조건:** 없음

**작업 내용:**

1. `scripts/improve_normalized_key.py` — 매칭 품질 개선:
```python
# 현재: "brand-slug:handle" 단순 비교
# 개선: 제품명 토크나이즈 후 핵심 모델코드 추출
# 예: "Palace Tri-Ferg Tee AW24" → "palace:tri-ferg-tee"
# 예: "Supreme Box Logo Hoodie FW23 Black" → "supreme:box-logo-hoodie"

import re

def extract_model_code(name: str, brand_slug: str) -> str:
    # 시즌 코드 제거: AW24, FW23, SS25, 2024, 2025
    name = re.sub(r'\b(AW|FW|SS|RE)\d{2,4}\b', '', name, flags=re.I)
    # 색상 제거: Black, White, Navy, ...
    colors = ['black', 'white', 'navy', 'grey', 'gray', 'red', 'blue', 'green']
    for c in colors:
        name = re.sub(rf'\b{c}\b', '', name, flags=re.I)
    # 슬러그화: 소문자 + 하이픈
    slug = re.sub(r'[^\w\s]', '', name).strip().lower()
    slug = re.sub(r'\s+', '-', slug)
    return f"{brand_slug}:{slug}"
```

2. `product_catalog` 테이블 — `channel_count` 컬럼 갱신:
```sql
UPDATE product_catalog pc
SET channel_count = (
    SELECT COUNT(DISTINCT channel_id)
    FROM products
    WHERE normalized_key = pc.normalized_key AND is_active = true
);
```

3. `GET /catalog/{normalized_key}` 응답에 매칭 채널 수 포함 확인

4. `match_confidence` 점수 0.8 미만인 제품 재처리:
```python
# match_confidence 재계산: 브랜드 일치 + 모델코드 유사도
# brand 일치: +0.5, 모델코드 Levenshtein < 0.3: +0.5
```

**완료 기준:**
- `channel_count >= 2`인 ProductCatalog 엔트리 > 1000개
- `match_confidence` NULL 비율 50% 이하로 감소
- `/catalog/palace:box-logo-tee` 응답에 여러 채널 표시 확인

---

## T-109: 이미지 URL 유효성 검증 자동화

**목표:** 깨진 이미지 URL 탐지 → is_active=False 처리 또는 재크롤 트리거.

**선행 조건:** 없음

**작업 내용:**

1. `scripts/verify_image_urls.py` 생성:
```python
"""
products.image_url을 HEAD 요청으로 검증.
404/403/timeout → image_url = NULL 업데이트.
"""
import asyncio, aiohttp

async def check_url(session, url) -> bool:
    try:
        async with session.head(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
            return r.status < 400
    except Exception:
        return False

# 병렬 500개씩 처리
```

2. `products` 테이블에 `image_verified_at` DateTime 컬럼 추가 (Alembic):
```python
# 검증 날짜 기록 → 30일마다 재검증
```

3. Railway 스케줄에 주 1회 실행 (토요일 05:00) 추가

4. 검증 실패 시 해당 채널 재크롤 트리거 옵션 (`--refetch-broken`):
```python
# 이미지 깨진 제품이 5개 이상인 채널 → 재크롤 대상 목록 출력
```

**완료 기준:**
- NULL image_url 비율 감소 또는 깨진 URL 탐지 수 집계 확인
- `products.image_verified_at` 갱신 확인

---

## T-110: Shopify 컬렉션 기반 전체 카탈로그 수집 강화

**목표:** Shopify JSON API `/products.json`의 태그·컬렉션·variant를 완전 활용해 카테고리/성별/시즌 자동 추출.

**선행 조건:** 없음

**작업 내용:**

1. `src/fashion_engine/crawler/product_crawler.py` — Shopify 파서 확장:
```python
# 기존: 태그에서 gender/subcategory 추출 (부분적)
# 추가: Shopify 컬렉션 페이지에서 카테고리 정보 보강
# /collections.json → [{ id, handle, title }]

SHOPIFY_CATEGORY_MAP = {
    "footwear": "shoes", "shoes": "shoes", "sneakers": "shoes",
    "tops": "top", "tees": "top", "t-shirts": "top",
    "hoodies": "outer", "jackets": "outer", "outerwear": "outer",
    "bottoms": "bottom", "pants": "bottom", "shorts": "bottom",
    "accessories": "accessory", "bags": "bag", "caps": "cap",
}

# 태그에서 성별 추출 강화:
GENDER_TAGS = {
    "mens": "men", "men's": "men", "womens": "women",
    "women's": "women", "unisex": "unisex", "kids": "kids",
}
```

2. `_parse_product`에서 컬렉션 핸들을 subcategory로 매핑

3. `is_new` 자동 감지: Shopify `product_type` = "new" OR 태그에 "new-arrival" 포함

4. 기존 제품 retroactive 재분류:
```python
# scripts/reclassify_from_shopify_tags.py
# 태그 정보가 있는 채널 제품 subcategory/gender 재분류
```

**완료 기준:**
- `SELECT subcategory, COUNT(*) FROM products GROUP BY subcategory` — 기존 대비 NULL 비율 감소
- `gender IS NOT NULL` 비율 60%+ (현재 확인 필요)
- Shopify 채널에서 수집한 제품에 `is_new` 자동 설정 확인

---

## T-111: 채널 자동 재활성화 파이프라인

**목표:** `is_active=False`인 채널을 주 1회 자동 재probe → 복구된 채널 자동 활성화.

**선행 조건:** 없음

**작업 내용:**

1. `scripts/reactivate_channels.py` 신규 스크립트:
```python
"""
비활성 채널을 probe해서 접근 가능하면 자동 재활성화.
사용법: uv run python scripts/reactivate_channels.py --limit 30
"""
# 비활성 채널 중 last_checked_at이 7일 이상 된 것만 대상
# channel_probe 로직 재사용
# 접근 가능 → is_active=True + Discord 알림 ("채널 복구: {name}")
```

2. `channels` 테이블에 `last_probe_at` DateTime 컬럼 추가 (Alembic)

3. Railway 스케줄 추가: 매주 화요일 04:00 실행

4. `GET /admin/channel-health` (T-124)에서 재활성화 이력 표시

**완료 기준:**
- `uv run python scripts/reactivate_channels.py --dry-run` 정상 실행
- 접근 가능 채널 자동 활성화 + Discord 알림 확인

---

## Phase 4 — AI 쿼리 레이어 고도화

---

## T-112: pgvector 의미 검색 (Semantic Search)

**목표:** 제품명 + 설명의 벡터 임베딩을 저장해 "궁금해 팔라스 체크 패턴 니트" 같은 자연어 쿼리에도 유사 제품 반환.

**선행 조건:** T-102 완료. Railway PostgreSQL에 pgvector 확장 활성화 필요.

**작업 내용:**

1. Railway PostgreSQL에 pgvector 활성화:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

2. Alembic 마이그레이션:
```python
# products 테이블에 임베딩 컬럼 추가
op.execute("CREATE EXTENSION IF NOT EXISTS vector")
op.add_column("products", sa.Column("name_embedding", Vector(384), nullable=True))
op.execute("CREATE INDEX ix_products_name_embedding ON products USING ivfflat (name_embedding vector_cosine_ops)")
```

3. `scripts/generate_embeddings.py`:
```python
# SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2") — 무료, 384차원
# 배치 500개씩 임베딩 → products.name_embedding UPDATE
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
```

4. `src/fashion_engine/services/search_service_v2.py` — 의미 검색 옵션:
```python
async def semantic_search(db, q: str, limit=20) -> list[ProductOut]:
    q_embedding = model.encode(q).tolist()
    # pgvector cosine similarity
    result = await db.execute(
        text("""
            SELECT *, 1 - (name_embedding <=> :emb) AS similarity
            FROM products
            WHERE name_embedding IS NOT NULL AND is_active = true
            ORDER BY name_embedding <=> :emb
            LIMIT :limit
        """),
        {"emb": str(q_embedding), "limit": limit}
    )
```

5. `GET /api/v2/search?mode=semantic` 파라미터 추가

**완료 기준:**
- "팔라스 체크 패턴" 검색 → "Palace Check Knit" 등 관련 제품 반환
- 응답시간 < 500ms (ivfflat 인덱스 기준)

---

## T-113: `/api/v2/brands/{slug}/sale-intel` — 브랜드 세일 패턴 API

**목표:** AI가 "팔라스 언제 세일해?" 에 답할 수 있도록 브랜드별 세일 패턴 API 제공.

**선행 조건:** T-101 완료

**작업 내용:**

1. `src/fashion_engine/services/brand_service.py` — 신규 함수:
```python
async def get_brand_sale_intel(db, brand_slug: str) -> dict:
    # 현재 세일 현황
    current_sale_count = SELECT COUNT(*) FROM products WHERE brand.slug=? AND is_sale=true
    current_max_discount = SELECT MAX(discount_rate) FROM products WHERE brand.slug=? AND is_sale=true

    # 최근 세일 이력 (price_history 기반)
    recent_sales = SELECT DATE_TRUNC('month', crawled_at), COUNT(DISTINCT product_id), AVG(discount_rate)
                   FROM price_history ph JOIN products p ON ph.product_id=p.id
                   JOIN brands b ON p.brand_id=b.id
                   WHERE b.slug=? AND ph.is_sale=true
                   GROUP BY 1 ORDER BY 1 DESC LIMIT 12

    # 월별 세일 빈도 (시즌성)
    # 세일 중인 채널 목록 + URL
    # 마지막 세일 시작일 (sale_started_at 기준)
```

2. 응답 스키마:
```python
class BrandSaleIntelOut(BaseModel):
    brand_slug: str
    brand_name: str
    is_currently_on_sale: bool
    current_sale_products: int
    current_max_discount_rate: int | None
    sale_channels: list[dict]           # [{ channel_name, url, products_on_sale }]
    monthly_sale_history: list[dict]    # [{ month, product_count, avg_discount }]
    last_sale_started_at: datetime | None
    typical_sale_months: list[int]      # 세일 빈도 높은 월 (1-12)
```

3. `GET /api/v2/brands/{slug}/sale-intel` 라우트 추가 (`src/fashion_engine/api/v2.py`)

4. MCP tool `get_brand_sale_status` 업데이트 — 이 API 호출로 연결

**완료 기준:**
```bash
curl "/api/v2/brands/palace/sale-intel" | jq '.typical_sale_months'
# → [1, 6, 7, 12] 같은 월 목록
```

---

## T-114: Redis 캐싱 레이어

**목표:** MCP/v2 엔드포인트에 Redis TTL 캐싱 적용해 응답시간 50% 단축 + Railway DB 쿼리 부하 감소.

**선행 조건:** Railway Redis 서비스 추가 (무료 플랜 가능)

**작업 내용:**

1. `pyproject.toml`에 `redis[hiredis]>=5.0` 추가

2. `src/fashion_engine/config.py`에 `redis_url: str | None = None` 추가

3. `src/fashion_engine/cache.py` 신규:
```python
import redis.asyncio as aioredis
import json
from functools import wraps

_redis: aioredis.Redis | None = None

def get_redis():
    global _redis
    if _redis is None and settings.redis_url:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis

async def cached(key: str, ttl: int, fetch_fn):
    """캐시 히트 → 즉시 반환. 미스 → fetch_fn 실행 후 캐싱."""
    r = get_redis()
    if r:
        cached = await r.get(key)
        if cached:
            return json.loads(cached)
    result = await fetch_fn()
    if r and result:
        await r.setex(key, ttl, json.dumps(result, default=str))
    return result
```

4. 적용 대상 엔드포인트 (TTL):
   - `/api/v2/availability/{key}` → TTL 300초 (5분)
   - `/api/v2/brands/{slug}/sale-intel` → TTL 600초 (10분)
   - `/api/v2/search` → TTL 60초 (1분)
   - `/products/sales` → TTL 120초 (2분)

5. 크롤러가 채널 완료 시 관련 캐시 키 무효화:
```python
await r.delete(f"availability:{product_key}")
```

**완료 기준:**
- Redis 없으면 캐시 없이 정상 동작 (graceful degradation)
- Cache hit 시 응답시간 < 50ms
- `/admin` 페이지에 cache hit rate 표시 (optional)

---

## T-115: 실시간 WebSocket 피드 스트리밍

**목표:** `/ws/feed` WebSocket 엔드포인트 — 크롤러가 새 이벤트 감지 시 즉시 클라이언트에 push.

**선행 조건:** T-083(activity_feed) 완료

**작업 내용:**

1. `src/fashion_engine/api/main.py` — WebSocket 라우터 추가:
```python
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def broadcast(self, message: dict):
        for ws in self.active[:]:
            try:
                await ws.send_json(message)
            except Exception:
                self.active.remove(ws)

manager = ConnectionManager()

@app.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket):
    await websocket.accept()
    manager.active.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive ping
    except WebSocketDisconnect:
        manager.active.remove(websocket)
```

2. `scripts/watch_agent.py` — 이벤트 저장 후 WebSocket broadcast:
```python
# activity_feed INSERT 직후
import httpx
await httpx.AsyncClient().post(
    "http://localhost:8000/internal/broadcast",
    json=event_dict,
    headers={"X-Internal-Key": settings.internal_key}
)
```

3. `frontend/src/app/feed/page.tsx` — WebSocket 연결:
```typescript
useEffect(() => {
  const ws = new WebSocket(`${WS_URL}/ws/feed`);
  ws.onmessage = (e) => {
    const event = JSON.parse(e.data);
    setFeedItems(prev => [event, ...prev].slice(0, 100));
  };
  return () => ws.close();
}, []);
```

**완료 기준:**
- 크롤 실행 후 브라우저 콘솔에서 WebSocket 메시지 수신 확인
- 피드 페이지에서 실시간 이벤트 추가 확인

---

## T-116: `/api/v2/price-history/{product_key}` — 교차채널 가격 추이

**목표:** 동일 제품(normalized_key)의 채널별 가격 히스토리를 통합해 "최저가 달성 시점"을 AI가 알 수 있게.

**선행 조건:** T-101 완료

**작업 내용:**

1. 서비스 함수:
```python
async def get_cross_channel_price_history(db, product_key: str, days: int = 90) -> dict:
    # normalized_key 또는 product_key로 product_id들 조회
    # price_history JOIN products JOIN channels
    # 채널별 일별 최저가 집계
    # 역대 최저가 + 달성 채널 + 날짜
```

2. 응답 스키마:
```python
class PriceHistoryPoint(BaseModel):
    date: date
    channel_name: str
    price_krw: int
    is_sale: bool

class CrossChannelPriceHistoryOut(BaseModel):
    product_key: str
    product_name: str
    history: list[PriceHistoryPoint]     # 날짜순
    all_time_low: PriceHistoryPoint | None
    current_lowest: PriceHistoryPoint | None
    price_trend: str                      # "falling" | "stable" | "rising"
```

3. `GET /api/v2/price-history/{product_key:path}` 라우트 추가

4. 프론트엔드 — `/compare/{key}` 페이지에 교차채널 가격 차트 추가 (Recharts):
```typescript
// 기존 단일채널 히스토리 → 교차채널 비교 차트
// X축: 날짜, Y축: 가격, 라인별 채널 색상 구분
```

**완료 기준:**
```bash
curl "/api/v2/price-history/palace:box-logo-tee?days=30" | jq '.all_time_low'
```

---

## T-117: MCP 서버 고도화 — 인증 + rate limit + resource 추가

**목표:** T-105 기초 구현을 프로덕션 수준으로 고도화. API 키 인증, 분당 요청 제한, 브랜드 목록 resource 추가.

**선행 조건:** T-105, T-113 완료

**작업 내용:**

1. API 키 인증 미들웨어:
```python
# MCP 연결 시 Authorization: Bearer {API_KEY} 헤더 검증
# .env: MCP_API_KEY=...
```

2. rate limit (메모리 기반, Redis 없어도 동작):
```python
from collections import defaultdict
import time

_request_counts: dict[str, list[float]] = defaultdict(list)

def check_rate_limit(api_key: str, max_rpm: int = 60) -> bool:
    now = time.time()
    window = [t for t in _request_counts[api_key] if now - t < 60]
    _request_counts[api_key] = window
    if len(window) >= max_rpm:
        return False
    _request_counts[api_key].append(now)
    return True
```

3. MCP resource 추가 (`@mcp.resource`):
```python
@mcp.resource("brands://list")
async def list_brands() -> str:
    """활성 브랜드 목록 (slug, name, tier)"""

@mcp.resource("channels://active")
async def list_active_channels() -> str:
    """활성 채널 목록 (name, platform, country)"""
```

4. `get_brand_sale_status` tool → T-113 API 연결

5. 프로젝트 루트에 `mcp.json` 생성 (Claude Desktop 설정용):
```json
{
  "mcpServers": {
    "fashion-data-engine": {
      "url": "https://fashion-data-engine-api.up.railway.app/mcp",
      "headers": { "Authorization": "Bearer ${MCP_API_KEY}" }
    }
  }
}
```

**완료 기준:**
- 잘못된 API 키로 연결 시 401 반환
- 분당 60회 초과 시 429 반환
- Claude Desktop에서 `fashion-data-engine` MCP 연결 + tool 호출 성공

---

## Phase 5 — 프론트엔드 UX 고도화

---

## T-118: 홈페이지 — AI 검색 중심 재설계

**목표:** 홈페이지(`/`)를 "AI가 쿼리하는 패션 브랜드 데이터" 포지셔닝에 맞게 재설계.

**선행 조건:** T-102(자연어 검색 API) 완료

**작업 내용:**

1. `frontend/src/app/page.tsx` 전면 개편:

```tsx
// 구성:
// 1. 헤로 섹션: "패션 브랜드 실시간 데이터 인프라" + 자연어 검색창
// 2. 검색창: 플레이스홀더 타이핑 애니메이션
//    "팔라스 박스로고티 M사이즈 재고있는 곳" → "슈프림 세일 언제해?" → ...
// 3. 실시간 통계: 채널 N개 | 제품 N만개 | 최근 업데이트 N분 전
// 4. 최신 세일 하이라이트 (가로 스크롤 카드 3~5개)
// 5. 신규 드롭 섹션 (오늘 등록된 제품)
// 6. "AI 에이전트로 사용하기" — MCP 연결 가이드 배너

const SEARCH_PLACEHOLDERS = [
  "팔라스 박스로고티 M사이즈 재고있는 채널은?",
  "슈프림 요즘 세일 많이 해?",
  "나이키 SB 덩크 최저가 어디서 살 수 있어?",
  "최근 2주 안에 드롭된 신제품 알려줘",
];
```

2. 검색창 → `/api/v2/search` 호출 → 인라인 결과 표시 (페이지 이동 없이)

3. 실시간 통계는 `/admin/intel-status` API에서 숫자 가져와 표시

**완료 기준:**
- 홈페이지에서 자연어 검색 후 인라인 결과 표시
- 타이핑 애니메이션 동작
- Lighthouse 성능 점수 > 80

---

## T-119: 제품 상세 페이지 `/product/{key}`

**목표:** 교차채널 가격 비교 + 사이즈 재고를 한눈에 보는 제품 상세 페이지.

**선행 조건:** T-101, T-103 완료

**작업 내용:**

1. `frontend/src/app/product/[key]/page.tsx` 생성:

```tsx
// 구성:
// 1. 제품 헤더: 이미지, 브랜드, 제품명
// 2. 채널별 가격 테이블 (재고 있는 것 우선):
//    | 채널 | 가격 | 할인율 | 재고 | 사이즈 | [바로 구매] |
// 3. 사이즈 재고 현황 (채널별 SizeChips 그리드)
// 4. 가격 추이 차트 (T-116 API 사용)
// 5. 관련 제품 추천 (같은 브랜드 세일 중인 제품)
// 6. [알림 설정] 버튼 (T-098 가격 알림 연동)

// URL 라우팅: /product/palace:box-logo-tee
// → GET /api/v2/availability/palace:box-logo-tee
```

2. 메타태그 (OpenGraph):
```tsx
export async function generateMetadata({ params }) {
  const data = await getAvailability(params.key);
  return {
    title: `${data.product_name} | 채널별 최저가`,
    description: `현재 ${data.in_stock_anywhere ? '재고 있음' : '품절'}. 최저가 ${data.lowest_price?.price_krw?.toLocaleString()}원`,
    openGraph: { images: [data.channels[0]?.image_url] }
  };
}
```

3. 기존 `/compare/{key}` → `/product/{key}` 리다이렉트

**완료 기준:**
- `/product/palace:box-logo-tee` 페이지 정상 렌더링
- 채널별 가격 테이블 + 사이즈 재고 표시
- OG 메타태그 확인 (Twitter Card Validator)

---

## T-120: 브랜드 페이지 강화 — 세일 패턴 + 채널 커버리지

**목표:** 브랜드 페이지(`/brands/{slug}`)에 세일 히스토리 차트 + 채널별 커버리지 추가.

**선행 조건:** T-113 완료

**작업 내용:**

1. `frontend/src/app/brands/[slug]/page.tsx` — 섹션 추가:

```tsx
// 기존: 브랜드 정보 + 제품 목록
// 추가:
// 1. 세일 인텔 카드: "현재 세일 N개 | 최대 할인율 N% | 마지막 세일: N일 전"
// 2. 월별 세일 빈도 바차트 (Recharts): 어느 달에 세일 많이 하나
// 3. 취급 채널 목록 + 채널별 현재 세일 제품 수
// 4. "이 브랜드 세일 시작하면 알림 받기" 버튼 (T-098 연동)
```

2. `GET /api/v2/brands/{slug}/sale-intel` 데이터 사용

3. 브랜드 티어 배지 표시 (high-end / premium / street / sports):
```tsx
const TIER_COLORS = {
  "high-end": "bg-amber-100 text-amber-800",
  "premium": "bg-purple-100 text-purple-800",
  "street": "bg-zinc-900 text-white",
  "sports": "bg-blue-100 text-blue-800",
}
```

**완료 기준:**
- 브랜드 페이지에 세일 히스토리 바차트 표시
- "현재 세일 중인 채널" 목록 + 링크 클릭 가능
- 월별 세일 빈도에서 시즌 패턴 시각화

---

## T-121: 모바일 최적화 + PWA 설정

**목표:** 모바일 사용성 전면 개선 + PWA 설치 가능하게 설정.

**선행 조건:** 없음 (독립)

**작업 내용:**

1. `frontend/public/manifest.json` 생성:
```json
{
  "name": "Fashion Data Engine",
  "short_name": "FashionDE",
  "description": "패션 브랜드 실시간 가격·재고 인텔",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#000000",
  "theme_color": "#000000",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

2. `frontend/src/app/layout.tsx` — manifest 링크 + viewport 설정:
```tsx
<link rel="manifest" href="/manifest.json" />
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
```

3. 모바일 터치 UX 개선:
   - 제품 카드: 최소 높이 44px 터치 타겟
   - 가로 스크롤 탭: 스와이프 지원
   - 하단 고정 네비게이션 바 (모바일 전용):
     - 홈 / 세일 / 드롭 / 검색 / 피드

4. 이미지 최적화: `next/image` 컴포넌트로 교체 (자동 WebP 변환)

**완료 기준:**
- Chrome에서 "앱 설치" 배너 표시
- Lighthouse 모바일 점수 > 75
- 5인치 화면에서 레이아웃 깨짐 없음

---

## T-122: OpenGraph + 소셜 공유 최적화

**목표:** 제품/세일 URL을 카카오톡·트위터에 공유할 때 이미지+가격 미리보기 표시.

**선행 조건:** T-119 완료

**작업 내용:**

1. 동적 OG 이미지 생성 (`frontend/src/app/api/og/route.tsx`):
```tsx
// @vercel/og 또는 next/og 사용
// 제품명 + 최저가 + 브랜드 로고를 텍스트로 OG 이미지 생성
import { ImageResponse } from 'next/og';

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const name = searchParams.get('name');
  const price = searchParams.get('price');
  const brand = searchParams.get('brand');

  return new ImageResponse(
    <div style={{ display: 'flex', background: '#000', width: '1200px', height: '630px' }}>
      <div style={{ color: '#fff', fontSize: 60, padding: 80 }}>
        <div style={{ color: '#888', fontSize: 32 }}>{brand}</div>
        <div>{name}</div>
        <div style={{ color: '#4ade80', fontSize: 40, marginTop: 20 }}>최저 {price}원</div>
      </div>
    </div>
  );
}
```

2. 각 페이지 `generateMetadata`에 OG 이미지 URL 추가:
```tsx
openGraph: {
  images: [`/api/og?name=${product_name}&price=${lowest_price}&brand=${brand}`]
}
```

3. 카카오 공유 SDK 연동 (선택):
   - 제품 카드에 [카카오 공유] 버튼 추가

**완료 기준:**
- Twitter Card Validator에서 이미지 미리보기 확인
- 카카오톡 URL 공유 시 썸네일 표시

---

## T-123: Next.js ISR 전환 — 핫 페이지 정적 생성

**목표:** `/brands/[slug]`, `/product/[key]` 페이지를 ISR로 전환해 초기 로드 속도 개선.

**선행 조건:** T-119, T-120 완료

**작업 내용:**

1. 브랜드 상세 페이지 ISR:
```typescript
// ISR: 5분마다 재생성
export const revalidate = 300;

export async function generateStaticParams() {
  // 상위 100개 브랜드만 빌드 시 pre-generate
  const brands = await fetch(`${API_URL}/brands?limit=100`).then(r => r.json());
  return brands.map((b: Brand) => ({ slug: b.slug }));
}
```

2. 제품 상세 페이지 ISR:
```typescript
export const revalidate = 180; // 3분 — 재고 정보 반영
```

3. 홈페이지 — 통계 숫자 ISR (1분):
```typescript
export const revalidate = 60;
```

4. API route에서 `Cache-Control` 헤더 설정:
```python
# FastAPI response에 캐시 힌트 추가
response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
```

**완료 기준:**
- `next build` 성공 + 주요 페이지 pre-render 확인
- Lighthouse 성능 점수 90+ (ISR 정적 페이지 기준)

---

## Phase 6 — 운영 & 모니터링

---

## T-124: 채널 건강 대시보드 (`/admin/channel-health`)

**목표:** 채널별 yield 트렌드, 파서 방식, 마지막 성공 크롤 시각을 한눈에 확인.

**선행 조건:** T-106 완료 (channel_crawl_stats)

**작업 내용:**

1. `src/fashion_engine/api/admin.py` — 신규 엔드포인트:
```python
@router.get("/channel-health")
async def get_channel_health(db: AsyncSession = Depends(get_db)):
    """
    채널별 최근 5회 크롤 yield 통계.
    응답: [{ channel_id, channel_name, platform, recent_yields: [int],
             avg_yield, last_success_at, parse_method, status }]
    status: "healthy" | "degraded" | "dead"
    """
```

2. `frontend/src/app/admin/channel-health/page.tsx` 신규:
   - 테이블: 채널명 / 플랫폼 / 최근 yield 스파크라인 / 상태 배지
   - 필터: healthy / degraded / dead
   - [재활성화 시도] 버튼 → `POST /admin/channels/{id}/reactivate`

3. 상태 기준:
   - `healthy`: 최근 3회 중 2회 이상 yield > 0
   - `degraded`: 최근 3회 중 1회 yield > 0
   - `dead`: 최근 3회 모두 yield = 0

**완료 기준:**
- `/admin/channel-health` 페이지에서 채널 상태 목록 확인
- 상태별 필터 동작
- [재활성화] 버튼 클릭 → probe 실행 확인

---

## T-125: 크롤 비용 추적 (LLM 토큰 사용량)

**목표:** GPT 파서 사용 채널별 토큰 소비량 추적 → 비용 예측 + 고비용 채널 최적화.

**선행 조건:** T-106 완료

**작업 내용:**

1. `channel_crawl_stats` 테이블에 컬럼 추가:
```python
llm_prompt_tokens  = Column(Integer, nullable=True)
llm_completion_tokens = Column(Integer, nullable=True)
llm_provider       = Column(String(20), nullable=True)  # "groq" | "gemini" | "openai"
llm_cost_usd       = Column(Numeric(10, 6), nullable=True)  # 추정 비용
```

2. `GPTParseResult`의 토큰 정보를 `channel_crawl_stats`에 기록

3. 비용 계산 테이블:
```python
LLM_COSTS_PER_1K = {
    "groq": 0.0,          # 무료
    "gemini": 0.000075,   # $0.075/1M input
    "openai": 0.00015,    # $0.15/1M input (gpt-4o-mini)
}
```

4. `GET /admin/llm-costs` 엔드포인트:
```python
# 일별/채널별 LLM 비용 집계
# 월간 총 예상 비용 표시
```

**완료 기준:**
- GPT 파서 실행 후 `channel_crawl_stats.llm_prompt_tokens` 기록 확인
- `/admin/llm-costs` 에서 월간 비용 추정치 확인

---

## T-126: API 응답시간 모니터링 + 슬로 쿼리 알림

**목표:** p95 응답시간 > 1초인 엔드포인트 자동 감지 + Discord 알림.

**선행 조건:** 없음

**작업 내용:**

1. FastAPI 미들웨어 추가 (`src/fashion_engine/api/main.py`):
```python
import time
from collections import defaultdict

_response_times: dict[str, list[float]] = defaultdict(list)

@app.middleware("http")
async def record_response_time(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    elapsed = time.monotonic() - start
    path = request.url.path
    _response_times[path].append(elapsed)
    # 최근 100개만 유지
    _response_times[path] = _response_times[path][-100:]
    return response
```

2. `GET /admin/performance` 엔드포인트:
```python
# 엔드포인트별 p50/p95/p99 + 평균 응답시간
```

3. `scripts/scheduler.py` — 1시간마다 p95 > 1초 엔드포인트 Discord 알림:
```python
# 내부 API 호출 → /admin/performance 결과 파싱 → 슬로 쿼리 Discord 알림
```

4. DB 슬로 쿼리 로깅 (PostgreSQL):
```python
# SQLAlchemy event listener로 > 500ms 쿼리 로깅
from sqlalchemy import event
@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.monotonic())
```

**완료 기준:**
- `/admin/performance` 에서 엔드포인트별 p95 응답시간 확인
- 인위적으로 슬로 쿼리 유발 시 Discord 알림 수신

---

## T-127: 자동 DB 백업 (Railway Volume → S3)

**목표:** Railway PostgreSQL 주 1회 자동 pg_dump → Cloudflare R2 또는 S3 업로드.

**선행 조건:** S3/R2 버킷 생성 (AWS free tier 또는 Cloudflare R2)

**작업 내용:**

1. `scripts/backup_db.py` 생성:
```python
"""
PostgreSQL pg_dump → gzip → S3/R2 업로드.
사용법: uv run python scripts/backup_db.py
"""
import subprocess, boto3, datetime, os

def backup():
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dump_path = f"/tmp/fashion_db_{ts}.sql.gz"

    # pg_dump (Railway DB URL에서 host/port/user/pass 파싱)
    subprocess.run(
        f"pg_dump {os.environ['RAILWAY_DATABASE_URL']} | gzip > {dump_path}",
        shell=True, check=True
    )

    # S3 업로드
    s3 = boto3.client("s3",
        endpoint_url=os.environ.get("S3_ENDPOINT"),
        aws_access_key_id=os.environ["S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["S3_SECRET_KEY"],
    )
    s3.upload_file(dump_path, os.environ["S3_BUCKET"], f"backups/{ts}.sql.gz")
    print(f"Backup uploaded: {ts}.sql.gz")

    # 30일 이상 된 백업 삭제
```

2. `config.py`에 S3 환경변수 추가:
```python
s3_endpoint: str | None = None
s3_access_key: str | None = None
s3_secret_key: str | None = None
s3_bucket: str | None = None
```

3. Railway 스케줄: 매주 일요일 02:00 실행

**완료 기준:**
- S3/R2 버킷에 `.sql.gz` 파일 업로드 확인
- 복원 테스트: `gunzip | psql` 정상 실행

---

## T-128: 데이터 신선도 지표 (last_crawled_at per channel)

**목표:** 각 채널의 마지막 성공 크롤 시각을 추적해 "N시간 전 업데이트" 표시.

**선행 조건:** T-106 완료

**작업 내용:**

1. `channels` 테이블에 `last_crawled_at` DateTime 컬럼 추가 (Alembic)

2. `scripts/crawl_products.py` — 채널 크롤 성공(yield > 0) 시 `last_crawled_at = now()` 업데이트

3. `src/fashion_engine/api/schemas.py` — `ChannelOut`에 `last_crawled_at`, `data_freshness_hours` 추가:
```python
@property
def data_freshness_hours(self) -> float | None:
    if self.last_crawled_at:
        return (datetime.utcnow() - self.last_crawled_at).total_seconds() / 3600
    return None
```

4. `GET /api/v2/availability/{key}` 응답에 `channel.last_crawled_at` 포함

5. 프론트엔드 — 채널 카드에 "N시간 전 업데이트" 표시:
```tsx
const freshness = channel.data_freshness_hours;
const label = freshness < 24 ? `${Math.round(freshness)}시간 전` : `${Math.round(freshness/24)}일 전`;
```

**완료 기준:**
- 크롤 후 `channels.last_crawled_at` 갱신 확인
- `/api/v2/availability/{key}` 응답에 `last_crawled_at` 포함

---

## T-129: Sentry 에러 트래킹 연동

**목표:** 백엔드 예외 + 프론트엔드 JS 에러를 Sentry로 캡처해 자동 알림.

**선행 조건:** Sentry 무료 계정 생성 (https://sentry.io — 무료 플랜 5K event/월)

**작업 내용:**

1. 백엔드 (`pyproject.toml`):
```toml
sentry-sdk = { version = ">=2.0", extras = ["fastapi"] }
```

2. `src/fashion_engine/api/main.py`:
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=0.1,  # 10% 트레이싱
        environment="production",
    )
```

3. `config.py`에 `sentry_dsn: str | None = None` 추가

4. 프론트엔드 (`frontend/package.json`):
```bash
npm install @sentry/nextjs
npx @sentry/wizard@latest -i nextjs
```

5. 크롤러 에러 캡처:
```python
import sentry_sdk
# except Exception as exc:
#     sentry_sdk.capture_exception(exc)
```

**완료 기준:**
- 의도적 에러 발생 시 Sentry 대시보드에 캡처 확인
- Discord 알림 연동 (Sentry → Discord webhook)

---

## Phase 7 — 비즈니스 인텔리전스

---

## T-130: 브랜드 세일 시즌성 분석 API

**목표:** "팔라스는 보통 몇 월에 세일해?" 질문에 데이터 기반으로 답하는 분석 API.

**선행 조건:** T-113 완료

**작업 내용:**

1. `src/fashion_engine/services/analytics_service.py` 신규:
```python
async def get_brand_seasonality(db, brand_slug: str) -> dict:
    """
    월별 세일 제품 수 집계 (price_history 기반, 최근 2년).
    """
    result = await db.execute(text("""
        SELECT
            EXTRACT(MONTH FROM ph.crawled_at) as month,
            COUNT(DISTINCT ph.product_id) as sale_count,
            AVG(ph.discount_rate) as avg_discount,
            COUNT(*) as data_points
        FROM price_history ph
        JOIN products p ON ph.product_id = p.id
        JOIN brands b ON p.brand_id = b.id
        WHERE b.slug = :slug
          AND ph.is_sale = true
          AND ph.crawled_at > NOW() - INTERVAL '2 years'
        GROUP BY 1
        ORDER BY 1
    """), {"slug": brand_slug})

    monthly = {int(r.month): {"sale_count": r.sale_count, "avg_discount": float(r.avg_discount or 0)} for r in result}
    peak_months = sorted(monthly, key=lambda m: monthly[m]["sale_count"], reverse=True)[:3]
    return {"monthly": monthly, "peak_sale_months": peak_months}
```

2. `GET /api/v2/brands/{slug}/seasonality` 라우트 추가

3. 프론트엔드 — 브랜드 페이지에 시즌성 히트맵 추가:
   - 12개월 × 할인율 color scale (진한 색 = 세일 많음)

**완료 기준:**
```bash
curl "/api/v2/brands/palace/seasonality" | jq '.peak_sale_months'
# → [1, 7, 12] 등 실제 데이터 기반 월 목록
```

---

## T-131: 사이즈 희소성 점수 (Size Scarcity Score)

**목표:** "M 사이즈 거의 없어" 상황을 점수화해 구매 긴박감 정보 제공.

**선행 조건:** T-101, T-103 완료

**작업 내용:**

1. 희소성 점수 계산:
```python
def compute_size_scarcity(size_availability: list[dict] | None) -> float | None:
    """
    0.0 = 모든 사이즈 풍부 / 1.0 = 거의 품절
    공식: 1 - (in_stock_count / total_count)
    """
    if not size_availability:
        return None
    total = len(size_availability)
    in_stock = sum(1 for s in size_availability if s.get("in_stock"))
    return 1.0 - (in_stock / total) if total > 0 else None
```

2. `products` 테이블에 `size_scarcity: Float` 컬럼 추가 (Alembic)

3. 크롤러가 `size_availability` 저장 시 자동 계산 + 기록

4. `GET /api/v2/availability/{key}` 응답에 `size_scarcity` 포함

5. 프론트엔드 — 희소성 높은 제품에 "⚡ 재고 소진 임박" 배지:
```tsx
{item.size_scarcity > 0.7 && (
  <span className="text-xs bg-orange-500 text-white px-2 py-0.5 rounded-full animate-pulse">
    재고 소진 임박
  </span>
)}
```

**완료 기준:**
- `products.size_scarcity` 크롤 후 자동 계산 확인
- 희소성 0.7 이상 제품에 배지 표시 확인

---

## T-132: 역대 최저가 감지 + 배지

**목표:** 현재 가격이 수집 기간 내 최저가이면 "역대 최저가" 배지 표시.

**선행 조건:** T-081 완료 (price_history 존재)

**작업 내용:**

1. `src/fashion_engine/services/product_service.py` — 함수 추가:
```python
async def get_all_time_low(db, product_id: int) -> int | None:
    """price_history에서 해당 제품의 최저 price_krw."""
    result = await db.execute(
        select(func.min(PriceHistory.price)).where(
            PriceHistory.product_id == product_id,
            PriceHistory.price > 0
        )
    )
    return result.scalar()
```

2. `products` 테이블에 `is_all_time_low: Boolean` 컬럼 추가 (Alembic)

3. 크롤 후 `is_all_time_low` 자동 계산:
```python
# 현재 price_krw == 수집 기간 내 최저가 → is_all_time_low = True
```

4. `ProductOut` 스키마에 `is_all_time_low` 추가

5. 프론트엔드 배지:
```tsx
{item.is_all_time_low && (
  <span className="text-xs bg-green-600 text-white px-2 py-0.5 rounded-full font-bold">
    역대 최저
  </span>
)}
```

**완료 기준:**
- 크롤 후 `products.is_all_time_low` 갱신 확인
- 세일 페이지에서 "역대 최저" 배지 표시 확인

---

## T-133: 크롤 커버리지 갭 주간 리포트

**목표:** 매주 자동으로 "수집 중 채널 vs 목표" 갭 분석 → Discord 리포트 전송.

**선행 조건:** T-106 완료

**작업 내용:**

1. `scripts/coverage_report.py` 확장 (기존 파일):
```python
"""
주간 커버리지 리포트:
- 활성 채널 수 / 비활성 채널 수
- 플랫폼별 수집률 (Shopify/WooCommerce/Cafe24/GPT)
- 총 제품 수 / 세일 제품 수 / 세일 비율
- 사이즈 재고 데이터 있는 제품 비율
- 역대 최저가 배지 제품 수
- 지난주 대비 증감
→ Discord #weekly-report 채널 전송
"""
```

2. `config.py`에 `weekly_report_webhook: str | None = None` 추가 (별도 Discord 채널)

3. Railway 스케줄: 매주 월요일 09:00 실행

4. 리포트 형식:
```
📊 주간 커버리지 리포트 (2026-W11)
━━━━━━━━━━━━━━━━━━━━━━━━
채널: 137개 활성 / 29개 비활성 (+2 복구)
제품: 81,234개 (+1,205)
세일: 2,847개 (3.5%) ▲0.8%p
사이즈 재고: 12,456개 (15.3%)
역대 최저: 234개

🔴 수집 실패 채널: 8개 (자동 GPT 전환 예정)
🟢 이번주 복구: END. Clothing, Kith Tokyo
```

**완료 기준:**
- 매주 월요일 Discord #weekly-report 전송 확인
- 지난주 대비 증감 수치 정확성 확인

---

## T-134: 드롭 예측 카운트다운 고도화

**목표:** Shopify `coming-soon` 태그 제품에 예상 출시일 카운트다운 표시.

**선행 조건:** T-079(coming-soon 감지) 완료

**작업 내용:**

1. `products` 테이블에 `expected_drop_at` DateTime 컬럼 추가 (Alembic)

2. Shopify 태그에서 출시일 파싱:
```python
# 태그 예시: "drop-2026-03-15", "launch-friday", "coming-soon-2026-04"
import re, dateutil.parser

DROP_DATE_PATTERNS = [
    r"drop-(\d{4}-\d{2}-\d{2})",
    r"launch-(\d{4}-\d{2}-\d{2})",
    r"coming-soon-(\d{4}-\d{2})",
]

def extract_drop_date(tags: list[str]) -> datetime | None:
    for tag in tags:
        for pattern in DROP_DATE_PATTERNS:
            m = re.search(pattern, tag)
            if m:
                return dateutil.parser.parse(m.group(1))
    return None
```

3. `GET /drops` API에 `expected_drop_at` 포함

4. 프론트엔드 — 드롭 카드에 카운트다운 타이머:
```tsx
const [countdown, setCountdown] = useState("");
useEffect(() => {
  const interval = setInterval(() => {
    const diff = new Date(drop.expected_drop_at).getTime() - Date.now();
    if (diff > 0) {
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff % 86400000) / 3600000);
      setCountdown(`${d}일 ${h}시간 후 드롭`);
    } else {
      setCountdown("출시됨");
    }
  }, 1000);
  return () => clearInterval(interval);
}, [drop.expected_drop_at]);
```

**완료 기준:**
- coming-soon 태그 있는 제품에 `expected_drop_at` 파싱 확인
- 드롭 페이지에서 카운트다운 타이머 동작

---

## T-135: 채널별 가격 경쟁력 분석 (`/admin/channel-compete`)

**목표:** 어떤 채널이 동일 제품에서 가장 싸게 파는지 분석 → 채널 우선순위 결정.

**선행 조건:** T-101 완료 (교차채널 매칭)

**작업 내용:**

1. 분석 쿼리:
```sql
-- 같은 normalized_key 제품에서 채널별 평균 가격 순위
WITH ranked AS (
  SELECT
    p.channel_id,
    p.normalized_key,
    p.price_krw,
    RANK() OVER (PARTITION BY p.normalized_key ORDER BY p.price_krw) as price_rank
  FROM products p
  WHERE p.price_krw IS NOT NULL
    AND p.normalized_key IS NOT NULL
    AND p.is_active = true
)
SELECT
  c.name as channel_name,
  COUNT(*) as matched_products,
  AVG(r.price_rank) as avg_price_rank,          -- 낮을수록 최저가 많음
  SUM(CASE WHEN r.price_rank = 1 THEN 1 ELSE 0 END) as cheapest_count
FROM ranked r
JOIN channels c ON r.channel_id = c.id
GROUP BY c.id, c.name
HAVING COUNT(*) >= 5
ORDER BY cheapest_count DESC;
```

2. `GET /admin/channel-compete` 엔드포인트 추가

3. 프론트엔드 — `/admin/channel-compete` 페이지:
   - 채널별 "최저가 제공 횟수" 랭킹 바차트
   - "평균 가격 순위" 테이블 (1에 가까울수록 저렴)

**완료 기준:**
- `/admin/channel-compete` 에서 채널별 가격 경쟁력 순위 확인
- 동일 제품 5개 이상 겹치는 채널만 분석 대상

---

## Phase 8 — 외부 연동 & 표준화

---

## T-136: OpenAPI 스펙 + 개발자 문서 페이지

**목표:** AI 에이전트 개발자가 API를 쉽게 연동할 수 있는 공개 문서 페이지 (`/api/docs`).

**선행 조건:** T-101, T-102, T-105 완료

**작업 내용:**

1. FastAPI 자동 생성 `/openapi.json` 정제:
```python
# main.py
app = FastAPI(
    title="Fashion Data Engine API",
    description="""
## 패션 브랜드 실시간 데이터 API

AI 에이전트, MCP 클라이언트, 외부 서비스가 패션 데이터에 접근하는 표준 인터페이스.

### 주요 엔드포인트
- `GET /api/v2/availability/{product_key}` — 채널별 재고·가격
- `GET /api/v2/search` — 자연어 제품 검색
- `GET /mcp` — MCP 서버 (SSE)
    """,
    version="2.0.0",
    contact={"name": "Fashion Data Engine", "url": "https://..."},
)
```

2. 커스텀 Swagger UI 스타일링 (`/docs` → 블랙 테마):
```python
from fastapi.openapi.docs import get_swagger_ui_html

@app.get("/api/docs", include_in_schema=False)
async def custom_swagger():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Fashion Data Engine API",
        swagger_css_url="/static/swagger-dark.css",
    )
```

3. MCP 연동 가이드 정적 페이지 (`frontend/src/app/developers/page.tsx`):
   - MCP 설정 코드 블록 복사 버튼
   - API 키 발급 링크
   - cURL 예시

4. `robots.txt` 업데이트 — API 문서 크롤러 허용

**완료 기준:**
- `/api/docs` 에서 블랙 테마 Swagger UI 표시
- `/developers` 페이지에서 MCP 연동 가이드 확인
- openapi.json 다운로드 가능

---

## T-137: Webhook 아웃바운드 — 세일 시작 외부 알림

**목표:** 구독된 브랜드 세일 시작 시 외부 URL로 POST 요청 발송 (Zapier, n8n 연동용).

**선행 조건:** T-083(activity_feed), T-085(WatchAgent) 완료

**작업 내용:**

1. `webhook_subscriptions` 테이블 신규:
```python
class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"
    id         = Column(Integer, primary_key=True)
    url        = Column(String(2000), nullable=False)
    secret     = Column(String(100), nullable=False)    # HMAC 서명용
    brand_ids  = Column(JSONB, nullable=True)           # NULL = 모든 브랜드
    event_types = Column(JSONB, nullable=False)         # ["sale_start", "new_drop"]
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

2. Webhook 관리 API:
```python
POST   /webhooks/subscriptions   # 구독 등록
DELETE /webhooks/subscriptions/{id}  # 구독 취소
GET    /webhooks/subscriptions   # 목록 (인증 필요)
```

3. `scripts/watch_agent.py` — 이벤트 발생 시 구독자에게 발송:
```python
import httpx, hmac, hashlib, json

async def dispatch_webhooks(event: dict):
    payload = json.dumps(event)
    async with httpx.AsyncClient() as client:
        for sub in active_subscriptions:
            if event["event_type"] not in sub.event_types:
                continue
            sig = hmac.new(sub.secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
            await client.post(sub.url, content=payload, headers={
                "Content-Type": "application/json",
                "X-Fashion-Signature": f"sha256={sig}",
            }, timeout=5.0)
```

**완료 기준:**
- Webhook 등록 후 세일 감지 시 외부 URL POST 확인 (requestbin.com 등으로 테스트)
- HMAC 서명 검증 로직 확인

---

## T-138: Google 쇼핑 피드 (Product Feed XML/RSS)

**목표:** Google Merchant Center에 제출 가능한 쇼핑 피드 생성 — SEO + 트래픽 유입.

**선행 조건:** T-103(ProductOut 확장) 완료

**작업 내용:**

1. `GET /feed/google-shopping` 엔드포인트:
```python
from fastapi.responses import Response

@router.get("/feed/google-shopping", response_class=Response)
async def google_shopping_feed(db=Depends(get_db)):
    """Google Merchant Center 호환 XML 피드."""
    products = await product_service.get_sale_products(db, limit=1000)

    xml_items = []
    for p in products:
        xml_items.append(f"""
        <item>
          <g:id>{p.id}</g:id>
          <title>{p.name}</title>
          <g:price>{p.price_krw} KRW</g:price>
          <g:sale_price>{p.price_krw} KRW</g:sale_price>
          <link>{p.url}</link>
          <g:image_link>{p.image_url or ''}</g:image_link>
          <g:availability>{'in stock' if p.is_active else 'out of stock'}</g:availability>
          <g:brand>{p.brand or ''}</g:brand>
          <g:condition>new</g:condition>
        </item>""")

    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
  <channel>
    <title>Fashion Data Engine — Sale Products</title>
    <link>https://fashion-data-engine.vercel.app</link>
    {''.join(xml_items)}
  </channel>
</rss>"""

    return Response(content=feed, media_type="application/xml")
```

2. `robots.txt`에 피드 URL 추가

3. sitemap.xml에 주요 제품 페이지 포함:
```python
@router.get("/sitemap.xml")
async def sitemap(db=Depends(get_db)):
    # 상위 브랜드 페이지 + 카탈로그 페이지 URL 생성
```

**완료 기준:**
- `/feed/google-shopping` 에서 유효한 XML 반환
- Google Rich Results Test에서 구조화 데이터 확인

---

## T-139: 데이터 bulk export API (CSV/JSON)

**목표:** 파트너사나 연구자가 전체 데이터를 CSV/JSON으로 다운로드 가능하게.

**선행 조건:** T-117(API 키 인증) 완료

**작업 내용:**

1. `GET /api/v2/export/products` (API 키 필요):
```python
@router.get("/export/products")
async def export_products(
    format: Literal["csv", "json"] = "json",
    brand_slug: str | None = None,
    is_sale: bool | None = None,
    api_key: str = Depends(verify_api_key),
    db=Depends(get_db),
):
    products = await product_service.get_all_for_export(db, brand_slug=brand_slug, is_sale=is_sale)

    if format == "csv":
        import csv, io
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["id", "name", "brand", "channel", "price_krw", "url", "is_sale", "stock_status"])
        writer.writeheader()
        writer.writerows([p.dict() for p in products])
        return Response(buf.getvalue(), media_type="text/csv",
                       headers={"Content-Disposition": "attachment; filename=products.csv"})
    return products
```

2. 스트리밍 응답 (대용량 대비):
```python
from fastapi.responses import StreamingResponse

async def generate_json_lines():
    async for product in product_service.stream_products(db, ...):
        yield json.dumps(product.dict()) + "\n"

return StreamingResponse(generate_json_lines(), media_type="application/x-ndjson")
```

3. 레이트 리밋: API 키당 1시간 1회

**완료 기준:**
- API 키 없이 요청 시 401
- `?format=csv` 로 CSV 다운로드 확인
- 10만 건 export 시 메모리 OOM 없음 (스트리밍)

---

## T-140: 멀티테넌트 API 키 관리 시스템

**목표:** API 키 발급·관리·rate limit 티어를 체계화해 유료 플랜 기반 마련.

**선행 조건:** T-117 완료

**작업 내용:**

1. `api_keys` 테이블 신규:
```python
class ApiKey(Base):
    __tablename__ = "api_keys"
    id          = Column(Integer, primary_key=True)
    key_hash    = Column(String(64), unique=True, nullable=False)  # SHA-256 hash
    name        = Column(String(100))
    tier        = Column(String(20), default="free")  # "free" | "pro" | "enterprise"
    rpm_limit   = Column(Integer, default=60)          # 분당 요청 수
    daily_limit = Column(Integer, default=1000)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
```

2. 티어별 제한:
```python
TIER_LIMITS = {
    "free": {"rpm": 10, "daily": 100, "endpoints": ["search", "availability"]},
    "pro": {"rpm": 60, "daily": 10000, "endpoints": ["*"]},
    "enterprise": {"rpm": 300, "daily": 100000, "endpoints": ["*", "export"]},
}
```

3. 관리자 API 키 발급:
```python
POST /admin/api-keys  # { name, tier } → { key, key_id }
# key는 발급 시 1회만 평문 표시, 이후는 hash만 저장
```

4. `GET /admin/api-keys` — 사용 통계 포함:
```python
# { key_id, name, tier, rpm_limit, last_used_at, monthly_requests }
```

5. 미들웨어에서 tier별 제한 적용 (T-117 rate limit 확장)

**완료 기준:**
- API 키 발급 → 해당 키로 API 호출 성공
- 티어 초과 시 429 + `Retry-After` 헤더 반환
- 무효 키 시 401 반환

---

## 구현 순서 요약 (T-106~T-140)

```
Phase 3 (데이터 품질) — 병렬 가능:
  T-107 (WooC/Cafe24 세일 수정)       ← 즉시, 독립
  T-108 (교차채널 매칭 개선)           ← 즉시, 독립
  T-109 (이미지 URL 검증)             ← 즉시, 독립
  T-110 (Shopify 카탈로그 강화)        ← 즉시, 독립
  T-106 (yield 모니터링)              ← 독립
  T-111 (채널 자동 재활성화)           ← T-106 선행

Phase 4 (AI 레이어):
  T-113 (브랜드 세일 패턴 API)         ← T-101 선행
  T-114 (Redis 캐싱)                  ← T-101~T-102 선행
  T-115 (WebSocket 피드)              ← T-083 선행
  T-116 (교차채널 가격 추이)           ← T-101 선행
  T-112 (pgvector 의미 검색)          ← T-102 선행, 최후순위
  T-117 (MCP 고도화)                  ← T-105, T-113 선행

Phase 5 (프론트엔드):
  T-122 (OG 메타태그)                 ← 즉시, 독립
  T-121 (모바일/PWA)                  ← 즉시, 독립
  T-118 (홈페이지 재설계)             ← T-102 선행
  T-119 (제품 상세 페이지)            ← T-101, T-103 선행
  T-120 (브랜드 페이지)               ← T-113 선행
  T-123 (ISR 전환)                    ← T-119, T-120 선행

Phase 6 (운영):
  T-128 (데이터 신선도)               ← 즉시, 독립
  T-129 (Sentry)                      ← 즉시, 독립
  T-124 (채널 건강 대시보드)          ← T-106 선행
  T-125 (LLM 비용 추적)              ← T-106 선행
  T-126 (API 응답시간)                ← 독립
  T-127 (DB 백업)                     ← 독립

Phase 7 (BI):
  T-131 (사이즈 희소성)               ← T-101 선행
  T-132 (역대 최저가)                 ← T-081 선행
  T-130 (세일 시즌성)                 ← T-113 선행
  T-134 (드롭 카운트다운)             ← T-079 선행
  T-133 (커버리지 갭 리포트)          ← T-106 선행
  T-135 (채널 경쟁력 분석)            ← T-101 선행

Phase 8 (표준화):
  T-136 (API 문서)                    ← T-101~T-105 선행
  T-137 (Webhook 아웃바운드)          ← T-083, T-085 선행
  T-138 (Google 쇼핑 피드)           ← T-103 선행
  T-139 (bulk export)                 ← T-117 선행
  T-140 (API 키 관리)                 ← T-117 선행
```

---

## 리뷰 포인트 체크리스트

> Codex가 구현한 각 PR을 머지 전에 검토할 항목.

### 🔴 보안 리뷰 (반드시 확인)

```
[ ] API 키는 평문 저장 금지 — SHA-256 hash만 DB에 저장 (T-140)
[ ] Webhook HMAC 검증 우회 불가 — X-Fashion-Signature 검증 로직 테스트 (T-137)
[ ] SQL Injection: text() 쿼리에 f-string 직접 삽입 금지, :param 바인딩 사용 (모든 analytics 쿼리)
[ ] CORS 설정: /api/v2/* 엔드포인트 와일드카드 허용 여부 확인
[ ] rate limit 우회 불가: IP + API 키 복합 체크, X-Forwarded-For 신뢰 설정
[ ] 관리자 엔드포인트 (/admin/*): ADMIN_BEARER_TOKEN 없으면 401
[ ] Sentry에 개인정보(이메일, 결제정보) 전송 금지 (T-129)
[ ] Export API (T-139): 스트리밍 중 연결 끊겨도 DB cursor 정상 종료 확인
```

### 🟡 데이터 무결성 리뷰

```
[ ] Alembic 마이그레이션: down_revision이 현재 head인지 확인
    (cat alembic/versions/*.py | grep down_revision | sort)
[ ] nullable 컬럼 추가 시 기존 레코드에 영향 없는지 확인
[ ] price_krw = 0 또는 음수 허용 금지 — CHECK constraint 또는 application 레벨 검증
[ ] size_availability JSONB 형식: [{"size": str, "in_stock": bool}] 외 다른 형식 거부
[ ] normalized_key 중복 INSERT 방지: ON CONFLICT DO UPDATE 사용 확인
[ ] is_all_time_low 계산: price_history 0건인 제품은 NULL (False 아님)
[ ] 환율 적용 결과 sanity check: price_krw가 원래 currency 대비 ±50% 이내인지
```

### 🟡 성능 리뷰

```
[ ] N+1 쿼리 금지: JOIN 또는 selectinload 사용 확인
    (SQL logging 켜서 요청당 쿼리 수 확인: echo=True)
[ ] JSONB 쿼리 (size_availability @> ...): GIN 인덱스 있는지 확인
[ ] pgvector 검색 (T-112): ivfflat 인덱스 없으면 seq scan — 확인 필수
[ ] 스트리밍 export (T-139): asyncio.sleep(0) yield로 event loop blocking 방지
[ ] WebSocket broadcast (T-115): active 연결 수 무제한 허용 금지 — max 100 cap
[ ] Redis 없을 때 graceful fallback: 캐시 미스 시 DB 직접 쿼리 (T-114)
[ ] ISR revalidate 값: 재고 정보는 max 300초, 가격 정보는 max 600초
```

### 🟢 API 설계 리뷰

```
[ ] v2 엔드포인트: /api/v2/* 프리픽스 일관성 (v1 엔드포인트 /products/* 와 혼용 금지)
[ ] 응답 스키마 null 처리: Optional 필드는 null 허용, 빈 리스트([]) vs null 구분
[ ] 페이지네이션: limit/offset 파라미터 + total_count 응답 포함
[ ] 에러 응답 형식 통일: { "detail": "에러 메시지" } (FastAPI 기본)
[ ] MCP tool docstring: AI가 읽는 도구 설명 — 영문 + 명확한 파라미터 설명 필수
[ ] 브랜드 slug: 소문자 하이픈 형식 일관성 ("palace", "a-p-c", "new-balance")
[ ] product_key 형식: "brand-slug:handle" — 콜론(:) 구분자 일관성
```

### 🟢 프론트엔드 리뷰

```
[ ] next build 오류 없음 (TypeScript 타입 에러 포함)
[ ] 로딩 상태: Suspense 또는 skeleton UI — 빈 화면 없음
[ ] 에러 상태: API 실패 시 에러 메시지 표시 (빈 화면/무한 로딩 금지)
[ ] 무한 스크롤: Intersection Observer 사용, scroll event listener 금지
[ ] WebSocket 재연결: 연결 끊겼을 때 exponential backoff로 재시도
[ ] OG 이미지: next/og 이미지에 한국어 폰트 로드 (Noto Sans KR) 확인
[ ] ISR 페이지: generateStaticParams 반환 목록이 너무 많으면 빌드 시간 증가 — 상위 N개만
[ ] 다크모드: Tailwind dark: 클래스 사용 시 시스템 설정과 동기화
```

### 🔵 운영 & 비용 리뷰

```
[ ] LLM 호출: 채널 크롤 시 불필요한 GPT fallback 호출 최소화 (Shopify/WC 먼저)
[ ] Groq rate limit: 분당 30req 제한 — 병렬 채널 크롤 시 throttle 필요
[ ] Redis TTL 설정: 너무 짧으면 캐시 효과 없음, 너무 길면 staleness — 엔드포인트별 적절한 TTL
[ ] DB 백업 (T-127): 백업 파일 크기 모니터링 — 너무 크면 S3 비용 증가
[ ] WebSocket 연결 수: Railway 서버 메모리 제한 (512MB 무료) 내에서 동작하는지 확인
[ ] Sentry rate: 무료 플랜 5K/월 초과 않도록 sample_rate 조정
[ ] weekly report (T-133): Discord API rate limit — 메시지 길이 2000자 제한
[ ] Google Shopping Feed (T-138): 상품 수 1000개 제한 — 페이지네이션 또는 split feed 고려
```

### 🔵 테스트 & 검증

```
각 태스크 완료 기준을 PR 설명에 실제 실행 결과 스크린샷/로그와 함께 첨부.

T-106: SELECT channel_id, COUNT(*) FROM channel_crawl_stats GROUP BY 1 LIMIT 10;
T-107: SELECT platform, COUNT(*) FILTER (WHERE is_sale) FROM products JOIN channels ON ... GROUP BY 1;
T-108: SELECT COUNT(*) FROM product_catalog WHERE channel_count >= 2;
T-112: SELECT COUNT(*) FROM products WHERE name_embedding IS NOT NULL;
T-113: curl /api/v2/brands/palace/sale-intel | jq '.current_sale_products'
T-114: 동일 쿼리 2회 실행 — 2번째 응답시간 < 50ms
T-117: MCP Inspector에서 5개 tool 호출 성공 스크린샷
T-119: /product/{key} 페이지 스크린샷 (모바일 + 데스크탑)
T-129: Sentry 대시보드 캡처 스크린샷
T-132: SELECT COUNT(*) FROM products WHERE is_all_time_low = true;
T-137: requestbin.com 수신 내역 스크린샷
T-140: 티어별 rate limit 초과 시 429 응답 curl 로그
```
