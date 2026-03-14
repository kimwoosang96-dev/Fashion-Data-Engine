# 과업 지시서 — 국내 편집샵 채널 조사 (Phase C)

> 담당: Codex Computer Use
> 목적: 국내 편집샵 채널별 브랜드 구성 + Cafe24 cate_no 매핑 조사
> 결과물: `agents/channel_research_results.md` 작성
> 참고 문서: `docs/plan.md` (섹션 2.2)

---

## 배경

Fashion Data Engine v2는 국내 중소형 수입 편집샵의 브랜드별 가격/재고를
한 곳에서 비교하는 서비스다.

크롤링 대상 채널은 대부분 **Cafe24** 기반이며,
Cafe24는 카테고리 번호(`cate_no`) 파라미터로 브랜드별 상품 목록을 필터링한다.

```
예시: https://thexshop.co.kr/category/carhartt-wip/126/
                                                       ^^^
                                                    cate_no = 126
```

이 조사의 목적은 각 채널에서:
1. 어떤 수입 브랜드를 취급하는지 파악
2. 브랜드별 `cate_no` 또는 URL 패턴 확인
3. 플랫폼 확인 (Cafe24 / Shopify / 기타)
4. 온라인 쇼핑 가능 여부 확인

---

## 조사 대상 채널 (31개)

### 그룹 1 — 브랜드 정보 이미 확인됨, cate_no만 조사

| # | 채널 | URL |
|---|------|-----|
| 1 | ETC Seoul | https://etcseoul.com |
| 2 | 옵스큐라 | https://obscura-store.com |
| 3 | 더엑스샵 | https://thexshop.co.kr |
| 4 | 에크루 | https://ecru.co.kr |
| 5 | 아이디룩 | https://idlook.co.kr |
| 6 | 슬로우스테디클럽 | https://slowsteadyclub.com |
| 7 | 아이앰샵 | https://iamshop-online.com |
| 8 | 라이커샵 | https://rhykershop.co.kr |
| 9 | 하이츠스토어 | https://heights-store.com |
| 10 | 애딕티드 서울 | https://addictedseoul.com (**Shopify** — /products.json 확인만) |

### 그룹 2 — 브랜드 구성 + cate_no 모두 조사 필요

| # | 채널 | URL |
|---|------|-----|
| 11 | 8DIVISION | https://www.8division.com |
| 12 | Unipair | https://www.unipair.com |
| 13 | GOOUTSTORE | https://gooutstore.cafe24.com |
| 14 | Alfred | https://www.thegreatalfred.com |
| 15 | Meclads | https://www.meclads.com |
| 16 | Openershop | https://www.openershop.co.kr |
| 17 | empty | https://www.empty.seoul.kr |
| 18 | a.dresser | https://www.adressershop.com |
| 19 | MODE MAN | https://www.mode-man.com |
| 20 | SCULP STORE | https://www.sculpstore.com |
| 21 | BIZZARE | https://www.bizzare.co.kr |
| 22 | grds | https://www.grds.com |
| 23 | Rino Store | https://www.rinostore.co.kr |
| 24 | COEVO | https://www.coevo.com |
| 25 | ADEKUVER | https://www.adekuver.com |
| 26 | PARLOUR | https://www.parlour.kr |
| 27 | 블루스맨 | https://www.bluesman.co.kr |
| 28 | EFFORTLESS | https://www.effortless-store.com |
| 29 | NOCLAIM | https://www.noclaim.co.kr |
| 30 | Casestudy | https://www.casestudystore.co.kr |
| 31 | APPLIXY | https://www.applixy.com |
| 32 | TUNE.KR | https://www.tune.kr |

---

## 각 채널에서 조사할 내용

### 필수 항목

```
1. 플랫폼 확인
   - Cafe24: URL에 cafe24 포함 / 소스에 "cafe24" 텍스트
   - Shopify: URL에 .myshopify.com / /products.json 접근 가능
   - 기타: 자체 플랫폼 여부

2. 온라인 쇼핑 가능 여부
   - 실제 온라인 판매 중인지 (일부는 오프라인 전용)

3. 취급 브랜드 목록
   - 사이트 내 "브랜드" 또는 "Brand" 메뉴에서 확인
   - 수입 브랜드 (해외 브랜드) 위주로 기록
   - 국내 자체 브랜드는 제외

4. 브랜드별 cate_no (Cafe24인 경우)
   - 브랜드 카테고리 클릭 → URL에서 숫자 추출
   - 예: /category/브랜드명/126/ → cate_no = 126
   - 브랜드 필터 URL 패턴이 다른 경우도 기록

5. 상품 목록 URL 패턴
   - 전체 상품: https://채널URL/category/all/숫자/
   - 브랜드별: https://채널URL/category/브랜드/숫자/
   - 세일: https://채널URL/category/sale/숫자/ (있는 경우)
```

### Shopify 채널 (애딕티드 서울)

```
- https://addictedseoul.com/products.json 접근 가능 여부 확인
- 접근 가능하면 "shopify" 플랫폼으로 기록
- 브랜드 목록은 /products.json?limit=250 에서 vendor 필드로 확인
```

---

## 결과물 형식

조사 완료 후 `agents/channel_research_results.md` 파일을 아래 형식으로 작성:

```markdown
# 채널 조사 결과

> 조사일: YYYY-MM-DD

## [채널명]

- URL: https://...
- 플랫폼: cafe24 / shopify / custom / 오프라인전용
- 온라인 판매: 가능 / 불가
- 취급 수입 브랜드: [브랜드1, 브랜드2, ...]
- 전체 상품 cate_no: 123
- 세일 상품 cate_no: 456 (없으면 "없음")
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | Auralee | 101 |
  | Gramicci | 102 |
- 특이사항: (없으면 생략)

---
```

### 접근 불가 / 폐업 채널 처리

```markdown
## [채널명]

- URL: https://...
- 상태: 접근불가 / 폐업 / 오프라인전용
- 비고: (확인된 내용)

---
```

---

## 우선순위

아래 순서로 조사. 브랜드가 이미 알려진 그룹 1을 먼저 처리해서
cate_no만 빠르게 확보:

**1순위** (그룹 1 — 브랜드 이미 확인, cate_no만 필요):
ETC Seoul → 더엑스샵 → 옵스큐라 → 슬로우스테디클럽 → 아이앰샵 → 라이커샵 → 에크루 → 아이디룩 → 하이츠스토어 → 애딕티드 서울

**2순위** (그룹 2 — 브랜드 + cate_no 모두 조사):
8DIVISION → Unipair → GOOUTSTORE → Alfred → Meclads → Openershop → empty → a.dresser → MODE MAN → SCULP STORE → BIZZARE → grds → Rino Store → COEVO → ADEKUVER → PARLOUR → 블루스맨 → EFFORTLESS → NOCLAIM → Casestudy → APPLIXY → TUNE.KR

---

## 참고: Cafe24 cate_no 찾는 법

1. 채널 사이트 접속
2. 상단/사이드 메뉴에서 "Brand" 또는 "브랜드" 클릭
3. 특정 브랜드 클릭
4. URL 확인: `/category/브랜드명/숫자/` 또는 `?cate_no=숫자`
5. 숫자 = cate_no

브랜드 메뉴가 없으면:
- "카테고리" 또는 "Category" 메뉴 확인
- 검색창에 브랜드명 검색 후 URL 확인

---

## 완료 기준

- 31개 채널 중 접근 가능한 모든 채널의 결과 작성
- `agents/channel_research_results.md` 파일 생성 및 커밋
- 조사 불가 채널은 사유 명시

---

*지시서 작성: 2026-03-14*
