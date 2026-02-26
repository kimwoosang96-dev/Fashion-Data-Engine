# FRONTEND_05: 가격비교 페이지 가격 히스토리 차트

**Task ID**: T-20260228-003
**Owner**: codex-dev
**Priority**: P2
**Labels**: frontend, backend, enhancement

---

## 배경

`price_history` 테이블에 81,892건의 가격 이력이 쌓여 있지만 현재 UI에서 전혀 활용되지 않음.
`/compare/[key]` 페이지에 채널별 가격 추이 미니 차트를 추가하면 "지금 사는 게 맞나?" 판단에 직접적으로 도움됨.

> 참고: `AGENTS.md` → Database Schema (price_history 테이블)

---

## 요구사항

### 백엔드: 신규 엔드포인트

`GET /products/{product_key:path}/price-history?days=30`

응답 예시:
```json
[
  {
    "channel_name": "Patta KR",
    "history": [
      {"date": "2026-02-01", "price_krw": 150000, "is_sale": false},
      {"date": "2026-02-15", "price_krw": 105000, "is_sale": true}
    ]
  }
]
```

### 프론트엔드: `/compare/[key]` 페이지 수정

- [ ] 채널 테이블 하단에 "가격 추이" 섹션 추가
- [ ] Recharts `LineChart` 사용 (또는 경량 대안)
  - x축: 날짜
  - y축: 가격 (KRW, ₩ 포맷)
  - 채널별 선 색상 구분
  - 세일 구간 점선 또는 점 강조
- [ ] 데이터 없으면 섹션 숨김 (graceful fallback)
- [ ] 기간 선택: 7일 / 30일 / 전체 탭

---

## 기술 스펙

### 백엔드

**신규 서비스 함수**: `src/fashion_engine/services/product_service.py`
```python
async def get_price_history(db, product_key: str, days: int = 30) -> list[dict]:
    # product_key로 products 조회 → product_ids 추출
    # price_history JOIN channels WHERE crawled_at >= now()-days
    # 채널별 그룹화
```

**신규 스키마**: `src/fashion_engine/api/schemas.py`
```python
class PriceHistoryPoint(BaseModel):
    date: str  # "YYYY-MM-DD"
    price_krw: int
    is_sale: bool

class ChannelPriceHistory(BaseModel):
    channel_name: str
    history: list[PriceHistoryPoint]
```

**신규 엔드포인트**: `src/fashion_engine/api/products.py`
```python
@router.get("/price-history/{product_key:path}")
async def get_price_history(product_key: str, days: int = Query(30)):
    ...
```

### 프론트엔드

**패키지 추가**: `cd frontend && npm install recharts`

**신규 API 함수** (`frontend/src/lib/api.ts`):
```typescript
export const getPriceHistory = (productKey: string, days = 30) =>
  apiFetch<ChannelPriceHistory[]>(
    `/products/price-history/${encodeURIComponent(productKey)}?days=${days}`
  );
```

**신규 타입** (`frontend/src/lib/types.ts`):
```typescript
export interface PriceHistoryPoint { date: string; price_krw: number; is_sale: boolean; }
export interface ChannelPriceHistory { channel_name: string; history: PriceHistoryPoint[]; }
```

**수정 파일**: `frontend/src/app/compare/[key]/page.tsx`
- `getPriceHistory(key)` 호출 추가
- `<PriceHistoryChart>` 신규 컴포넌트 (또는 인라인)

---

## 완료 조건

- [ ] `npm run build` 빌드 통과
- [ ] `/compare/patta:patta-team-track-pants` 접속 시 가격 추이 차트 표시
- [ ] 30일 데이터 없는 제품에서 차트 섹션 숨김 (에러 없음)
- [ ] y축 ₩ 단위 포맷 (`₩150,000`)

---

## 참고

- `AGENTS.md` → Database Schema (price_history), Key API Endpoints
- Recharts: https://recharts.org/en-US/api/LineChart
- 참고 패턴: `src/fashion_engine/services/product_service.py` (get_price_comparison)
