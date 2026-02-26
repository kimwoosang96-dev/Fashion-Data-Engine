# FRONTEND_04: 브랜드 상세 페이지 `/brands/[slug]`

**Task ID**: T-20260228-002
**Owner**: codex-dev
**Priority**: P1
**Labels**: frontend, enhancement

---

## 배경

현재 `/brands` 페이지는 브랜드 목록 테이블만 제공하고, 브랜드를 클릭해도 아무것도 없음.
80,096개 제품 데이터가 있으니 브랜드별 제품 목록과 채널별 가격 비교로 이어지는 상세 페이지가 필요함.
백엔드에 `GET /brands/{slug}/products` 엔드포인트가 이미 구현돼 있음.

> 참고: `AGENTS.md` → Key API Endpoints (`/brands/{slug}/products`)

---

## 요구사항

### 페이지: `frontend/src/app/brands/[slug]/page.tsx` (신규)

- [ ] 헤더: 브랜드명, slug, tier badge, 원산지
- [ ] 통계 카드: 총 제품 수 / 세일 제품 수 / 취급 채널 수
- [ ] 제품 그리드: `GET /brands/{slug}/products` 결과 표시
  - `ProductCard` 컴포넌트 재사용
  - 세일 제품 우선 정렬 (API 이미 지원)
- [ ] 세일만 보기 토글 (`is_sale` 필터)
- [ ] 제품 카드 클릭 → `/compare/{product_key}`

### 페이지 수정: `frontend/src/app/brands/page.tsx`

- [ ] 브랜드 행 클릭 시 `/brands/{brand.brand_slug}` 로 이동 (현재 링크 없음)

---

## 기술 스펙

**신규 파일**: `frontend/src/app/brands/[slug]/page.tsx`

**신규 API 함수** (`frontend/src/lib/api.ts`에 추가):
```typescript
export const getBrandProducts = (slug: string, isSale?: boolean) =>
  apiFetch<Product[]>(`/brands/${slug}/products${isSale ? "?is_sale=true" : ""}`);
```

**신규 타입** (`frontend/src/lib/types.ts`에 추가, 필요 시):
```typescript
// /brands/{slug}/products 응답은 기존 Product[] 타입 그대로 사용 가능
```

**재사용할 기존 컴포넌트**:
- `frontend/src/components/ProductCard.tsx`
- `frontend/src/components/ui/badge.tsx`

**백엔드 엔드포인트** (이미 구현됨):
- `GET /brands/{slug}/products` → `list[ProductOut]`
- `GET /brands/{slug}/channels` → 취급 채널 목록

---

## 완료 조건

- [ ] `npm run build` 빌드 통과
- [ ] `/brands/patta` 접속 시 Patta 브랜드 제품 그리드 표시
- [ ] 세일 토글 클릭 시 세일 제품만 표시
- [ ] 제품 클릭 시 `/compare/{product_key}` 이동
- [ ] `/brands` 페이지에서 행 클릭 시 상세 페이지로 이동

---

## 참고

- `AGENTS.md` → Key API Endpoints, Frontend Structure
- 유사 패턴: `frontend/src/app/compare/[key]/page.tsx`
- 현재 브랜드 slug 예시: `patta`, `new-balance`, `adidas`, `supreme`
