# T-072 | INTEL_HUB_SPRINT0_01

> **목적**: Fashion Intel Hub v1 구현 전 선행 조건 완비
> — Railway Worker 스케줄러 확장, 지도 라이브러리 확정, 환경변수 정의

---

## 배경

PRD v1.1 리뷰는 Intel Hub 구현 전 반드시 해결해야 할 선행 조건을 **Sprint 0**으로 명시한다.

> "Intel Hub는 정기 ingest가 필요하다. 현재 자동화(Worker)가 없으면 '탭은 있는데 데이터가 안 움직이는' 상태가 된다."

현재 상태:
- Railway Worker 서비스: `scheduler.py`로 운영 중 (03:00 크롤, 07:10 뉴스 수집)
- Intel ingest 크론 잡: 미등록
- 지도 라이브러리: 미확정 (`/map` 페이지는 정적 SVG 사용 중)
- Intel 관련 환경변수: 미정의

---

## 요구사항

### Step 1: 지도 라이브러리 선택 — Maplibre GL JS 사용

**결정**: Maplibre GL JS v4 (오픈소스, 무료 타일 가능)

근거:
- OpenFreeMap / Stadia Maps 무료 타일 사용 가능 (API 키 불필요 or 무료 티어 충분)
- worldmonitor(참고 레퍼런스)와 동일 라이브러리
- Next.js 16 App Router와 호환 (`dynamic import + ssr:false` 패턴)
- Leaflet 대비 벡터 타일 지원 → 고줌 클러스터링 성능 우수

**패키지 추가**:
```bash
cd frontend
npm install maplibre-gl pmtiles
# pmtiles: 오프라인/CDN 타일 지원 (선택, 지금은 설치만)
```

**환경변수** (`frontend/.env.local`):
```
NEXT_PUBLIC_MAP_STYLE_URL=https://tiles.openfreemap.org/styles/liberty
# 또는 Stadia Maps: https://tiles.stadiamaps.com/styles/alidade_smooth.json
```

**컴포넌트 스텁 생성** (`frontend/src/components/IntelMap.tsx`):
```tsx
// 스텁: T-074(INTEL_HUB_FRONTEND_01)에서 구현
'use client';
export default function IntelMap() {
  return <div id="intel-map" style={{ width: '100%', height: '400px' }} />;
}
```

---

### Step 2: Railway Worker에 Intel ingest 크론 잡 추가

**파일**: `scripts/scheduler.py`

현재 스케줄:
- 03:00 — `crawl_products.py` (전체 크롤)
- 07:00 — `crawl_news.py` (뉴스 수집)
- 07:10 — `update_exchange_rates.py`

**추가 스케줄** (Intel ingest — T-073 구현 후 활성화):
```python
# Intel Hub ingest 잡 (T-073 구현 후 활성화)
# scheduler.add_job(
#     run_intel_ingest,
#     CronTrigger(hour=7, minute=30),
#     id="intel_ingest_0730",
#     replace_existing=True,
# )
```

지금은 **주석 처리 상태로 추가**. T-073 완료 후 주석 해제.

---

### Step 3: Intel 환경변수 정의

**`.env.example`에 추가**:
```bash
# Intel Hub
INTEL_NEWS_INGEST_ENABLED=true   # RSS 뉴스 → intel_events 미러링
INTEL_DERIVED_ENABLED=false       # 파생 이벤트(sale_start/sold_out 등) — T-075 완료 후 활성화
INTEL_MIN_CONFIDENCE=low          # 이벤트 공개 최소 신뢰도 (low|medium|high)
INTEL_CACHE_TTL_SECS=60          # /intel/* API 캐시 TTL
```

---

### Step 4: FastAPI 라우터 파일 스텁 생성

**파일**: `src/fashion_engine/api/intel.py`

```python
"""
Fashion Intel Hub API — 스텁
T-073(INTEL_HUB_DATA_MODEL_01)에서 구현 예정.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/intel", tags=["intel"])

@router.get("/events")
async def list_events():
    return {"events": [], "total": 0, "note": "Not yet implemented — see T-073"}

@router.get("/map-points")
async def map_points():
    return {"points": []}

@router.get("/timeline")
async def timeline():
    return {"buckets": []}

@router.get("/highlights")
async def highlights():
    return {"highlights": []}
```

**`src/fashion_engine/api/main.py`에 라우터 등록**:
```python
from fashion_engine.api.intel import router as intel_router
app.include_router(intel_router)
```

---

### Step 5: 검증

```bash
# 라우터 등록 확인
uv run uvicorn fashion_engine.api.main:app --reload &
curl -s http://localhost:8000/intel/events | python3 -m json.tool

# 스케줄러 dry-run (Intel 잡 포함 확인)
uv run python scripts/scheduler.py --dry-run

# frontend 빌드 확인
cd frontend && npm install && npm run build
```

---

## DoD

- [ ] `maplibre-gl` npm 패키지 설치 완료, `frontend/src/components/IntelMap.tsx` 스텁 생성
- [ ] `NEXT_PUBLIC_MAP_STYLE_URL` 환경변수 `.env.example` 반영
- [ ] `scripts/scheduler.py`에 Intel ingest 크론 잡 주석 추가
- [ ] `.env.example`에 Intel 환경변수 4개 추가
- [ ] `src/fashion_engine/api/intel.py` 스텁 생성 + `main.py` 라우터 등록
- [ ] `GET /intel/events` 200 응답 확인

---

## 참고

- PRD v1.0: `docs/FASHION_INTEL_HUB_PRD_2026-03-02.md`
- PRD v1.1 리뷰: `docs/fashion_intel_prd_review_v1_1_2026-03-02.md` §11 (Sprint 0)
- worldmonitor: https://worldmonitor.app (참고 UX)
- Maplibre GL JS: https://maplibre.org/maplibre-gl-js/docs/
- OpenFreeMap 타일: https://openfreemap.org
