# T-073 | INTEL_HUB_DATA_MODEL_01

> **목적**: Fashion Intel Hub v1 데이터 모델 + 백엔드 API + 기본 데이터 ingest 구현
> — `intel_events` + `intel_event_sources` + ingest run 로깅, drops/collabs/news 미러링

---

## 배경

PRD v1.0 §7 데이터 모델 + PRD v1.1 §4 보완 기반.

T-072(INTEL_HUB_SPRINT0_01) 완료 후 진행. 스텁 API(`/intel/events` 등)가 이미 존재하며, 이 과업에서 실제 구현으로 교체한다.

**v1 포함 레이어 (DoD 기준)**:
- `drop` — 기존 `drops` 테이블 미러링
- `collab` — 기존 `brand_collaborations` 테이블 미러링
- `news` — 기존 `fashion_news` / RSS 결과 미러링
- `sale_start` — 파생 이벤트 기초 (is_sale 전환, T-075 전에 기본 ingest만)

---

## 요구사항

### Step 1: DB 모델 + Alembic 마이그레이션

#### 1-A. `intel_events` 모델

**파일**: `src/fashion_engine/models/intel_event.py`

```python
class IntelEvent(Base):
    __tablename__ = "intel_events"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 분류
    event_type: Mapped[str]  # drop|collab|sale_start|sales_spike|restock|sold_out|news|brand_post
    layer: Mapped[str]        # UI 토글용 (event_type과 동일하거나 세분화 가능)

    # 시간
    event_time: Mapped[datetime | None]     # 실제 사건 시각
    detected_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(onupdate=func.now(), default=func.now())

    # 주체 (모두 nullable — 최대한 연결, 없어도 허용)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"))
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    product_key: Mapped[str | None]

    # 위치
    geo_country: Mapped[str | None]   # ISO2 (예: KR, JP, US)
    geo_city: Mapped[str | None]
    geo_lat: Mapped[float | None]
    geo_lng: Mapped[float | None]
    geo_precision: Mapped[str] = mapped_column(default="global")  # global|country|city|point

    # 콘텐츠
    title: Mapped[str]
    summary: Mapped[str | None]
    details_json: Mapped[str | None]   # JSON 문자열
    source_url: Mapped[str | None]
    source_domain: Mapped[str | None]
    source_type: Mapped[str | None]    # official|media|social|crawler
    source_published_at: Mapped[datetime | None]

    # 품질/상태
    severity: Mapped[str] = mapped_column(default="medium")   # low|medium|high|critical
    confidence: Mapped[str] = mapped_column(default="medium") # low|medium|high
    dedup_key: Mapped[str | None]  # UNIQUE 인덱스
    is_active: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=False)

    # 감사
    created_by: Mapped[str] = mapped_column(default="system")  # system|admin
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("intel_ingest_runs.id"))
```

**dedup_key 생성 함수**:
```python
def build_dedup_key(event_type, brand_id, channel_id, product_key, event_date) -> str:
    """
    형식: {event_type}:{brand_id|na}:{channel_id|na}:{product_key_hash|na}:{date_bucket}
    date_bucket: YYYY-MM-DD
    """
    import hashlib
    pk_hash = hashlib.md5(product_key.encode()).hexdigest()[:8] if product_key else "na"
    date_bucket = event_date.strftime("%Y-%m-%d") if event_date else "na"
    return f"{event_type}:{brand_id or 'na'}:{channel_id or 'na'}:{pk_hash}:{date_bucket}"
```

#### 1-B. `intel_event_sources` 모델 (PRD v1.1 §4.2 권장안)

```python
class IntelEventSource(Base):
    __tablename__ = "intel_event_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("intel_events.id", ondelete="CASCADE"))
    source_url: Mapped[str]
    source_domain: Mapped[str | None]
    source_type: Mapped[str | None]
    source_published_at: Mapped[datetime | None]
    raw_title: Mapped[str | None]
    raw_summary: Mapped[str | None]
    ingested_at: Mapped[datetime] = mapped_column(default=func.now())

    __table_args__ = (
        UniqueConstraint("event_id", "source_url"),
    )
```

#### 1-C. `intel_ingest_runs` / `intel_ingest_logs` 모델 (PRD v1.1 §4.3)

```python
class IntelIngestRun(Base):
    __tablename__ = "intel_ingest_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_name: Mapped[str]       # news|drops|collabs|derived
    started_at: Mapped[datetime] = mapped_column(default=func.now())
    finished_at: Mapped[datetime | None]
    status: Mapped[str] = mapped_column(default="running")  # running|done|failed
    events_created: Mapped[int] = mapped_column(default=0)
    events_updated: Mapped[int] = mapped_column(default=0)
    sources_ingested: Mapped[int] = mapped_column(default=0)
    dedup_merged: Mapped[int] = mapped_column(default=0)
    error_count: Mapped[int] = mapped_column(default=0)

class IntelIngestLog(Base):
    __tablename__ = "intel_ingest_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("intel_ingest_runs.id"))
    source_type: Mapped[str | None]
    source_url: Mapped[str | None]
    status: Mapped[str]         # success|failed|skipped|dedup
    error_type: Mapped[str | None]  # http_4xx|parse_error|mapping_error|dedup
    duration_ms: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(default=func.now())
```

**Alembic 마이그레이션**:
- 신규 revision: `f1a2b3c4d5e6_add_intel_hub_tables`
- 4개 테이블 + 인덱스:

```python
# 인덱스
op.create_index("idx_intel_events_time", "intel_events", ["event_time", "detected_at"])
op.create_index("idx_intel_events_layer_time", "intel_events", ["layer", "event_time"])
op.create_index("idx_intel_events_brand_time", "intel_events", ["brand_id", "event_time"])
op.create_index("idx_intel_events_channel_time", "intel_events", ["channel_id", "event_time"])
op.create_unique_constraint("uq_intel_events_dedup_key", "intel_events", ["dedup_key"])
```

---

### Step 2: Intel Ingest 서비스

**파일**: `src/fashion_engine/services/intel_service.py`

핵심 함수:
```python
async def upsert_intel_event(db, event_data: dict) -> tuple[IntelEvent, bool]:
    """dedup_key 기준 upsert. (event, is_new) 반환."""

async def ingest_drops(db, run_id: int) -> dict:
    """drops 테이블 → intel_events 미러링."""

async def ingest_collabs(db, run_id: int) -> dict:
    """brand_collaborations → intel_events 미러링."""

async def ingest_news(db, run_id: int) -> dict:
    """fashion_news → intel_events 미러링."""
```

#### 2-A. drops → intel_events 미러링 규칙

```python
# drops.status 변화 또는 신규 drops 항목 → intel_event 생성
# event_type = "drop"
# layer = "drop"
# title = f"{brand_name} {drop.title or 'Drop'}"
# event_time = drop.release_date or drop.detected_at
# brand_id = drop.brand_id
# geo_country = brand.origin_country
# geo_precision = "country" if geo_country else "global"
# severity 매핑:
#   upcoming → "medium"
#   released → "high"
#   sold_out  → "high"
# source_type = "crawler"
# dedup_key = build_dedup_key("drop", brand_id, None, None, event_time)
```

#### 2-B. collabs → intel_events 미러링 규칙

```python
# brand_collaborations → intel_event
# event_type = "collab"
# layer = "collab"
# title = f"{brand1_name} × {brand2_name}"  # 두 브랜드명 조합
# event_time = collab.release_date or collab.created_at
# brand_id = collab.brand1_id (primary)
# severity: hype_score 기반 매핑
#   0–30  → "low"
#   31–60 → "medium"
#   61–80 → "high"
#   81+   → "critical"
# source_type = "crawler"
# dedup_key = build_dedup_key("collab", brand1_id, None, None, event_time)
```

#### 2-C. news → intel_events 미러링 규칙

```python
# fashion_news → intel_event
# event_type = "news"
# layer = "news"
# title = news.title
# summary = news.summary
# source_url = news.url
# source_domain = news.source
# source_published_at = news.published_at
# brand_id = news.brand_id (있으면)
# channel_id = news.channel_id (있으면)
# geo_country = brand.origin_country or channel.country (있으면)
# geo_precision = "country" if geo_country else "global"
# confidence: source에 따라
#   공식 사이트 → "high"
#   주요 미디어(hypebeast, highsnobiety 등) → "medium"
#   기타 → "low"
# dedup_key = build_dedup_key("news", brand_id, channel_id, None, source_published_at)
```

---

### Step 3: Ingest 실행 스크립트

**파일**: `scripts/ingest_intel_events.py`

```python
"""
Intel Hub 이벤트 ingest 스크립트.

실행:
  uv run python scripts/ingest_intel_events.py              # 전체 (drops+collabs+news)
  uv run python scripts/ingest_intel_events.py --job news   # 단일 잡
  uv run python scripts/ingest_intel_events.py --since 7d  # 최근 N일만
"""

import asyncio, argparse
from datetime import datetime, timedelta
from fashion_engine.db import AsyncSessionLocal
from fashion_engine.services.intel_service import ingest_drops, ingest_collabs, ingest_news
from fashion_engine.models.intel_event import IntelIngestRun
# ...

async def main(jobs: list[str], since: datetime | None):
    async with AsyncSessionLocal() as db:
        for job_name in jobs:
            run = IntelIngestRun(job_name=job_name)
            db.add(run)
            await db.flush()
            try:
                if job_name == "drops":
                    result = await ingest_drops(db, run.id)
                elif job_name == "collabs":
                    result = await ingest_collabs(db, run.id)
                elif job_name == "news":
                    result = await ingest_news(db, run.id)
                run.status = "done"
                run.events_created = result["created"]
                run.events_updated = result["updated"]
                run.finished_at = datetime.utcnow()
            except Exception as e:
                run.status = "failed"
                run.error_count += 1
            await db.commit()
            print(f"[{job_name}] created={result.get('created',0)}, updated={result.get('updated',0)}")
```

**Makefile 타깃 추가**:
```makefile
ingest-intel:
	uv run python scripts/ingest_intel_events.py

ingest-intel-news:
	uv run python scripts/ingest_intel_events.py --job news
```

---

### Step 4: FastAPI `/intel/*` API 구현

**파일**: `src/fashion_engine/api/intel.py` (T-072 스텁 → 실제 구현으로 교체)

#### 4-A. `GET /intel/events`

쿼리 파라미터:
- `layers` (comma-separated: `drop,collab,news,sale_start,...`)
- `time_range` (`24h|7d|30d|90d|custom`)
- `start`, `end` (ISO8601, `custom` 시 사용)
- `brand_slug`
- `channel_id`
- `country`
- `q` (제목 검색)
- `min_confidence` (`low|medium|high`)
- `limit` (기본 50, 최대 100)
- `cursor` (cursor pagination: `event_time,id` 형식)

응답:
```json
{
  "events": [...],
  "total": 342,
  "layer_counts": {"drop": 12, "collab": 5, "news": 45, ...},
  "next_cursor": "2026-03-01T12:00:00,123"
}
```

**페이지네이션**: cursor 기반 (`event_time DESC NULLS LAST, detected_at DESC, id DESC`)

#### 4-B. `GET /intel/map-points`

쿼리: `layers`, `time_range`, `start`, `end`, `bbox` (minLng,minLat,maxLng,maxLat)

응답 (최소 필드만):
```json
{
  "points": [
    {"id": 1, "lat": 37.5, "lng": 127.0, "event_type": "drop",
     "severity": "high", "title": "Nike Drop", "geo_precision": "country"}
  ]
}
```

- bbox 필터 적용 (geo_lat/geo_lng BETWEEN bbox 값)
- geo_precision=global 이벤트는 제외 (지도에 표시 불가)

#### 4-C. `GET /intel/timeline`

쿼리: `layers`, `time_range`, `granularity` (`hour|day|week`, 기본 `day`)

응답:
```json
{
  "granularity": "day",
  "buckets": [
    {
      "date": "2026-03-01",
      "total": 15,
      "by_layer": {"drop": 3, "collab": 2, "news": 10}
    }
  ]
}
```

#### 4-D. `GET /intel/highlights`

최근 24~48시간 기준 severity+confidence 가중치 상위 10개:

```
score = (recency 가중치 0.4) + (severity 가중치 0.4) + (confidence 가중치 0.2)
severity 점수: critical=4, high=3, medium=2, low=1
confidence 점수: high=3, medium=2, low=1
recency: exp(-hours_since_event / 24)
```

#### 4-E. `GET /intel/events/{id}`

상세 카드: 연결 제품/브랜드/채널 정보 포함, `intel_event_sources` 목록 포함

#### 4-F. Admin 엔드포인트

- `GET /intel/admin/ingest-runs` — ingest run 목록 (Bearer 인증)
- `POST /intel/admin/verify/{id}` — `is_verified=True` 처리 (Bearer 인증)
- `POST /intel/admin/rebuild` — 특정 기간 재색인 (Bearer 인증)

---

### Step 5: 캐시

모든 공개 `/intel/*` API에 짧은 TTL 캐시 적용:

```python
from functools import lru_cache
# 또는 FastAPI-Cache2 또는 간단히 응답 헤더로
# Cache-Control: public, max-age=60

# 권장: stale-on-error 전략
# 업스트림 DB 장애 시 이전 캐시 반환
```

`INTEL_CACHE_TTL_SECS` 환경변수 사용.

---

## DoD

- [ ] Alembic 마이그레이션 `f1a2b3c4d5e6_add_intel_hub_tables` 실행 완료
- [ ] `intel_events` / `intel_event_sources` / `intel_ingest_runs` / `intel_ingest_logs` 모델 생성
- [ ] `scripts/ingest_intel_events.py` — drops/collabs/news 각각 ingest 성공
- [ ] 최초 ingest 후 `intel_events` 행 수 ≥ 50개
- [ ] `GET /intel/events` — 빈 배열 아닌 실제 이벤트 반환
- [ ] `GET /intel/map-points` — geo_precision=country 이상 이벤트 핀 포함
- [ ] `GET /intel/timeline` — 날짜별 버킷 반환
- [ ] `GET /intel/highlights` — 상위 10개 이벤트 반환
- [ ] `GET /intel/admin/ingest-runs` — Bearer 인증 + run 목록 반환
- [ ] Makefile `ingest-intel`, `ingest-intel-news` 타깃 동작 확인

---

## 검증

```bash
# 마이그레이션
uv run alembic upgrade head

# 최초 ingest
uv run python scripts/ingest_intel_events.py

# 이벤트 수 확인
sqlite3 data/fashion.db "
SELECT event_type, layer, COUNT(*) as n, MIN(event_time), MAX(event_time)
FROM intel_events
GROUP BY event_type, layer
ORDER BY n DESC;
"

# API 동작 확인
uv run uvicorn fashion_engine.api.main:app --reload &
curl "http://localhost:8000/intel/events?layers=drop,news&limit=10" | python3 -m json.tool
curl "http://localhost:8000/intel/highlights" | python3 -m json.tool
curl "http://localhost:8000/intel/map-points?layers=drop,collab" | python3 -m json.tool
```

---

## 참고

- PRD v1.0: `docs/FASHION_INTEL_HUB_PRD_2026-03-02.md` §7, §8, §9
- PRD v1.1 리뷰: `docs/fashion_intel_prd_review_v1_1_2026-03-02.md` §3, §4, §6, §8
- 전제: T-072 (INTEL_HUB_SPRINT0_01) 완료
