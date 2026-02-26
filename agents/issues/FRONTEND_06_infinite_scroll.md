# FRONTEND_06: 세일 페이지 무한스크롤 (19,997개 제품 대응)

**Task ID**: T-20260228-004
**Owner**: codex-dev
**Priority**: P2
**Labels**: frontend, ux, performance

---

## 배경

현재 `sales/page.tsx`는 150개 고정 로드, `page.tsx` (대시보드)는 60개 고정.
DB에 세일 제품이 19,997개 있으므로, 스크롤 기반 추가 로드가 없으면 대부분의 세일 제품이 보이지 않음.

> 참고: `AGENTS.md` → Key API Endpoints (`/products/sales-highlights?limit=&offset=`)

---

## 요구사항

### `frontend/src/app/sales/page.tsx` 수정

- [ ] 초기 로드: 60개 (`limit=60, offset=0`)
- [ ] 하단 스크롤 도달 시 60개 추가 로드 (`offset += 60`)
- [ ] Intersection Observer API 사용 (외부 라이브러리 없이)
- [ ] 로딩 스피너: 추가 로드 중 하단에 표시
- [ ] "더 이상 없음" 메시지: 전체 로드 완료 시
- [ ] 총 세일 제품 수 헤더에 표시 (`"세일 제품 19,997개"`)

---

## 기술 스펙

**수정 파일**: `frontend/src/app/sales/page.tsx`

```tsx
const observerRef = useRef<HTMLDivElement>(null);
const [offset, setOffset] = useState(0);
const [hasMore, setHasMore] = useState(true);
const LIMIT = 60;

// Intersection Observer
useEffect(() => {
  const observer = new IntersectionObserver(
    ([entry]) => { if (entry.isIntersecting && hasMore) loadMore(); },
    { threshold: 0.1 }
  );
  if (observerRef.current) observer.observe(observerRef.current);
  return () => observer.disconnect();
}, [hasMore, offset]);

const loadMore = async () => {
  const next = await getSaleHighlights(LIMIT, offset);
  if (next.length < LIMIT) setHasMore(false);
  setItems(prev => [...prev, ...next]);
  setOffset(prev => prev + LIMIT);
};
```

**재사용할 기존 함수** (`frontend/src/lib/api.ts:32`):
```typescript
getSaleHighlights(limit: number, offset: number) // 이미 offset 파라미터 지원
```

---

## 완료 조건

- [ ] `npm run build` 빌드 통과
- [ ] `/sales` 페이지 스크롤 내리면 자동으로 추가 제품 로드
- [ ] 로딩 중 스피너 표시
- [ ] 마지막 페이지에서 "모두 불러왔습니다" 메시지
- [ ] 총 세일 수 헤더 표시

---

## 참고

- `AGENTS.md` → Frontend Structure, Key API Endpoints
- Intersection Observer MDN: https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API
- 유사 패턴: `frontend/src/app/purchases/page.tsx` (테이블 로드 패턴 참고)
