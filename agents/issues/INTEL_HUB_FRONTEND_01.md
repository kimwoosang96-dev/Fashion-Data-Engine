# T-074 | INTEL_HUB_FRONTEND_01

> **목적**: Fashion Intel Hub v1 프론트엔드 구현
> — `/intel` 페이지, 레이어 토글, Maplibre 지도(country precision), 피드(가상 스크롤), 타임라인 차트

---

## 배경

PRD v1.0 §10, PRD v1.1 §9 (UX 성능 원칙) 기반.

**전제**: T-072(INTEL_HUB_SPRINT0_01)와 T-073(INTEL_HUB_DATA_MODEL_01) 완료.

**v1 UI 범위 (DoD 기준)**:
- 레이어 토글 (drop/collab/news/sale_start)
- Maplibre 지도 — country precision 핀, 클릭 시 이벤트 카드 오픈
- 피드 리스트 — 가상 스크롤 (최대 200개 DOM 유지)
- 타임라인 바 차트 — 날짜별 레이어 stacked
- 이벤트 상세 드로어 — 브랜드/채널/제품 연결 + 액션 버튼
- URL 쿼리 상태 공유 (deep link)

---

## 요구사항

### Step 1: `/intel` 페이지 기본 레이아웃

**파일**: `frontend/src/app/intel/page.tsx`

**레이아웃 구조**:
```
┌──────────────────────────────────────────────┐
│  Intel Hub                 [레이어 토글 바]  │
├─────────────────────┬────────────────────────┤
│                     │  [타임라인 차트]        │
│   지도              │  [피드 리스트]          │
│   (Maplibre)        │  ─────────────────────  │
│                     │  [이벤트 카드 ×N]       │
└─────────────────────┴────────────────────────┘
```

- 좌측 지도 40%, 우측 피드 60% (md 이상), 모바일은 피드 단독
- 피드 클릭 → 지도 fly to, 지도 핀 클릭 → 피드 해당 카드 강조

---

### Step 2: 레이어 토글 컴포넌트

**파일**: `frontend/src/components/intel/LayerToggle.tsx`

```tsx
type Layer = 'drop' | 'collab' | 'news' | 'sale_start' | 'sales_spike' | 'sold_out' | 'restock';

const LAYER_CONFIG: Record<Layer, { label: string; color: string; icon: string }> = {
  drop:        { label: 'Drops',      color: '#8B5CF6', icon: '📦' },
  collab:      { label: 'Collabs',    color: '#EC4899', icon: '🤝' },
  news:        { label: 'News',       color: '#3B82F6', icon: '📰' },
  sale_start:  { label: 'Sales',      color: '#EF4444', icon: '🏷️' },
  sales_spike: { label: 'Spike',      color: '#F97316', icon: '📈' },
  sold_out:    { label: 'Sold Out',   color: '#6B7280', icon: '🔴' },
  restock:     { label: 'Restock',    color: '#10B981', icon: '🔄' },
};

// v1 기본 활성: drop, collab, news (sale_start는 T-075 이후)
const DEFAULT_LAYERS: Layer[] = ['drop', 'collab', 'news'];
```

URL 쿼리 상태: `?layers=drop,collab,news&range=7d`

---

### Step 3: Maplibre 지도 구현

**파일**: `frontend/src/components/intel/IntelMap.tsx`

T-072에서 스텁 생성됨 → 이 과업에서 실제 구현.

**타일**: `NEXT_PUBLIC_MAP_STYLE_URL` (OpenFreeMap liberty 스타일)

**핀 렌더링**:
```tsx
// /intel/map-points API 결과를 GeoJSON 소스로 추가
// severity에 따른 원 크기: critical=20, high=14, medium=10, low=7
// event_type에 따른 색상: LAYER_CONFIG 색상 사용
// geo_precision=global 이벤트는 제외 (지도 표시 불가)

const geojson = {
  type: 'FeatureCollection',
  features: points.map(p => ({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [p.lng, p.lat] },
    properties: { id: p.id, event_type: p.event_type, severity: p.severity, title: p.title }
  }))
};
```

**클러스터링** (Maplibre 내장):
```tsx
map.addSource('intel-events', {
  type: 'geojson',
  data: geojson,
  cluster: true,
  clusterMaxZoom: 8,
  clusterRadius: 40,
});
```

**인터랙션**:
- 핀 클릭 → 해당 이벤트 상세 드로어 오픈
- 피드 카드 호버 → 지도 해당 핀 강조 (pulse 애니메이션)

**주의**: `dynamic(() => import('./IntelMap'), { ssr: false })` 패턴 사용 (SSR 미지원)

---

### Step 4: 피드 리스트 (가상 스크롤)

**파일**: `frontend/src/components/intel/IntelFeed.tsx`

**가상 스크롤 구현**:
- `react-virtual` 또는 `@tanstack/react-virtual` 사용
- 아이템 높이 고정 (120px) 또는 추정
- DOM에 최대 200개 유지

**이벤트 카드 컴포넌트** (`IntelEventCard.tsx`):
```tsx
interface IntelEventCardProps {
  event: IntelEvent;
  isHighlighted?: boolean;
  onClick: (event: IntelEvent) => void;
}

// 카드 UI 요소:
// - severity 배지 (색상: critical=red, high=orange, medium=yellow, low=gray)
// - event_type 아이콘 (LAYER_CONFIG icon)
// - title + summary (2줄 truncate)
// - event_time 상대 시간 (예: "3시간 전")
// - source_domain + confidence 배지
// - brand/channel 태그 (있으면)
```

**페이지네이션**: cursor 기반 무한스크롤 (`IntersectionObserver`)

---

### Step 5: 타임라인 바 차트

**파일**: `frontend/src/components/intel/IntelTimeline.tsx`

`/intel/timeline` API 데이터로 stacked bar chart 렌더링.

**구현**: 커스텀 SVG (기존 `PriceHistoryChart.tsx` 패턴 참고) 또는 `recharts`

```tsx
// 각 날짜 버킷을 stacked bar로
// x축: 날짜 (granularity 기준)
// y축: 이벤트 수
// 색상: LAYER_CONFIG.color 사용
// 클릭: 해당 날짜로 피드 필터 적용
```

---

### Step 6: 이벤트 상세 드로어

**파일**: `frontend/src/components/intel/IntelEventDrawer.tsx`

`/intel/events/{id}` API 호출 → 상세 정보 표시.

**드로어 컨텐츠**:
- 이벤트 제목 + 요약
- severity/confidence 배지
- 원문 링크 (source_url)
- 연결 브랜드 → `/brands/{slug}` 링크
- 연결 채널 → 외부 쇼핑몰 링크
- 연결 제품 → `/compare/{product_key}` 링크
- "Watch" 버튼 (관심 등록, WatchListItem — 기존 기능 연결)
- `intel_event_sources` 목록 (여러 출처가 있는 경우)

---

### Step 7: Nav 메뉴 + 딥링크

**`frontend/src/components/Nav.tsx`에 "Intel" 메뉴 추가**:
```tsx
<Link href="/intel">Intel</Link>
```

**URL 쿼리 상태 (deep link)**:
```
/intel?layers=drop,collab&range=7d&country=KR
/intel?layers=news&range=30d&brand=nike
```

`useSearchParams` + `useRouter`로 URL 동기화.

---

### Step 8: API 타입 + 클라이언트

**파일**: `frontend/src/lib/api.ts`에 추가

```ts
export interface IntelEvent {
  id: number;
  event_type: string;
  layer: string;
  event_time: string | null;
  detected_at: string;
  brand_id: number | null;
  channel_id: number | null;
  product_key: string | null;
  geo_country: string | null;
  geo_lat: number | null;
  geo_lng: number | null;
  geo_precision: string;
  title: string;
  summary: string | null;
  source_url: string | null;
  source_domain: string | null;
  severity: string;
  confidence: string;
  is_verified: boolean;
}

export interface IntelMapPoint {
  id: number;
  lat: number;
  lng: number;
  event_type: string;
  severity: string;
  title: string;
  geo_precision: string;
}

export interface IntelTimelineBucket {
  date: string;
  total: number;
  by_layer: Record<string, number>;
}

// API 함수
export async function getIntelEvents(params: {...}): Promise<IntelEventsResponse>
export async function getIntelMapPoints(params: {...}): Promise<{points: IntelMapPoint[]}>
export async function getIntelTimeline(params: {...}): Promise<{buckets: IntelTimelineBucket[]}>
export async function getIntelHighlights(): Promise<{highlights: IntelEvent[]}>
export async function getIntelEvent(id: number): Promise<IntelEvent>
```

---

### Step 9: 성능 최적화 (PRD v1.1 §9.1)

- **Instant render**: 초기 로드 시 `highlights` + `map-points(요약)` 먼저, 피드/타임라인 lazy-load
- **지도 초기화**: `useEffect` 내에서 비동기 초기화 (`map.on('load', ...)`)
- **맵 포인트 업데이트**: 레이어 토글 시 GeoJSON 소스 데이터만 교체 (지도 재초기화 불필요)
- **피드 API 호출**: debounce 300ms (레이어 토글 연속 클릭 방지)

---

## DoD

- [ ] `/intel` 페이지 접근 시 레이아웃 렌더링 (지도 + 피드 + 타임라인 + 레이어 토글)
- [ ] Maplibre 지도 OpenFreeMap 타일 로드 완료
- [ ] 지도에 country precision 핀 표시 (Intel 이벤트 있는 경우)
- [ ] 레이어 토글 클릭 시 피드/지도 필터링 동작
- [ ] 이벤트 카드 클릭 → 상세 드로어 오픈
- [ ] 피드 무한스크롤 (50개 이후 cursor 페이지네이션)
- [ ] 타임라인 차트 날짜별 레이어 stacked 렌더링
- [ ] Nav에 "Intel" 메뉴 추가
- [ ] URL 쿼리로 레이어/기간 상태 공유 (deep link)
- [ ] `npm run build` 빌드 성공

---

## 패키지 추가 필요

```bash
cd frontend
npm install @tanstack/react-virtual
# maplibre-gl은 T-072에서 이미 설치됨
```

---

## 참고

- PRD v1.0: `docs/FASHION_INTEL_HUB_PRD_2026-03-02.md` §5, §6, §10
- PRD v1.1 리뷰: `docs/fashion_intel_prd_review_v1_1_2026-03-02.md` §9 (성능 원칙)
- 기존 가상 스크롤 패턴: `frontend/src/app/sales/page.tsx` (IntersectionObserver)
- 기존 드로어/모달 패턴: `frontend/src/app/compare/[key]/page.tsx`
- 전제: T-072, T-073 완료
