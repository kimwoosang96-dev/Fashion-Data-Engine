# PRICE_CATALOG_AUDIT_01: 가격 오염 데이터 정비 + 재발 방지

**Task ID**: T-20260302-065
**Owner**: codex-dev
**Priority**: P1
**Labels**: backend, data-quality, bug-fix, catalog

---

## 배경

ProductCatalog 가격 비교 페이지에서 **가격 격차 300%+ 제품 다수 발생**.

### 실측 데이터 (현재 DB)

```
product_catalog 가격격차 TOP10:
  new-balance:u2010etb: min=195 KRW / max=332,000 KRW   (170,256%!)
  new-balance:u2010etn: min=136 KRW / max=207,000 KRW   (152,206%)
  nike:iq0641:          min=215 KRW / max=315,000 KRW   (146,512%)
  converse:a12831c:     min=127 KRW / max=172,000 KRW   (135,433%)

이상 저가 price_history 샘플 (KRW < 1000):
  Limited Edt (SG):   price=6 KRW   (정상: ~200 SGD = 228,000 KRW)
  Guerrilla-Group (JP): price=10 KRW (정상: ~10,000 JPY = 92,000 KRW)
  ANNMS Shop (CA):    price=12 KRW   (정상: ~200 CAD = 210,000 KRW)
```

### 근본 원인 분석

**오염 경로**: 초기 크롤 (Phase 3) 시 일부 채널의 `get_rate_to_krw()` 에서 `1.0 fallback` 적용

```python
# src/fashion_engine/services/product_service.py
async def get_rate_to_krw(db: AsyncSession, currency: str) -> float:
    if currency == "KRW":
        return 1.0
    row = ...
    if row:
        return row.rate
    logger.warning("환율 미등록: %s, fallback 1.0 적용", currency)
    return 1.0  # ← BUG: USD 195 → 195 KRW로 저장됨
```

- `exchange_rates` 테이블이 비어있거나 해당 통화가 미등록인 시점에 크롤 발생
- `rate = 1.0` 적용 → USD 195 → 195 KRW 저장 (정상: 195 × 1440 = 280,800 KRW)
- 이 오염 레코드가 `ProductCatalog.min_price_krw`에 반영되어 격차 발생

**현재 상태 확인**:
- `price_history` 전체: 139,452개, 100% `currency='KRW'` (저장 자체는 항상 KRW 환산)
- `exchange_rates` 현재: USD(1440), EUR(1700), GBP(1941), JPY(9.2), SGD(1138) 등 정상 등록
- 이중 환산 없음: `catalog.py` API는 `currency='KRW'` 레코드에 rate=1.0 적용 → 변환 없음

---

## 리서치 항목 (DB 쿼리 분석 필수)

Codex는 구현 전 다음 쿼리를 실행하여 오염 범위를 정확히 파악할 것:

### 1. 오염 레코드 수 및 분포 확인

```sql
-- 채널별 국가 × 최소 합리 가격 기준으로 이상 레코드 카운트
SELECT c.name, c.country, c.url,
       COUNT(*) as total,
       SUM(CASE WHEN ph.price < 1000 THEN 1 ELSE 0 END) as suspicious_low,
       MIN(ph.price) as min_price,
       AVG(ph.price) as avg_price
FROM price_history ph
JOIN products p ON p.id = ph.product_id
JOIN channels c ON c.id = p.channel_id
WHERE ph.currency = 'KRW'
GROUP BY c.id, c.name, c.country, c.url
HAVING suspicious_low > 0
ORDER BY suspicious_low DESC;
```

### 2. 격차 300%+ ProductCatalog 전체 목록

```sql
SELECT normalized_key, listing_count,
       min_price_krw, max_price_krw,
       ROUND(CAST(max_price_krw AS FLOAT) / min_price_krw * 100, 0) as gap_pct
FROM product_catalog
WHERE min_price_krw > 0 AND max_price_krw > 0
  AND max_price_krw > min_price_krw * 3
ORDER BY gap_pct DESC;
```

### 3. 오염 레코드의 정확한 특성

```sql
-- 이상 저가 레코드의 채널 국가 분포
SELECT c.country, COUNT(*) as n, AVG(ph.price) as avg_suspicious_price
FROM price_history ph
JOIN products p ON p.id = ph.product_id
JOIN channels c ON c.id = p.channel_id
WHERE ph.price < 1000 AND ph.currency = 'KRW'
  AND c.country != 'KR'  -- KRW 채널 제외 (한국 KRW는 낮을 수 있음)
GROUP BY c.country ORDER BY n DESC;
```

### 4. price_history 모델 is_active 필드 존재 여부 확인

```bash
sqlite3 data/fashion.db "PRAGMA table_info(price_history);"
```

→ `is_active` 없으면 Alembic migration 필요 (오염 레코드 비활성화 방식) 또는 직접 삭제 방식 결정

---

## 요구사항

### Step 1: 감사 스크립트 (신규: `scripts/audit_price_data.py`)

```python
"""
오염된 price_history 레코드 탐지 및 보고 스크립트.

탐지 기준 (채널 국가 기반):
  - country IN ('US','UK','EU','AU','CA','SG','HK') → price_krw < 10,000 이면 의심
  - country = 'JP' → price_krw < 1,000 이면 의심
  - country = 'KR' → price_krw < 100 이면 의심 (KRW 100원 미만은 불가)
  - 또는: 채널 내 중앙값의 1% 미만인 레코드 (통계적 outlier)

출력:
  - 채널별 오염 레코드 수 및 비율
  - 격차 300%+ ProductCatalog 항목 수
  - 정정 예상값 (역산: price / actual_rate = 원본 통화값)
"""
```

인터페이스:
```bash
# 감사만 (기본)
uv run python scripts/audit_price_data.py

# 상세 출력 (채널별 샘플 포함)
uv run python scripts/audit_price_data.py --verbose
```

### Step 2: 정리 스크립트 (신규: `scripts/cleanup_price_data.py`)

```python
"""
오염 price_history 레코드 비활성화 또는 삭제 스크립트.

전략 결정 (Codex가 DB 조사 후 선택):
  Option A: 직접 삭제 (price_history에 is_active 없는 경우)
    → DELETE FROM price_history WHERE id IN (...)
  Option B: 비활성화 (is_active 필드 추가 후)
    → UPDATE price_history SET is_active=0 WHERE id IN (...)

안전장치:
  - dry-run 기본값 (--apply 명시 필요)
  - 삭제/비활성화 대상 수 > 10,000개이면 확인 프롬프트
  - brand-store 채널의 레코드는 더 신중하게 처리 (핵심 데이터)
"""
```

인터페이스:
```bash
# dry-run (기본)
uv run python scripts/cleanup_price_data.py

# 적용
uv run python scripts/cleanup_price_data.py --apply --yes
```

### Step 3: `get_rate_to_krw()` 강화

**파일**: `src/fashion_engine/services/product_service.py`

```python
# 현재 (BUG)
async def get_rate_to_krw(db: AsyncSession, currency: str) -> float:
    ...
    logger.warning("환율 미등록: %s, fallback 1.0 적용", currency)
    return 1.0  # ← 재발 원인

# 수정: 하드코딩 근사치 fallback (1.0 대신)
_FALLBACK_RATES: dict[str, float] = {
    "USD": 1400.0, "EUR": 1680.0, "GBP": 1930.0,
    "JPY": 9.0,   "HKD": 182.0,  "SGD": 1130.0,
    "CNY": 207.0, "AUD": 1020.0, "CAD": 1050.0,
    "TWD": 45.0,  "DKK": 228.0,  "SEK": 159.0,
}

async def get_rate_to_krw(db: AsyncSession, currency: str) -> float | None:
    if currency == "KRW":
        return 1.0
    row = (await db.execute(
        select(ExchangeRate).where(
            ExchangeRate.from_currency == currency,
            ExchangeRate.to_currency == "KRW",
        )
    )).scalar_one_or_none()
    if row:
        return float(row.rate)

    # DB 미등록: 하드코딩 근사치 사용
    fallback = _FALLBACK_RATES.get(currency)
    if fallback:
        logger.warning(
            "환율 DB 미등록: %s → 하드코딩 fallback %.1f 적용 (정확도 낮음)",
            currency, fallback
        )
        return fallback

    # 알 수 없는 통화: None 반환 → 호출부에서 저장 스킵
    logger.error("알 수 없는 통화: %s — 가격 저장 스킵", currency)
    return None
```

**호출부 수정** (`scripts/crawl_products.py`):
```python
rate = await get_rate_to_krw(db, currency)
if rate is None:
    logger.warning("통화 %s 환율 없음 → 채널 %s 제품 가격 저장 스킵", currency, channel.name)
    continue  # 또는 해당 채널 전체 스킵
```

### Step 4: `record_price()` 유효성 검사 추가

**파일**: `src/fashion_engine/services/product_service.py`

```python
async def record_price(
    db: AsyncSession,
    product_id: int,
    info: ProductInfo,
    rate_to_krw: float | None,
) -> PriceHistory | None:
    # rate=None이면 저장 스킵
    if rate_to_krw is None:
        logger.warning("rate=None → 가격 저장 스킵 (product_id=%d)", product_id)
        return None

    price_krw = round(float(info.price) * rate_to_krw)

    # 비현실적 가격 경고 (저장은 진행)
    MIN_KRW = 100          # 100원 미만: 확실히 오류
    MAX_KRW = 50_000_000   # 5천만원 초과: 확실히 오류
    if price_krw < MIN_KRW or price_krw > MAX_KRW:
        logger.warning(
            "비현실적 가격 감지: product_id=%d, price=%s %s (rate=%.2f) → %d KRW",
            product_id, info.price, info.currency, rate_to_krw, price_krw,
        )
        return None  # 이상 가격은 저장하지 않음

    ...
```

### Step 5: ProductCatalog 재빌드

오염 데이터 정리 후 Catalog 재빌드:

```bash
# 1. 오염 데이터 적용
uv run python scripts/cleanup_price_data.py --apply --yes

# 2. Catalog 재빌드 (전체)
uv run python scripts/build_product_catalog.py

# 3. 가격 통계 업데이트
uv run python scripts/update_catalog_prices.py

# 4. 결과 검증
sqlite3 data/fashion.db "
SELECT COUNT(*) FROM product_catalog
WHERE min_price_krw > 0 AND max_price_krw > 0
  AND max_price_krw > min_price_krw * 3;"
# 예상: 0 (격차 300%+ 제거)
```

---

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `src/fashion_engine/services/product_service.py` | `get_rate_to_krw()`, `record_price()` 수정 |
| `scripts/audit_price_data.py` | 신규 — 오염 데이터 탐지 및 보고 |
| `scripts/cleanup_price_data.py` | 신규 — 오염 레코드 정리 |
| `scripts/build_product_catalog.py` | 재빌드 |
| `scripts/update_catalog_prices.py` | 가격 통계 갱신 |

### 코드 위치 참고

- `get_rate_to_krw()`: `product_service.py` 라인 21-36
- `record_price()`: `product_service.py` 라인 114-146
- `crawl_products.py` rate 조회: 라인 157-158
- `record_price()` 호출: 라인 176

---

## DoD (완료 기준)

- [ ] `scripts/audit_price_data.py` — 오염 레코드 수/채널 분포 정확히 보고
- [ ] `get_rate_to_krw()` — 1.0 silent fallback 제거, 하드코딩 근사치 fallback 적용, None 반환 추가
- [ ] `record_price()` — rate=None 시 저장 스킵, 비현실적 가격 저장 거부
- [ ] `scripts/cleanup_price_data.py` — dry-run 기본, --apply 시 오염 레코드 제거
- [ ] ProductCatalog 재빌드 완료
- [ ] `product_catalog`에서 격차 300%+ 항목 **0개** (목표)

## 검증

```bash
# 감사 실행
uv run python scripts/audit_price_data.py

# 정리 dry-run
uv run python scripts/cleanup_price_data.py

# 정리 적용
uv run python scripts/cleanup_price_data.py --apply --yes

# Catalog 재빌드
uv run python scripts/build_product_catalog.py
uv run python scripts/update_catalog_prices.py

# 격차 300%+ 제품 0개 확인
sqlite3 data/fashion.db "
SELECT COUNT(*),
       MIN(min_price_krw) as min_p,
       MAX(max_price_krw) as max_p
FROM product_catalog
WHERE min_price_krw > 0 AND max_price_krw > 0
  AND max_price_krw > min_price_krw * 3;"

# 재발 방지 확인: rate=None 케이스 테스트
uv run python -c "
import asyncio, sys; sys.path.insert(0,'src')
from fashion_engine.database import AsyncSessionLocal, init_db
async def test():
    await init_db()
    from fashion_engine.services.product_service import get_rate_to_krw
    async with AsyncSessionLocal() as db:
        r = await get_rate_to_krw(db, 'UNKNOWN_CURRENCY')
        assert r is None, f'Expected None, got {r}'
        print('PASS: Unknown currency returns None')
        r = await get_rate_to_krw(db, 'USD')
        assert r > 1000, f'Expected USD rate > 1000, got {r}'
        print(f'PASS: USD rate = {r}')
asyncio.run(test())
"
```
