# CRAWL_RATE_LIMIT_FIX_01: Shopify IP rate-limit 대응 + 크롤 성공률 개선

**Task ID**: T-20260302-064
**Owner**: codex-dev
**Priority**: P1
**Labels**: backend, crawler, reliability, performance

---

## 배경

CrawlRun #2 (157채널) 분석 결과:

| 구분 | 채널 수 | 원인 |
|------|---------|------|
| 성공 | 15개 | Shopify API 정상 수집 |
| 실패 (Shopify rate-limit) | **62개** | concurrency=5 → IP 단위 429 발생 |
| 실패 (NULL platform) | 73개 | Shopify/Cafe24/WooCommerce 미해당 |
| timeout | 3개 | THEXSHOP, Harrods, 8DIVISION |
| 로그 누락 | **5채널** | exception이 CrawlChannelLog 작성 전 bubble up |

**핵심 증거**:
- `032c` 전체 크롤 중 → `0개` 실패 (HTTP 429)
- `032c` 단독 크롤 → `240개` 성공
- `Cole Buxton`, `Slam Jam`, `Goodhood` 등 실제로 제품이 있는 유명 Shopify 스토어들이 동일 패턴으로 실패

**근본 원인**:

Shopify는 단일 IP에서 짧은 시간 내 다수의 Shopify 스토어에 `/products.json?limit=250` 동시 요청 시 **IP 단위 rate-limit**을 적용한다. `concurrency=5`로 5개 채널이 병렬 요청하면:
1. 각 채널이 `/products.json?limit=250&page=1` 를 동시에 요청
2. Shopify CDN이 동일 IP에서 짧은 시간 내 다수 스토어 bulk 요청 감지
3. HTTP 429 반환 → tenacity 3회 재시도 후 포기 → `products=[]` → `not_supported`

---

## 리서치 항목 (웹서치 필수)

Codex는 구현 전 다음을 웹서치로 조사하여 구현 전략을 결정할 것:

### 1. Shopify rate limit 정책
```
검색어: "Shopify products.json rate limit per IP" "Shopify API rate limiting 2024"
         "site:community.shopify.com products.json 429"
         "shopify public api rate limit requests per minute"
```
- Shopify 공개 API (`/products.json`)는 IP 단위로 몇 req/min 허용?
- `Retry-After` 헤더 보장 여부
- 동일 IP에서 다수 스토어 접근 시 공유 rate-limit 풀이 있는지

### 2. asyncio token-bucket rate limiter
```
검색어: "asyncio token bucket rate limiter python 2024"
         "aiohttp rate limiting across multiple requests python"
         "asyncio global rate limit semaphore"
```
- 초당 N 요청으로 제한하는 asyncio 호환 token-bucket 구현
- 기존 라이브러리 (aiolimiter, ratelimit) 검토

### 3. httpx session 최적화
```
검색어: "httpx AsyncClient connection pooling keep-alive"
         "httpx AsyncClient session reuse multiple requests"
```
- httpx 연결 재사용으로 TLS 핸드셰이크 오버헤드 감소
- Shopify 관련 헤더 최적화

### 4. Shopify Storefront API 가능성
```
검색어: "Shopify Storefront API public token products list no auth"
         "shopify storefront api rate limits vs rest api"
```
- Storefront API로 인증 없이 제품 목록 수집 가능한지
- rate limit이 공개 REST API보다 관대한지

---

## 요구사항

### 변경 파일 1: `src/fashion_engine/crawler/product_crawler.py`

#### 수정 1: 전역 Shopify 요청 throttle

```python
# 모듈 레벨 전역 rate limiter
# 구현 방식 선택 (리서치 후 결정):
# Option A: asyncio.Semaphore 기반 (동시 요청 수 제한)
_SHOPIFY_GLOBAL_SEM: asyncio.Semaphore | None = None

def _get_shopify_sem() -> asyncio.Semaphore:
    global _SHOPIFY_GLOBAL_SEM
    if _SHOPIFY_GLOBAL_SEM is None:
        _SHOPIFY_GLOBAL_SEM = asyncio.Semaphore(2)  # 동시 Shopify 요청 최대 2개
    return _SHOPIFY_GLOBAL_SEM

# Option B: token-bucket (초당 N 요청 제한) — 리서치 후 선택
```

`_try_shopify_products()` 내에서 각 페이지 요청 시 전역 semaphore 획득:
```python
async def _try_shopify_products(self, channel_url: str, currency: str) -> list[ProductInfo]:
    ...
    for page in range(1, SHOPIFY_MAX_PAGES + 1):
        url = f"{base}/products.json?limit=100&page={page}"  # 250→100
        try:
            async with _get_shopify_sem():  # ← 전역 throttle
                resp = await self._fetch_with_retry(url)
                data = resp.json()
        except Exception:
            break
        ...
```

#### 수정 2: Shopify 요청 헤더 강화

현재 `_fetch_with_retry()`에서 User-Agent만 설정. 브라우저처럼 보이는 헤더 추가:

```python
# 기존 (라인 194)
headers = {"User-Agent": random.choice(USER_AGENTS)}

# 개선
_BROWSER_HEADERS = {
    "Accept": "application/json, text/html, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

async def _fetch_with_retry(self, url: str, timeout: float | None = None) -> httpx.Response:
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        **_BROWSER_HEADERS,
    }
    ...
```

#### 수정 3: Shopify limit 250 → 100

```python
# 기존 (라인 301)
url = f"{base}/products.json?limit=250&page={page}"

# 변경
url = f"{base}/products.json?limit=100&page={page}"

# SHOPIFY_MAX_PAGES도 조정 (limit=100 기준 최대 4000개 = 40페이지)
SHOPIFY_MAX_PAGES = 40  # 기존 16 → 40 (같은 총량 커버)
```

#### 수정 4: 채널 시작 stagger delay

`crawl_channel()` 진입 시 채널 ID 기반 랜덤 지연으로 동시 요청 분산:

```python
async def crawl_channel(
    self,
    channel_url: str,
    country: str | None = None,
    cafe24_brand_categories: list[tuple[str, str]] | None = None,
) -> ChannelProductResult:
    # stagger delay: 동시 시작 분산 (0~3초 랜덤)
    await asyncio.sleep(random.uniform(0, 3))

    currency = self._infer_currency(channel_url, country)
    ...
```

---

### 변경 파일 2: `scripts/crawl_products.py`

#### 수정 5: concurrency 기본값 변경

```python
# 기존 (라인 303-305)
concurrency: int = typer.Option(
    5, help="동시 처리 채널 수 (기본 5, Shopify API 기준 안전한 상한)"
)

# 변경
concurrency: int = typer.Option(
    2, help="동시 처리 채널 수 (기본 2, Shopify rate-limit 방지)"
)
```

#### 수정 6: CrawlChannelLog 예외 보호 (5채널 로그 누락 버그 수정)

현재 `run_lock` 구간에서 예외 발생 시 CrawlChannelLog가 미작성되어 해당 채널이 결과에서 누락됨.

```python
# 현재 (라인 238-275): 예외 발생 시 아무것도 기록 안 됨
async with run_lock:
    async with AsyncSessionLocal() as db:
        db.add(CrawlChannelLog(...))
        ...
        await db.commit()

# 수정: 예외 발생 시 최소한 internal_error 로그 작성
try:
    async with run_lock:
        async with AsyncSessionLocal() as db:
            db.add(CrawlChannelLog(
                run_id=run_id,
                channel_id=channel.id,
                status=log_status,
                ...
            ))
            await db.execute(text("UPDATE crawl_runs SET done_channels=done_channels+1 ..."))
            await db.commit()
except Exception as log_exc:
    logger.error("CrawlChannelLog 기록 실패 [%s]: %s", channel.name, log_exc)
    # 별도 세션으로 최소 실패 로그 재시도
    try:
        async with AsyncSessionLocal() as db2:
            db2.add(CrawlChannelLog(
                run_id=run_id,
                channel_id=channel.id,
                status="failed",
                error_msg=f"Internal log error: {str(log_exc)[:200]}",
                error_type="internal_error",
                duration_ms=duration_ms,
            ))
            await db2.execute(
                text("UPDATE crawl_runs SET done_channels=done_channels+1 WHERE id=:run_id"),
                {"run_id": run_id},
            )
            await db2.commit()
    except Exception:
        logger.critical("CrawlChannelLog 재시도도 실패 [%s]", channel.name)
```

---

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `src/fashion_engine/crawler/product_crawler.py` | 전역 throttle, 헤더 강화, limit=100, stagger delay |
| `scripts/crawl_products.py` | concurrency=2, CrawlChannelLog 예외 보호 |

### 코드 위치 참고

- `_fetch_with_retry()`: 라인 186-202
- `_try_shopify_products()`: 라인 289-322 (limit=250, SHOPIFY_MAX_PAGES)
- `crawl_channel()`: 라인 232-285 (진입점)
- `_crawl_one_channel()`: 라인 82-291 (CrawlChannelLog 기록: 238-275)
- `concurrency` 옵션: 라인 303-305

---

## DoD (완료 기준)

- [ ] concurrency 기본값 5 → 2 변경
- [ ] 전역 Shopify rate throttle 적용 (semaphore 또는 token-bucket)
- [ ] Shopify 요청 헤더 강화 (Accept, Accept-Language, Cache-Control 추가)
- [ ] `limit=250` → `limit=100` 변경, `SHOPIFY_MAX_PAGES` 조정
- [ ] 채널 stagger delay 0~3초 추가
- [ ] CrawlChannelLog 예외 보호 → 5채널 누락 버그 수정
- [ ] CrawlRun #4 실행 시 Shopify 채널 성공 수 ≥ 50개 (목표, Run #2 대비 3배+)

## 검증

```bash
# 전체 크롤 실행 후 결과 비교
uv run python scripts/crawl_products.py --no-alerts --skip-catalog

# CrawlRun 결과 확인
sqlite3 data/fashion.db "
SELECT id, total_channels, done_channels, error_channels,
       ROUND((JULIANDAY(finished_at) - JULIANDAY(started_at)) * 1440, 1) as duration_min
FROM crawl_runs ORDER BY id DESC LIMIT 3;"

# 로그 누락 채널 없는지 확인
sqlite3 data/fashion.db "
SELECT c.name FROM channels c
WHERE c.is_active=1
  AND c.channel_type NOT IN ('secondhand-marketplace', 'non-fashion')
  AND c.id NOT IN (
    SELECT channel_id FROM crawl_channel_logs
    WHERE run_id=(SELECT MAX(id) FROM crawl_runs)
  );"
# 예상: 0개 (누락 없음)

# shopify 채널 성공 수
sqlite3 data/fashion.db "
SELECT c.platform, ccl.status, COUNT(*) as n
FROM crawl_channel_logs ccl
JOIN channels c ON c.id = ccl.channel_id
WHERE ccl.run_id=(SELECT MAX(id) FROM crawl_runs)
GROUP BY c.platform, ccl.status
ORDER BY c.platform, ccl.status;"
```
