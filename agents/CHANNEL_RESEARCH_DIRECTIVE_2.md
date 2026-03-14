# 과업 지시서 — 국내 편집샵 브랜드별 cate_no 추가 조사 (Phase C-2)

> 담당: Codex Computer Use
> 목적: 1차 조사에서 전체 cate_no만 확인된 12개 채널의 **브랜드별 cate_no** 확보
> 결과물: `agents/channel_research_results.md` 에 브랜드별 cate_no 추가 기재
> 선행 문서: `agents/channel_research_results.md` (1차 조사 결과)

---

## 배경

1차 조사(`CHANNEL_RESEARCH_DIRECTIVE.md`)에서 아래 12개 채널은
전체 상품 cate_no는 확인됐으나 **브랜드별 cate_no**를 찾지 못했다.

브랜드별 cate_no가 있어야 "Carhartt WIP 제품만" 또는 "Auralee 제품만"
크롤링할 수 있으므로, 이번 조사에서 반드시 확보해야 한다.

---

## 조사 대상 12개 채널

| # | 채널 | URL | 전체 cate_no | 세일 cate_no |
|---|------|-----|------------|------------|
| 1 | ETC Seoul | https://etcseoul.com | 24 | 1519 |
| 2 | 옵스큐라 | https://obscura-store.com | 28 | 401 |
| 3 | 에크루 | https://ecru.co.kr | 1795 | 1817 |
| 4 | 아이디룩 | https://idlook.co.kr | 32 | - |
| 5 | 라이커샵 | https://rhykershop.co.kr | 493 | 495 |
| 6 | MODE MAN | https://www.mode-man.com | 50 | 965 |
| 7 | Unipair | https://www.unipair.com | 64 | 150 |
| 8 | GOOUTSTORE | https://gooutstore.cafe24.com | - | - |
| 9 | Alfred | https://www.thegreatalfred.com | 44 | 51 |
| 10 | Openershop | https://www.openershop.co.kr | 828 | 1119 |
| 11 | empty | https://www.empty.seoul.kr | - | 868 |
| 12 | PARLOUR | https://www.parlour.kr | 99 | - |

---

## 브랜드별 cate_no 찾는 방법 (심화)

1차 조사에서 공개 브랜드 인덱스가 노출되지 않은 경우,
아래 방법들을 **순서대로** 시도한다.

### 방법 1 — 브랜드 메뉴 직접 클릭

```
사이트 접속 → 상단/사이드 메뉴에서 "Brand" 또는 "브랜드" 클릭
→ 개별 브랜드 클릭 → URL에서 숫자 추출

예: /category/carhartt-wip/375/  →  cate_no = 375
    /brand?cate_no=259            →  cate_no = 259
```

### 방법 2 — 검색창 활용

```
사이트 검색창에 브랜드명 입력 (예: "Auralee")
→ 검색 결과 페이지 URL 또는 필터 링크에서 cate_no 확인
```

### 방법 3 — 상품 상세 페이지에서 역추적

```
상품 목록에서 임의의 상품 클릭
→ 상품 상세 페이지 → "브랜드" 또는 "제조사" 링크 클릭
→ URL에서 cate_no 추출
```

### 방법 4 — 페이지 소스 검색

```
브라우저에서 페이지 소스 보기 (Ctrl+U)
→ "cate_no" 또는 "brand" 텍스트로 검색
→ 브랜드명과 함께 등장하는 숫자 확인
```

### 방법 5 — Cafe24 공통 URL 패턴 시도

아래 경로를 직접 접속해 브랜드 인덱스 노출 여부 확인:
```
https://채널URL/brand.html
https://채널URL/brands.html
https://채널URL/product/maker.html
https://채널URL/product/brand.html
https://채널URL/product/list-brand.html
```

---

## 채널별 1차 조사 특이사항 및 힌트

### ETC Seoul (etcseoul.com)
- 1차: `brand.html`에서 브랜드 인덱스 확인됨. 단 cate_no 링크 추출 실패.
- **힌트**: `/brand.html` 재방문 → 각 브랜드 링크에서 cate_no 추출 재시도
- 확보 목표 브랜드: Arc'teryx, Salomon, Mont-Bell, And Wander, Goldwin, ROA, Satisfy, Auralee, Engineered Garments, Nanamica

### 옵스큐라 (obscura-store.com)
- 1차: SHOP/MEN/WOMEN/SHOES/ACC/SALE 구조만 확인. 브랜드 메뉴 없음.
- **힌트**: 상품 상세 페이지 → 브랜드 링크 역추적 (방법 3)
- 확보 목표 브랜드: Stein, Montbell, And Wander, Guidi, Tekla, Helinox, Brownyard

### 에크루 (ecru.co.kr)
- 1차: `product/maker.html` 발견. A.Presse(1531), Neighborhood(1375) 일부 확인.
- **힌트**: `product/maker.html` 재방문 → 전체 브랜드 목록 cate_no 추출
- 확보 목표 브랜드: A.Presse, Standalone, Perverze, Neighborhood, Ancellm, Acne Studios, MSGM

### 아이디룩 (idlook.co.kr)
- 1차: `E-STORE(/triple/common/estore.html?cate_no=32)` 확인. 브랜드 메뉴 미노출.
- **힌트**: estore 페이지 접속 → 브랜드별 카테고리 링크 탐색. 또는 상품 상세 브랜드 링크(방법 3)
- 확보 목표 브랜드: Sandro, Maje, A.P.C., Marimekko, Denham, Claude Pierlot

### 라이커샵 (rhykershop.co.kr)
- 1차: Gimaguas(565), Diemme(500) 확인. Brands 메뉴 있음.
- **힌트**: `/Brands` 메뉴 직접 클릭 → 전체 브랜드 cate_no 수집
- 확보 목표 브랜드: Gimaguas, Diemme, ROA, Carne Bollente, Opera Sport, Northworks, Martin Faizey

### MODE MAN (mode-man.com)
- 1차: 상품군 cate_no(50, 965)만 확인. 브랜드 인덱스 미노출.
- **힌트**: 메타 키워드에 브랜드명 존재 → 상품 상세 페이지에서 브랜드 링크 역추적(방법 3)
- 확보 목표 브랜드: Nigel Cabourn, Buzz Rickson's, orSlow, Red Wing, Pherrow's, Andersen-Andersen, Reproduction of Found, Sanders

### Unipair (unipair.com)
- 1차: Joe's Garage(257), Green Door Newman(42), UNIPAIR(232) 확인.
- **힌트**: 이미 주요 브랜드 cate_no 확보됨. 추가 수입 브랜드 확인.
- 확보 목표: 수입 슈즈 브랜드 추가 발굴 (Paraboot, Sanders, Alden 등 가능성)

### GOOUTSTORE (gooutstore.cafe24.com)
- 1차: Fashion(26), Outdoor(27) 섹션만 확인. 브랜드 인덱스 미노출.
- **힌트**: `/brand.html` 시도 → 없으면 상품 상세 브랜드 링크 역추적
- 확보 목표 브랜드: 어떤 아웃도어 수입 브랜드를 취급하는지 파악

### Alfred (thegreatalfred.com)
- 1차: 홈(44), 세일(51) 확인. 브랜드 인덱스 미노출.
- **힌트**: 방법 4(소스 검색) 또는 방법 5(공통 URL 시도)
- 확보 목표: 취급 수입 브랜드 파악 + 브랜드별 cate_no

### Openershop (openershop.co.kr)
- 1차: 전체(828), 세일(1119). "해외 디자이너 브랜드 편집샵" 메타 설명.
- **힌트**: SHOP 메뉴 내부 탐색 → Archive Sale 링크에서 브랜드 카테고리 추출
- 확보 목표: 취급 수입 브랜드 파악 + 브랜드별 cate_no

### empty (empty.seoul.kr)
- 1차: 세일(868), Mad Frenzy(750), Florentina Leitner(783), Lillilly(749), Karlaidlaw(751) 확인.
- **힌트**: 이미 일부 확보. RAFFLE 메뉴 탐색으로 추가 브랜드 발굴.
- 확보 목표: 전체 상품 cate_no + 추가 브랜드 cate_no

### PARLOUR (parlour.kr)
- 1차: 전체(99). `maker.html` 404. 남성 구두 편집샵.
- **힌트**: 상품 상세 페이지 브랜드 링크 역추적(방법 3)
- 확보 목표: Alden, Crockett & Jones, J.M. Weston, La Botte Gardiane, R.M. Williams, Berwick, Sanders

---

## 결과물 형식

`agents/channel_research_results.md` 의 해당 채널 섹션에
아래 형식으로 **브랜드별 cate_no 표를 추가 또는 업데이트**:

```markdown
## [채널명] — 업데이트

- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | Auralee | 259 |
  | Arc'teryx | 1088 |
  | (추가 발굴 브랜드) | (cate_no) |
- 업데이트 사유: 2차 조사에서 추가 확보
```

---

## 우선순위

브랜드 커버리지가 높고 cate_no 확보 가능성이 높은 채널 먼저:

1. **ETC Seoul** — `/brand.html` 재방문으로 해결 가능
2. **라이커샵** — Brands 메뉴 존재, 재탐색으로 해결 가능
3. **에크루** — `product/maker.html` 재방문으로 해결 가능
4. **MODE MAN** — 아메카지 특화, 상품 상세 역추적
5. **옵스큐라** — 상품 상세 역추적
6. **아이디룩** — estore 페이지 탐색
7. **Openershop** — SHOP 내부 탐색
8. **GOOUTSTORE** — 브랜드 인덱스 탐색
9. **Alfred** — 소스 탐색
10. **PARLOUR** — 상품 상세 역추적
11. **empty** — 추가 브랜드 발굴
12. **Unipair** — 추가 수입 브랜드 확인

---

## 완료 기준

- 12개 채널 각각에 대해 브랜드별 cate_no 최대한 확보
- 찾지 못한 경우 시도한 방법과 실패 사유 명시
- `agents/channel_research_results.md` 업데이트 후 커밋

---

*지시서 작성: 2026-03-14*
