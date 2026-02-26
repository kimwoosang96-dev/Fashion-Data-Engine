# FRONTEND_03: 브랜드/채널 페이지 클라이언트 사이드 검색 필터

**Task ID**: T-20260227-004
**Owner**: codex-dev
**Priority**: P1
**Labels**: frontend, enhancement, ux

---

## 배경

현재 `brands/page.tsx`는 최대 400개 브랜드를 한 번에 로드하고, `channels/page.tsx`는 250개 채널을 로드하지만
검색/필터 기능이 없어서 원하는 항목을 찾기 어려움.
추가 API 호출 없이 클라이언트 사이드 필터링으로 구현 가능.

> 참고: `AGENTS.md` → Frontend Structure

---

## 요구사항

### brands/page.tsx
- [ ] 페이지 상단에 검색 입력창 추가 (`<Input placeholder="브랜드 검색...">`)
- [ ] 입력 시 `brand.brand_name` 또는 `brand.brand_slug`에 대소문자 무시 부분 매칭
- [ ] 티어 필터 드롭다운 추가: "전체 / high-end / premium / street / sports"
- [ ] 검색어 + 티어 필터 AND 조건 적용
- [ ] 필터 적용 후 결과 수 표시: `"N개 브랜드"`

### channels/page.tsx
- [ ] 페이지 상단에 검색 입력창 추가 (`<Input placeholder="채널 검색...">`)
- [ ] 입력 시 `channel.channel_name` 또는 `channel.channel_url`에 대소문자 무시 부분 매칭
- [ ] 세일 여부 필터 토글: "세일 진행 중만 보기" checkbox 또는 토글
- [ ] 필터 적용 후 결과 수 표시: `"N개 채널"`

---

## 기술 스펙

**수정 파일**: `frontend/src/app/brands/page.tsx`, `frontend/src/app/channels/page.tsx`

```tsx
// brands/page.tsx 패턴
const [query, setQuery] = useState("");
const [tierFilter, setTierFilter] = useState<string>("all");

const filtered = items.filter((b) => {
  const matchQuery = !query ||
    b.brand_name.toLowerCase().includes(query.toLowerCase()) ||
    b.brand_slug.toLowerCase().includes(query.toLowerCase());
  const matchTier = tierFilter === "all" || b.tier === tierFilter;
  return matchQuery && matchTier;
});
```

**재사용할 기존 컴포넌트**:
- `frontend/src/components/ui/input` — `<Input>`
- 추가 API 호출 없음 (이미 로드된 데이터 필터링)

**재사용할 타입**:
- `frontend/src/lib/types.ts` — `BrandHighlight`, `ChannelHighlight`

---

## 완료 조건

- [ ] `npm run build` 빌드 통과
- [ ] 브랜드 페이지: "pal" 검색 시 "Palaces", "Palace" 포함 브랜드만 표시
- [ ] 브랜드 페이지: 티어 "street" 선택 시 해당 브랜드만 표시
- [ ] 채널 페이지: 채널명/URL로 검색 가능
- [ ] 채널 페이지: "세일 진행 중만" 필터 동작

---

## 참고

- `AGENTS.md` → Frontend Structure, Coding Conventions
- `frontend/src/lib/types.ts` — `BrandHighlight.tier`, `ChannelHighlight.is_running_sales`
