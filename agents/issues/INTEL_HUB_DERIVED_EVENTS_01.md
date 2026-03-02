# T-075 | INTEL_HUB_DERIVED_EVENTS_01

> **목적**: Fashion Intel Hub v1 파생 이벤트 로직 구현
> — sale_start / sold_out / restock / sales_spike 이벤트 감지 + ingest + 운영 대시보드

---

## 배경

PRD v1.0 §8 (ETL 파이프라인) + PRD v1.1 §3 (레이어별 생성 규칙) 기반.

**전제**: T-073(INTEL_HUB_DATA_MODEL_01) 완료.

T-073에서 drops/collabs/news 미러링이 완료됐다. 이 과업에서는:
1. `products`/`price_history`/`product_catalog` 기반 **파생 이벤트 4종** 구현
2. Intel 운영 대시보드 (`/admin` 확장) 추가
3. 스케줄러에 Intel ingest 잡 활성화

**파생 이벤트 4종**:
- `sale_start`: 세일 시작 (is_sale False→True 전환)
- `sold_out`: 품절 (archived_at NULL→NOT NULL)
- `restock`: 재입고 (품절 후 재등장)
- `sales_spike`: 채널/브랜드 단위 세일 급증 (48h 롤링 윈도우 임계치 기반)

---

## 요구사항

### Step 1: `sale_start` 이벤트 생성 (세일 시작)

**소스**: `products` + `price_history` 테이블

**생성 규칙**:
```python
# 크롤러가 upsert_product() 호출 시:
# is_sale이 False → True 로 바뀌는 시점에 intel_event 생성

# products.is_sale = True AND 이전 크롤(가장 최근 price_history)에서 is_sale = False
# ─ 즉, 현재 크롤에서 처음으로 is_sale=True인 경우

# intel_event 필드:
# event_type = "sale_start"
# layer = "sale_start"
# title = f"{brand_name} {product_name} 세일 시작"  (간결하게: max 80자)
# event_time = 현재 크롤 시각
# brand_id = product.brand_id
# channel_id = product.channel_id
# product_id = product.id
# product_key = product.product_key
# geo_country = channel.country
# geo_precision = "country" if geo_country else "global"
# severity 매핑 (discount_rate 기준):
#   >= 50% → "critical"
#   >= 30% → "high"
#   >= 15% → "medium"
#   기타   → "low"
# details_json = {
#   "discount_rate": ...,
#   "price_krw": ...,
#   "original_price_krw": ...,
#   "channel_id": ...
# }
# source_type = "crawler"
# confidence = "high" (내부 데이터 기반)
```

**구현 위치**: `src/fashion_engine/services/intel_service.py`에 `maybe_create_sale_start_event()` 추가.

**호출 위치**: `src/fashion_engine/services/product_service.py`의 `upsert_product()`에서 `sale_just_started=True` 시 호출.

> 참고: `upsert_product()`는 이미 `(product, is_new, sale_just_started)` 튜플을 반환함 (MEMORY.md 기록).

---

### Step 2: `sold_out` 이벤트 생성 (품절)

**소스**: `products.archived_at` 전환 감지

**생성 규칙 (PRD v1.1 §3.5 — 안전한 v1 규칙)**:
```python
# products.archived_at이 NULL → NOT NULL 된 경우에만 sold_out 이벤트 생성
# (일시적 크롤 실패로 인한 오탐 방지)

# intel_event 필드:
# event_type = "sold_out"
# layer = "sold_out"
# title = f"{brand_name} {product_name} 품절"
# severity:
#   listing_count(판매 채널 수) >= 3 → "high"
#   브랜드 tier = "high-end"         → severity 상향
#   기본                              → "medium"
# confidence = "high" (archived_at 기반 확실한 신호)
```

**구현 위치**: `product_service.py`의 `upsert_product()` 또는 `archive_product()`.

---

### Step 3: `restock` 이벤트 생성 (재입고)

**소스**: `products.archived_at`이 NOT NULL → NULL 복구

**생성 규칙 (PRD v1.1 §3.6)**:
```python
# 조건: 이전 상태에서 archived_at이 NOT NULL (품절) 상태였던 제품이
#        이번 크롤에서 다시 active(archived_at=NULL, is_active=True)로 전환될 때

# intel_event 필드:
# event_type = "restock"
# layer = "restock"
# title = f"{brand_name} {product_name} 재입고"
# severity: sold_out 이벤트의 severity 상속 또는 기본 "medium"

# 연동: 기존 sold_out 이벤트(같은 product_key) 의 is_active=False 처리
# ─ "재입고됐으니 품절 이벤트는 종료"
```

---

### Step 4: `sales_spike` 이벤트 생성 (세일 급증)

**소스**: `products`, `price_history`, `product_catalog` 기반 집계

**생성 규칙 (PRD v1.1 §3.4 — 임계치 기반 v1)**:

```python
# 배치 잡으로 채널/브랜드 단위 48h 롤링 윈도우 분석
# ─ scripts/ingest_intel_events.py --job derived_spike 로 실행

# 1. 채널 단위 집계:
#    SELECT channel_id,
#           COUNT(*) FILTER (WHERE is_sale=True) as sale_count_48h,
#           COUNT(*) FILTER (WHERE is_active=True) as active_count,
#           AVG(discount_rate) FILTER (WHERE is_sale=True) as avg_discount_48h
#    FROM products
#    WHERE updated_at >= NOW() - INTERVAL '48 hours'
#    GROUP BY channel_id

# 2. 기준선(baseline): 지난 7일 평균 sale_ratio
# 3. 트리거 조건:
#    sale_count_48h >= 15
#    AND sale_ratio_48h >= baseline_ratio + 0.15 (15%p 이상 급증)
#    OR avg_discount_48h >= baseline_avg_discount + 0.10 (10%p 이상 상승)

# intel_event 필드:
# event_type = "sales_spike"
# layer = "sales_spike"
# title = f"{channel_name} 세일 급증 ({sale_count_48h}개 제품)"
# severity:
#   다수 채널 동시 발생 → "critical"
#   sale_ratio delta >= 30%p → "high"
#   기본 → "medium"
# details_json = {
#   "sale_count_48h": ...,
#   "sale_ratio_48h": ...,
#   "avg_discount_48h": ...,
#   "baseline_sale_ratio": ...,
#   "delta_ratio": ...,
# }
```

---

### Step 5: `intel_service.py` 확장

기존 T-073의 `intel_service.py`에 파생 이벤트 함수 추가:

```python
async def maybe_create_sale_start_event(
    db, product: Product, discount_rate: float | None
) -> IntelEvent | None:
    """upsert_product()에서 sale_just_started=True 시 호출"""

async def maybe_create_sold_out_event(
    db, product: Product
) -> IntelEvent | None:
    """product.archived_at 전환 시 호출"""

async def maybe_create_restock_event(
    db, product: Product
) -> IntelEvent | None:
    """품절 → 재입고 전환 시 호출, 기존 sold_out 이벤트 종료 처리"""

async def ingest_sales_spike(db, run_id: int) -> dict:
    """배치 잡: 채널/브랜드 단위 48h 스파이크 감지"""
```

---

### Step 6: `ingest_intel_events.py` 확장

```bash
# 파생 이벤트 전체 (sold_out은 크롤 중 실시간 생성, spike만 배치)
uv run python scripts/ingest_intel_events.py --job derived_spike

# Makefile 타깃 추가
ingest-intel-spike:
	uv run python scripts/ingest_intel_events.py --job derived_spike
```

---

### Step 7: 스케줄러 Intel ingest 잡 활성화

**파일**: `scripts/scheduler.py`

T-072에서 추가한 주석을 해제하고 실제 잡으로 활성화:

```python
async def run_intel_ingest():
    """Intel Hub ingest: drops/collabs/news 미러링 + sales_spike 파생"""
    proc = await asyncio.create_subprocess_exec(
        "uv", "run", "python", "scripts/ingest_intel_events.py",
        "--job", "drops", "collabs", "news", "derived_spike",
    )
    await proc.wait()

scheduler.add_job(
    run_intel_ingest,
    CronTrigger(hour=7, minute=30),
    id="intel_ingest_0730",
    replace_existing=True,
)
```

환경변수 `INTEL_DERIVED_ENABLED=true`로 활성화 확인.

---

### Step 8: Admin Intel 운영 대시보드

**`GET /admin/intel-status` 엔드포인트** (Bearer 인증):

```json
{
  "total_events": 342,
  "layer_counts": {"drop": 45, "collab": 12, "news": 180, "sale_start": 89, ...},
  "last_ingest": {
    "runs": [
      {"job_name": "news", "started_at": "...", "status": "done",
       "events_created": 12, "error_count": 0}
    ]
  },
  "freshness": {
    "news": {"last_event_at": "...", "status": "fresh"},
    "drop": {"last_event_at": "...", "status": "stale"},
    "sale_start": {"last_event_at": "...", "status": "fresh"}
  }
}
```

**`freshness` 계산**:
- `fresh`: 마지막 이벤트가 24h 이내
- `stale`: 24~72h
- `error`: ingest_run 최근 실행이 failed
- `disabled`: INTEL_*_ENABLED=false

**프론트 `/admin`에 "Intel 운영" 섹션 추가**:
```
레이어별 이벤트 수 | 최근 ingest 실행 현황 | freshness 상태
```

---

### Step 9: Confidence/Severity 계산 유틸리티

**파일**: `src/fashion_engine/services/intel_service.py`에 추가

```python
def calc_confidence_score(
    source_type: str,
    brand_mapped: bool,
    channel_mapped: bool,
    sources_count: int,
    geo_precision: str,
) -> tuple[int, str]:
    """
    PRD v1.1 §7.1 기반 confidence 점수 계산.
    Returns: (score 0-100, label low|medium|high)
    """
    score = 0
    if source_type == "official":   score += 50
    elif source_type == "crawler":  score += 40
    elif source_type == "media":    score += 30
    elif source_type == "social":   score += 20

    if brand_mapped or channel_mapped: score += 10
    if sources_count >= 2:              score += 15
    if geo_precision in ("point", "city"): score += 5

    label = "high" if score >= 80 else "medium" if score >= 50 else "low"
    return score, label
```

---

## DoD

- [ ] `maybe_create_sale_start_event()` 구현 + `upsert_product()` sale_just_started 후크 연결
- [ ] `maybe_create_sold_out_event()` 구현 + `archive_product()` 연결
- [ ] `maybe_create_restock_event()` 구현 + 기존 sold_out 이벤트 is_active=False 처리
- [ ] `ingest_sales_spike()` 배치 잡 구현 (48h 롤링 윈도우)
- [ ] 스케줄러에 `intel_ingest_0730` 잡 활성화
- [ ] `GET /admin/intel-status` API 동작 + freshness 계산
- [ ] Admin 페이지에 Intel 운영 섹션 추가
- [ ] 최초 파생 이벤트 ingest 후 `sale_start` ≥ 10개, `sold_out` 혹은 `restock` ≥ 1개
- [ ] `INTEL_DERIVED_ENABLED=true` 환경변수로 활성/비활성 제어 동작 확인

---

## 검증

```bash
# 파생 이벤트 ingest 테스트
uv run python scripts/ingest_intel_events.py --job derived_spike

# 파생 이벤트 수 확인
sqlite3 data/fashion.db "
SELECT event_type, COUNT(*) as n
FROM intel_events
WHERE event_type IN ('sale_start', 'sold_out', 'restock', 'sales_spike')
GROUP BY event_type;
"

# 스케줄러 dry-run (Intel 잡 포함 확인)
uv run python scripts/scheduler.py --dry-run

# Admin API
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/admin/intel-status | python3 -m json.tool
```

---

## 참고

- PRD v1.0: `docs/FASHION_INTEL_HUB_PRD_2026-03-02.md` §8 (파이프라인)
- PRD v1.1 리뷰: `docs/fashion_intel_prd_review_v1_1_2026-03-02.md` §3 (생성 규칙), §7 (scoring)
- 기존 sale_just_started 로직: `src/fashion_engine/services/product_service.py`
- 전제: T-073 완료
