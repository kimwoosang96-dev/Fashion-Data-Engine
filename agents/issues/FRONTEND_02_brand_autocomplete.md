# FRONTEND_02: 대시보드 검색창 브랜드 자동완성 드롭다운

**Task ID**: T-20260227-003
**Owner**: codex-dev
**Priority**: P1
**Labels**: frontend, enhancement

---

## 배경

대시보드(`/`) 검색창에서 타이핑 시 현재 제품 검색만 동작함.
브랜드명을 입력했을 때 브랜드 제안이 드롭다운으로 나타나면 해당 브랜드 세일 제품을 빠르게 필터링할 수 있음.

> 참고: `AGENTS.md` → Frontend Structure, Key API Endpoints 섹션

---

## 요구사항

- [ ] 검색창 타이핑 시 제품 검색과 브랜드 검색을 **병렬**로 호출
- [ ] 드롭다운에 브랜드 결과(상단)와 제품 결과(하단) 구분 표시
- [ ] 브랜드 행 클릭 → 그리드를 해당 브랜드의 세일 제품으로 필터링 (`getSaleProducts(60, brand.slug)`)
- [ ] 제품 행 클릭 → 기존 동작 유지 (제품 그리드 업데이트)
- [ ] 검색창 바깥 클릭 시 드롭다운 닫힘
- [ ] 검색어 없으면 드롭다운 숨김

---

## 기술 스펙

### 신규 컴포넌트: `frontend/src/components/SearchDropdown.tsx`

```tsx
interface SearchDropdownProps {
  brandResults: Brand[];
  productResults: Product[];
  onBrandClick: (brand: Brand) => void;
  onProductClick: (product: Product) => void;
}
```

각 섹션 헤더: "브랜드" / "제품"
결과 없으면 해당 섹션 숨김

### 수정 파일: `frontend/src/app/page.tsx`

```tsx
// handleSearch 병렬 호출로 교체
const [products, brands] = await Promise.all([
  searchProducts(q),
  searchBrands(q),
]);
setBrandSuggestions(brands);
setSearchResults(products);
```

브랜드 선택 시 `setQuery(brand.name)` + `setSaleProducts` 교체 + 드롭다운 닫기

### 재사용할 기존 함수 (이미 구현됨)

- `frontend/src/lib/api.ts:37` — `searchBrands(q: string)`
- `frontend/src/lib/api.ts:20` — `getSaleProducts(limit, brand?: string)`
- `frontend/src/lib/api.ts:23` — `searchProducts(q: string)`

### 재사용할 타입

- `frontend/src/lib/types.ts` — `Brand`, `Product`

---

## 완료 조건

- [ ] `npm run build` 빌드 통과 (타입 에러 없음)
- [ ] 검색창에 "supreme" 입력 시 브랜드 "Supreme" 행 표시
- [ ] 브랜드 행 클릭 시 그리드가 해당 브랜드 세일 제품으로 교체
- [ ] 검색어 지우면 원래 세일 그리드로 복귀
- [ ] 드롭다운이 검색창 바깥 클릭 시 닫힘

---

## 참고

- 기존 유사 구현: `frontend/src/app/watchlist/page.tsx` (브랜드 검색 드롭다운 패턴)
- `AGENTS.md` → Frontend Structure, Coding Conventions
