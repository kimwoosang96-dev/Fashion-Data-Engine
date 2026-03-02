# T-076 | INTEL_HUB_DERIVED_EVENTS_FIX_01

> **목적**: T-075 파생 이벤트 구현 후 검토에서 발견된 3가지 미구현 항목 보완
> — sales_spike 임계치 강화 + sale_start severity 정교화 + geo_precision/confidence 유틸 추가

---

## 배경 (리뷰 결과 기반)

T-075(INTEL_HUB_DERIVED_EVENTS_01) Codex 구현 완료 후 코드 리뷰 결과:

**이미 정상 구현된 항목** ✅
- `upsert_derived_product_event()` — intel_service.py 구현 완료
- `sale_start` 훅 — `crawl_products.py` L206~221에 연결됨
- `sold_out` / `restock` 훅 — `crawl_products.py` L222~240에 연결됨
- 스케줄러 `intel_ingest_0730` 잡 활성화됨
- `GET /admin/intel-status` API 동작 중

**미구현/미달 항목** ❌ ← 이 과업의 범위
1. `sales_spike` 임계치 단순 (>= 5) — PRD 기준 미달
2. `sale_start` severity: discount_rate 기반이 아닌 flat "high" 고정
3. `upsert_derived_product_event()`: geo_precision 미설정 (default="global")
4. `calc_confidence_score()` 유틸리티 미구현 (PRD v1.1 §7.1)

---

## 요구사항

### Step 1: `_pick_sales_spike_candidates()` 임계치 강화

**파일**: `scripts/ingest_intel_events.py`

**현재 코드** (L263~279):
```python
.having(func.count(Product.id) >= 5)  # 단순 카운트
```

**PRD v1.1 §3.4 기준**:
- `sale_count_48h >= 15` (AND)
- `sale_ratio_48h >= baseline_ratio + 0.15` (7d 기준선 대비 15%p 급증) (OR)
- `avg_discount_48h >= baseline_avg_discount + 0.10`

**구현**:

```python
async def _pick_sales_spike_candidates(
    db: AsyncSession, window_hours: int
) -> list[tuple[int, int, float, float]]:
    """
    (brand_id, sale_count, sale_ratio_48h, avg_discount_48h) 반환.
    조건: sale_count >= 15 AND (sale_ratio_delta >= 0.15 OR discount_delta >= 0.10)
    """
    since_window = utcnow() - timedelta(hours=window_hours)
    since_baseline = utcnow() - timedelta(days=7)

    # 1. 48h 윈도우 집계
    window_rows = (
        await db.execute(
            select(
                Product.brand_id,
                func.count(Product.id).label("total_count"),
                func.sum(func.cast(Product.is_sale, Integer)).label("sale_count"),
                func.avg(
                    case((Product.is_sale == True, Product.discount_rate), else_=None)
                ).label("avg_discount"),
            )
            .where(
                Product.brand_id.is_not(None),
                Product.is_active == True,
                Product.updated_at >= since_window,
            )
            .group_by(Product.brand_id)
            .having(func.sum(func.cast(Product.is_sale, Integer)) >= 15)
        )
    ).all()

    if not window_rows:
        return []

    # 2. 7d 기준선 집계 (같은 brand_id 목록)
    brand_ids = [r.brand_id for r in window_rows]
    baseline_rows = (
        await db.execute(
            select(
                Product.brand_id,
                func.count(Product.id).label("total_count"),
                func.sum(func.cast(Product.is_sale, Integer)).label("sale_count"),
                func.avg(
                    case((Product.is_sale == True, Product.discount_rate), else_=None)
                ).label("avg_discount"),
            )
            .where(
                Product.brand_id.in_(brand_ids),
                Product.is_active == True,
                Product.updated_at >= since_baseline,
            )
            .group_by(Product.brand_id)
        )
    ).all()
    baseline_map = {
        r.brand_id: (
            (r.sale_count or 0) / max(r.total_count or 1, 1),
            float(r.avg_discount or 0.0),
        )
        for r in baseline_rows
    }

    # 3. delta 조건 필터링
    results = []
    for r in window_rows:
        ratio_48h = (r.sale_count or 0) / max(r.total_count or 1, 1)
        discount_48h = float(r.avg_discount or 0.0)
        base_ratio, base_discount = baseline_map.get(r.brand_id, (0.0, 0.0))
        ratio_delta = ratio_48h - base_ratio
        discount_delta = discount_48h - base_discount

        if ratio_delta >= 0.15 or discount_delta >= 0.10:
            results.append((int(r.brand_id), int(r.sale_count), ratio_48h, discount_48h))

    return results
```

`_ingest_derived_spike()` 호출부도 시그니처 변경에 맞게 수정:
```python
for brand_id, sale_count, sale_ratio, avg_discount in await _pick_sales_spike_candidates(db, window_hours):
    ...
    severity = "critical" if sale_ratio >= 0.4 else "high" if sale_ratio >= 0.25 else "medium"
    details = {
        "window_hours": window_hours,
        "sale_count": sale_count,
        "sale_ratio_48h": round(sale_ratio, 4),
        "avg_discount_48h": round(avg_discount, 4),
    }
```

**SQLAlchemy import 추가 필요**: `from sqlalchemy import Integer, case`

---

### Step 2: `upsert_derived_product_event()` severity 정교화

**파일**: `src/fashion_engine/services/intel_service.py`

**현재 코드** (L352~354):
```python
severity = "medium"
if event_type in {"sale_start", "sold_out"}:
    severity = "high"
```

**개선**: `sale_start` 이벤트는 `details["discount_rate"]`로 severity 결정

```python
def _calc_sale_start_severity(discount_rate: float | None) -> str:
    """PRD v1.1 §3.2 기준: discount_rate (0~1 float 또는 0~100 퍼센트 모두 지원)"""
    if discount_rate is None:
        return "low"
    # 0~1 float이면 100 곱해 퍼센트로 변환
    pct = discount_rate * 100 if discount_rate <= 1.0 else discount_rate
    if pct >= 50:
        return "critical"
    if pct >= 30:
        return "high"
    if pct >= 15:
        return "medium"
    return "low"


# upsert_derived_product_event() 내부 severity 결정 로직 교체:
if event_type == "sale_start":
    severity = _calc_sale_start_severity(details.get("discount_rate") if details else None)
elif event_type == "sold_out":
    severity = "high"
elif event_type == "restock":
    severity = "medium"
else:
    severity = "medium"
```

---

### Step 3: `geo_precision` 설정

**파일**: `src/fashion_engine/services/intel_service.py`

`upsert_derived_product_event()` — `IntelEvent` 생성 시 `geo_precision` 추가:

```python
geo_country = (channel.country or "").upper()[:2] or None
geo_precision = "country" if geo_country else "global"

row = IntelEvent(
    ...
    geo_country=geo_country,
    geo_precision=geo_precision,   # ← 추가 (현재 default="global" 방치됨)
    ...
)
```

---

### Step 4: `calc_confidence_score()` 유틸리티 추가

**파일**: `src/fashion_engine/services/intel_service.py`

PRD v1.1 §7.1 기준으로 confidence 점수 계산 함수 추가:

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
    Returns: (score 0-100, label "low" | "medium" | "high")
    """
    score = 0
    if source_type == "official":
        score += 50
    elif source_type == "crawler":
        score += 40
    elif source_type == "media":
        score += 30
    elif source_type == "social":
        score += 20

    if brand_mapped or channel_mapped:
        score += 10
    if sources_count >= 2:
        score += 15
    if geo_precision in ("point", "city"):
        score += 5

    label = "high" if score >= 80 else "medium" if score >= 50 else "low"
    return score, label
```

파생 이벤트(derived)는 내부 DB 기반이므로 항상 "high" confidence가 적절하지만, 이 함수는 미러링 이벤트(외부 소스 기반) 등에서 재사용 가능.

---

### Step 5: `discount_rate` 전달 확인

**파일**: `scripts/crawl_products.py`

`sale_start` 이벤트 생성 시 `details`에 `discount_rate` 전달:

```python
if sale_just_started:
    discount_rate = None
    if info.compare_at_price and info.price and info.compare_at_price > 0:
        discount_rate = round(1 - info.price / info.compare_at_price, 4)

    await upsert_derived_product_event(
        db,
        event_type="sale_start",
        product=product,
        channel=channel,
        brand=brand_obj,
        title=f"{brand_name} {product.name[:60]} 세일 시작",
        summary=f"할인율 {round(discount_rate * 100)}%" if discount_rate else None,
        source_url=product.url,
        details={
            "discount_rate": discount_rate,
            "price_krw": product.price_krw,
            "original_price_krw": info.compare_at_price * rate if info.compare_at_price and rate else None,
            "channel_id": channel.id,
        },
    )
```

현재 코드에 `discount_rate`가 details에 포함되지 않은 경우 Step 2의 severity 계산이 항상 "low"가 되므로 반드시 전달 필요.

**기존 `crawl_products.py` sale_start 블록 위치**: L206~221

---

## DoD

- [ ] `_pick_sales_spike_candidates()` — 임계치 `>= 15` + 7d baseline delta(15%p/10%p) 조건 추가
- [ ] `_ingest_derived_spike()` — 반환값 시그니처 변경 + severity(critical/high/medium) 정교화
- [ ] `_calc_sale_start_severity()` — discount_rate 기반 severity 헬퍼 함수 추가
- [ ] `upsert_derived_product_event()` — sale_start severity 정교화 적용
- [ ] `upsert_derived_product_event()` — geo_precision 명시적 설정 추가
- [ ] `calc_confidence_score()` — PRD v1.1 §7.1 기반 유틸리티 추가
- [ ] `crawl_products.py` — sale_start details에 discount_rate 전달 확인/보완
- [ ] `uv run python scripts/ingest_intel_events.py --job derived_spike` — 오류 없이 실행

---

## 검증

```bash
# 파생 이벤트 배치 잡 실행
uv run python scripts/ingest_intel_events.py --job derived_spike

# 결과 확인
sqlite3 data/fashion.db "
SELECT event_type, severity, COUNT(*) as n
FROM intel_events
WHERE event_type IN ('sale_start', 'sold_out', 'restock', 'sales_spike')
GROUP BY event_type, severity
ORDER BY event_type, severity;
"

# sale_start severity 분포 확인 (discount_rate별)
sqlite3 data/fashion.db "
SELECT severity, COUNT(*) as n,
       ROUND(AVG(CAST(json_extract(details_json, '$.discount_rate') AS REAL)) * 100, 1) as avg_discount_pct
FROM intel_events
WHERE event_type = 'sale_start'
GROUP BY severity;
"

# geo_precision 설정 확인
sqlite3 data/fashion.db "
SELECT geo_precision, COUNT(*) as n
FROM intel_events
WHERE source_type = 'derived'
GROUP BY geo_precision;
"
```

---

## 참고

- PRD v1.1: `docs/fashion_intel_prd_review_v1_1_2026-03-02.md` §3.4 (sales_spike), §7.1 (scoring)
- 기존 구현 확인:
  - `src/fashion_engine/services/intel_service.py`: `upsert_derived_product_event()` L328~381
  - `scripts/ingest_intel_events.py`: `_pick_sales_spike_candidates()` L263~279
  - `scripts/crawl_products.py`: sale_start/sold_out/restock 훅 L206~240
- 전제: T-073, T-075 완료 (이미 확인됨)
