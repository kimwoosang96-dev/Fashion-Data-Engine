# CHANNEL_PROBE_01: 제품 0개 채널 자동 진단 스크립트

**Task ID**: T-20260302-056
**Owner**: codex-dev
**Priority**: P1
**Labels**: backend, script, data-quality

---

## 배경

현재 DB에 제품 0개 채널이 78개 존재하며, 이들의 platform이 전부 NULL입니다.
`detect_platforms.py`의 `/shop.json` 방식은 많은 Shopify 스토어가 해당 엔드포인트를 차단하기 때문에 감지 실패율이 높습니다.

보다 신뢰성 있는 방법:
- `/products.json?limit=1` → 200+JSON이면 Shopify
- `/product/list.html?cate_no=1` → 200이면 Cafe24 가능성 높음
- 메인 URL HTTP 상태코드 수집 (도메인 유효성 판단)

**참고 파일**: `AGENTS.md`, `scripts/detect_platforms.py` (기존 구현 참고), `src/fashion_engine/models/channel.py`

---

## 요구사항

### 파일: `scripts/channel_probe.py`

#### 기능 목록
1. DB에서 `product_count = 0` 채널 목록 조회 (또는 `--all` 플래그 시 전체)
2. 각 채널에 대해 비동기 HTTP 탐색:
   - `{url}` 메인 URL → HTTP 상태 코드
   - `{url}/products.json?limit=1` → 200+JSON이면 Shopify
   - `{url}/product/list.html?cate_no=1` → 200이면 Cafe24 후보
3. 결과를 콘솔 + CSV 파일로 출력 (`--output` 플래그, 기본 `reports/channel_probe_{date}.csv`)
4. `--apply` 플래그 시 감지된 platform을 DB에 업데이트

#### CLI 인터페이스

```bash
# 기본: 제품 0개 채널만, dry-run
uv run python scripts/channel_probe.py

# 모든 채널 대상
uv run python scripts/channel_probe.py --all

# DB 업데이트 포함
uv run python scripts/channel_probe.py --apply

# CSV 저장 경로 지정
uv run python scripts/channel_probe.py --output reports/probe_result.csv
```

#### 응답 구조

```python
@dataclass
class ProbeResult:
    channel_id: int
    name: str
    url: str
    http_status: int | None          # 메인 URL 상태코드
    shopify: bool                    # /products.json 200+JSON
    cafe24: bool                     # /product/list.html 200
    platform_detected: str | None   # "shopify" | "cafe24" | None
    note: str                        # 에러 메시지 또는 특이사항
```

#### CSV 출력 형식

```csv
channel_id,name,url,http_status,shopify,cafe24,platform_detected,note
1,"Bodega","https://bdgastore.com",200,True,False,shopify,""
2,"DSM","https://store.doverstreetmarket.com",200,False,False,,custom platform suspected
```

---

### 구현 세부사항

#### httpx 비동기 병렬 처리

```python
import httpx
import asyncio
from asyncio import Semaphore

SEM = Semaphore(10)  # 동시 최대 10개 채널

async def probe_channel(client: httpx.AsyncClient, channel) -> ProbeResult:
    async with SEM:
        # 1. 메인 URL
        # 2. /products.json?limit=1
        # 3. /product/list.html?cate_no=1
        ...
```

#### Shopify 감지 기준

```python
async def _check_shopify(client, base_url) -> bool:
    url = f"{base_url.rstrip('/')}/products.json?limit=1"
    try:
        resp = await client.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            return isinstance(data, dict) and "products" in data
    except Exception:
        pass
    return False
```

#### Cafe24 감지 기준

```python
async def _check_cafe24(client, base_url) -> bool:
    url = f"{base_url.rstrip('/')}/product/list.html?cate_no=1"
    try:
        resp = await client.get(url, timeout=8)
        if resp.status_code == 200:
            # HTML 소스에서 "cafe24" 문자열 확인
            return "cafe24" in resp.text.lower()
    except Exception:
        pass
    return False
```

#### `--apply` 시 DB 업데이트

```python
# 기존 channel_service.update_platform() 재사용
from fashion_engine.services.channel_service import update_platform

if result.platform_detected and apply:
    async with AsyncSessionLocal() as db:
        await update_platform(db, result.channel_id, result.platform_detected)
        await db.commit()
```

---

### 대상 채널 쿼리

```python
# product_count = 0인 채널
from sqlalchemy import select, func, outerjoin
from fashion_engine.models.channel import Channel
from fashion_engine.models.product import Product

stmt = (
    select(Channel.id, Channel.name, Channel.url, Channel.platform)
    .outerjoin(Product, Product.channel_id == Channel.id)
    .where(Channel.is_active == True)
    .group_by(Channel.id)
    .having(func.count(Product.id) == 0)
    .order_by(Channel.name.asc())
)
```

---

## DoD (완료 기준)

- [ ] `scripts/channel_probe.py` 존재
- [ ] `--help` 출력 정상
- [ ] dry-run 실행 시 콘솔에 결과 테이블 출력
- [ ] `--output` 플래그로 CSV 저장
- [ ] `--apply` 시 Shopify/Cafe24 감지 채널 platform DB 업데이트
- [ ] `asyncio.Semaphore(10)` 병렬 처리

## 검증

```bash
# 기본 dry-run (제품 0개 채널)
uv run python scripts/channel_probe.py

# CSV 저장
uv run python scripts/channel_probe.py --output reports/channel_probe_test.csv
cat reports/channel_probe_test.csv | head -20

# apply 모드
uv run python scripts/channel_probe.py --apply

# DB 확인
sqlite3 data/fashion.db "SELECT platform, COUNT(*) FROM channels GROUP BY platform"
```
