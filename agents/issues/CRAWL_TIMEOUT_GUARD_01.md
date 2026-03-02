# CRAWL_TIMEOUT_GUARD_01: 채널별 asyncio timeout으로 deadlock 방지

**Task ID**: T-20260302-061
**Owner**: codex-dev
**Priority**: P1
**Labels**: backend, crawler, reliability, critical

---

## 배경

CrawlRun #1에서 157채널 크롤 중 PID deadlock 발생:
- 154/157 채널 완료 후 Harrods, A.A. Spectrum, Mercari, 슈피겐 4채널에서 멈춤
- CPU time frozen at 8:18.37 (20분 이상)
- 메모리 130MB → 6MB 급감 (asyncio loop 내부 상태 이상)
- PID 강제 종료 후 CrawlRun 수동 finalize 필요

**근본 원인**:

```python
# 현재: scripts/crawl_products.py
result = await crawler.crawl_channel(channel)  # timeout 없음!

# product_crawler.py:
self._client = httpx.AsyncClient(timeout=self._timeout)  # 15.0s
# + tenacity 3회 retry = 최대 ~50s/요청
# 단, asyncio 레벨 timeout 없음 → 이벤트 루프 블록 가능
```

httpx 레벨 timeout은 있으나 asyncio 레벨 채널 전체 timeout이 없어:
1. Cafe24 cate_no가 수백 개인 채널 → 수천 번의 HTTP 요청 → 수 시간 소요 가능
2. 특정 조건(SSL handshake hang 등)에서 asyncio 자체가 block

---

## 요구사항

### 변경 파일 1: `scripts/crawl_products.py`

#### 채널별 asyncio.wait_for 래핑

```python
import asyncio

# 타입별 채널 timeout (초)
CHANNEL_TIMEOUT_SECS: dict[str, int] = {
    "cafe24": 600,    # Cafe24는 카테고리 수백 개 가능
    "shopify": 180,
    "woocommerce": 180,
    "default": 300,
}


async def _crawl_channel_with_timeout(
    crawler: ProductCrawler,
    channel: Channel,
) -> CrawlResult:
    """asyncio timeout을 적용한 채널 크롤 래퍼."""
    platform = channel.platform or "default"
    timeout = CHANNEL_TIMEOUT_SECS.get(platform, CHANNEL_TIMEOUT_SECS["default"])
    try:
        return await asyncio.wait_for(
            crawler.crawl_channel(channel),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.warning(
            f"[crawl] {channel.name} timeout after {timeout}s"
        )
        return CrawlResult(
            channel_id=channel.id,
            products=[],
            error=f"Channel timeout after {timeout}s",
            error_type="timeout",
            crawl_strategy=None,
        )
```

기존 호출부:
```python
# 변경 전
result = await crawler.crawl_channel(channel)

# 변경 후
result = await _crawl_channel_with_timeout(crawler, channel)
```

---

### 변경 파일 2: `src/fashion_engine/crawler/product_crawler.py`

#### httpx.AsyncClient timeout 세분화

```python
# 변경 전
self._client = httpx.AsyncClient(timeout=self._timeout)  # 15.0

# 변경 후 (connect/read 분리)
self._client = httpx.AsyncClient(
    timeout=httpx.Timeout(
        connect=10.0,   # 연결 타임아웃
        read=30.0,      # 응답 읽기 타임아웃 (대형 HTML에 여유)
        write=10.0,
        pool=5.0,
    ),
    ...
)
```

#### Cafe24 카테고리 수 상한

`_discover_cafe24_brand_categories()` 반환값에 상한 추가:

```python
MAX_CAFE24_CATEGORIES = 50   # 카테고리가 너무 많으면 잘라냄

async def _discover_cafe24_brand_categories(self, base_url: str) -> list[int]:
    # ... 기존 로직 ...
    cate_nos = sorted(set(cate_nos))
    if len(cate_nos) > MAX_CAFE24_CATEGORIES:
        logger.warning(
            f"[cafe24] {base_url}: {len(cate_nos)}개 카테고리 감지 "
            f"→ 상위 {MAX_CAFE24_CATEGORIES}개만 크롤"
        )
        cate_nos = cate_nos[:MAX_CAFE24_CATEGORIES]
    return cate_nos
```

---

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `scripts/crawl_products.py` | 채널별 `asyncio.wait_for` 래핑 추가 |
| `src/fashion_engine/crawler/product_crawler.py` | httpx timeout 세분화 + 카테고리 수 상한 |

---

## DoD (완료 기준)

- [ ] `scripts/crawl_products.py`에 `_crawl_channel_with_timeout()` 추가
- [ ] 모든 채널 크롤 호출이 `_crawl_channel_with_timeout()` 경유
- [ ] timeout 초과 시 `error_type="timeout"` CrawlResult 반환
- [ ] `CHANNEL_TIMEOUT_SECS` 타입별 설정 (cafe24=600, shopify=180, default=300)
- [ ] httpx.Timeout 세분화 (`connect=10, read=30`)
- [ ] Cafe24 카테고리 수 상한 50개

## 검증

```bash
# Harrods (또는 다른 느린 채널)에 단독 크롤 시도
# → timeout 내에 graceful 종료 확인
uv run python scripts/crawl_products.py --channel-id <HARRODS_ID>

# 로그에서 timeout 메시지 확인
# "[crawl] Harrods timeout after 300s"

# DB에서 해당 채널 log 확인
sqlite3 data/fashion.db "
SELECT error_type, error_msg FROM crawl_channel_logs
WHERE channel_id=<HARRODS_ID>
ORDER BY created_at DESC LIMIT 3;"
```
