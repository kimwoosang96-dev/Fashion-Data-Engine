# 채널 리서치 의뢰서 — GPT Pro용
> 작성일: 2026-03-01 | 최종 업데이트: 2026-03-01 | 담당: Claude PM → GPT Pro 조사 의뢰

---

## 배경 및 목적

Fashion Data Engine은 Shopify/Cafe24 기반 패션 편집샵과 브랜드 스토어의 제품·가격 데이터를 수집합니다.
현재 두 가지 문제가 발견되어, 아래 채널들의 실태를 정확히 파악해야 합니다.

**문제 1: Route 배송보험 제품 오인덱싱**
Shopify 스토어에 설치된 Route Package Protection 앱이 `/products.json` API에 일반 제품처럼 노출됩니다.
크롤러가 이를 패션 제품으로 오인식하여 DB에 저장하고 있습니다.
- 예시: "Shipping Protection by Route" (vendor: route, ₩1,398~₩1,400)
- 영향 채널: The Loop Running Supply, 18 East, Velour Garments (스크린샷 확인)
- 코드 픽스: T-20260301-054 (vendor/title/product_type denylist 추가 — 과업지시 완료)

**문제 2: 제품 0개 채널 73개 — 원인 파악 필요**
DB에 edit-shop + brand-store 기준 73개 채널이 제품 0개 상태이며 **전부 크롤 시도 이력 없음(never)**.
웹사이트 구조, 플랫폼 (Shopify가 아닐 가능성), URL 유효성 등을 확인해야 합니다.

---

## 조사 채널 목록

### 그룹 A: Route 배송보험 문제 확인된 채널 (3개)

| 채널명 | 타입 | 국가 | URL | 문제 |
|--------|------|------|-----|------|
| The Loop Running Supply | edit-shop | US | thelooprunningsupply.com | Route 배송보험 제품 노출 |
| 18 East | brand-store | US | 18east.com | Route 배송보험 제품 노출 |
| Velour Garments | brand-store | ES | velourgarments.com | Route 배송보험 제품 노출 |

**조사 항목 (그룹 A 각 채널):**
1. 현재 스토어 상태 (정상 운영 / 임시 폐쇄 / 도메인 변경)
2. Shopify 플랫폼 여부 확인 (`/products.json?limit=5` 접근 테스트)
3. Route.com 앱 설치 여부 (카트/체크아웃 페이지에서 "Route Protection" 위젯 확인)
4. 제품 카탈로그에서 "Shipping Protection" 또는 "Package Protection" 제품 존재 여부
5. 채널이 패션 편집샵으로서 적합한지 여부 (주력 취급 브랜드/카테고리)

---

### 그룹 B-1: 글로벌 유명 채널 — Shopify 여부 우선 확인 (12개)

> 패션 업계 인지도가 높아 크롤 가능하면 데이터 가치가 큼. Shopify인지 먼저 확인.

| 채널명 | 타입 | 국가 | URL |
|--------|------|------|-----|
| Bodega | edit-shop | US | https://bdgastore.com |
| Joe Freshgoods | brand-store | US | https://www.joefreshgoods.com |
| Warren Lotas | brand-store | US | https://www.warrenlotas.com |
| Dover Street Market | edit-shop | UK | https://store.doverstreetmarket.com |
| PALACE SKATEBOARDS | brand-store | UK | https://shop.palaceskateboards.com |
| SEVENSTORE | edit-shop | UK | https://www.sevenstore.com |
| HIP | edit-shop | UK | https://www.thehipstore.co.uk |
| HBX | edit-shop | HK | https://hbx.com |
| AXEL ARIGATO | brand-store | SE | https://www.axelarigato.com |
| Séfr | brand-store | SE | https://www.sefr-online.com |
| KA-YO | edit-shop | SE | https://www.ka-yo.com |
| Camperlab | brand-store | ES | https://www.camperlab.com |

**조사 항목:**
1. `/products.json?limit=5` 접근 가능 여부 (Shopify 여부 확인)
2. 현재 스토어 상태 (HTTP 상태 코드)
3. 플랫폼이 Shopify가 아니라면 무엇인지 (WooCommerce / 자체 개발 / 기타)
4. 크롤 가능 여부 판단

---

### 그룹 B-2: 일본 채널 — 비표준 플랫폼 의심 (15개)

> 일본 쇼핑몰 중 일부는 stores.jp / buyshop.jp / theshop.jp / ocnk.net / shop-pro.jp 등
> Shopify/Cafe24가 아닌 플랫폼 사용. 플랫폼 확인 필수.

| 채널명 | 타입 | URL | 추정 플랫폼 |
|--------|------|-----|------------|
| SOMEIT | brand-store | https://someit.stores.jp | stores.jp |
| elephant TRIBAL fabrics | brand-store | https://elephab.buyshop.jp | buyshop.jp |
| UNDERCOVER Kanazawa | edit-shop | https://undercoverk.theshop.jp | theshop.jp |
| TITY | edit-shop | https://tity.ocnk.net | ocnk.net |
| Laid back | edit-shop | https://laidback0918.shop-pro.jp | MakeShop |
| TIGHTBOOTH | brand-store | https://shop.tightbooth.com | ? |
| TTTMSW | brand-store | https://www.tttmsw.jp | ? |
| ACRMTSM | brand-store | https://www.acrmtsm.jp | ? |
| CLESSTE | brand-store | https://www.clesste.com | ? |
| F/CE | brand-store | https://www.fce-store.com | ? |
| LTTT | brand-store | https://www.lttt.life | ? |
| MaisonShunIshizawa store | brand-store | https://www.maisonshunishizawa.online | ? |
| Pherrow's | brand-store | https://www.pherrows.tokyo | ? |
| The Real McCoy's | brand-store | https://www.therealmccoys.jp | ? |
| and wander | brand-store | https://www.andwander.co.kr | ? (URL이 .co.kr인데 JP 등록 — 확인 필요) |

**조사 항목:**
1. `/products.json?limit=5` 접근 가능 여부 (Shopify 여부)
2. 실제 사용 플랫폼 (페이지 소스 또는 HTTP 헤더 확인)
3. `and wander`의 경우: 일본 공식 스토어 URL이 .co.kr인지, 별도 한국 스토어인지

---

### 그룹 B-3: 한국 채널 — Cafe24 또는 자체몰 (29개)

> 한국 편집샵/브랜드스토어. Cafe24 기반일 가능성이 높으나, 폐업·URL 변경 가능성도 있음.
> 아래 채널 중 **인지도 높은 우선순위 채널**을 먼저 확인.

**우선 확인 (국내 인지도 높음):**

| 채널명 | 타입 | URL |
|--------|------|-----|
| Kasina | edit-shop | https://www.kasina.co.kr |
| thisisneverthat | brand-store | https://www.thisisneverthat.com |
| CAYL | brand-store | https://www.cayl.co.kr |
| Unipair | edit-shop | https://www.unipair.com |
| ECRU Online | edit-shop | https://www.ecru.co.kr |
| GOOUTSTORE | edit-shop | https://gooutstore.cafe24.com |
| obscura | edit-shop | https://www.obscura-store.com |
| Casestudy | edit-shop | https://www.casestudystore.co.kr |
| grds | edit-shop | https://www.grds.com |

**나머지 확인:**

| 채널명 | 타입 | URL |
|--------|------|-----|
| 8DIVISION | edit-shop | https://www.8division.com |
| ADEKUVER | edit-shop | https://www.adekuver.com |
| APPLIXY | edit-shop | https://www.applixy.com |
| Alfred | edit-shop | https://www.thegreatalfred.com |
| BIZZARE | edit-shop | https://www.bizzare.co.kr |
| COEVO | edit-shop | https://www.coevo.com |
| EFFORTLESS | edit-shop | https://www.effortless-store.com |
| ETC SEOUL | edit-shop | https://www.etcseoul.com |
| MODE MAN | edit-shop | https://www.mode-man.com |
| Meclads | edit-shop | https://www.meclads.com |
| NOCLAIM | edit-shop | https://www.noclaim.co.kr |
| Openershop | edit-shop | https://www.openershop.co.kr |
| PARLOUR | edit-shop | https://www.parlour.kr |
| Rino Store | edit-shop | https://www.rinostore.co.kr |
| SCULP STORE | edit-shop | https://www.sculpstore.com |
| THEXSHOP | edit-shop | https://www.thexshop.co.kr |
| TUNE.KR | edit-shop | https://www.tune.kr |
| a.dresser | edit-shop | https://www.adressershop.com |
| empty | edit-shop | https://www.empty.seoul.kr |
| Sun Chamber Society | brand-store | https://www.sunchambersociety.com |
| heritagefloss | brand-store | https://www.heritagefloss.com |
| nightwaks | brand-store | https://www.nightwaks.com |
| 브레슈 (Breche) | brand-store | https://www.breche-online.com |
| 블루스맨 (Bluesman) | edit-shop | https://www.bluesman.co.kr |

**조사 항목:**
1. 도메인 유효 여부 (HTTP 상태 코드)
2. Cafe24 여부 (`/product/list.html?cate_no=1` 또는 페이지 소스에서 cafe24 확인)
3. Shopify 여부 (`/products.json?limit=5`)
4. 폐업 또는 도메인 이전 여부

---

### 그룹 B-4: 기타 글로벌 채널 (4개)

| 채널명 | 타입 | 국가 | URL |
|--------|------|------|-----|
| Stone Island | brand-store | IT | https://www.stoneisland.com |
| VINAVAST | edit-shop | HK | https://www.vinavast.co |
| The Trilogy Tapes | brand-store | UK | https://www.thetrilogytapes.com |
| Goldwin | brand-store | JP | https://www.goldwin-global.com |

**조사 항목:** Shopify 여부, 스토어 상태, 플랫폼

---

## 공통 조사 방법

### Shopify 여부 확인
```
[채널URL]/products.json?limit=5
→ 200 응답 + JSON이면 Shopify
→ 404/redirect이면 Shopify 아님 또는 보안 설정
```

### Cafe24 여부 확인 (한국 쇼핑몰)
```
[채널URL]/product/list.html?cate_no=1
→ 200이면 Cafe24 가능성 높음
또는 페이지 소스에서 "cafe24" 문자열 확인
```

### Route 앱 설치 여부
```
1. 스토어 카트 페이지 접속
2. "Route Protection" 또는 "Package Protection" 항목 확인
3. 체크아웃 페이지에서 Route 위젯 확인
```

### 채널 상태 확인
```
1. 메인 URL 접속 → HTTP 200 / 301 / 404 / 503
2. Google 검색: "[채널명] site:[도메인]"
3. Instagram/SNS에서 최근 업데이트 확인
```

---

## 기대 산출물

아래 형식으로 조사 결과를 정리해주세요:

```markdown
## [채널명]
- URL: https://...
- 상태: 정상 운영 / 폐쇄 / 도메인 변경 / 기타
- 플랫폼: Shopify / Cafe24 / stores.jp / 기타
- /products.json 접근: 가능 / 불가
- Route 앱: 사용 중 / 미사용 / 확인 불가 (그룹 A만)
- 비패션 제품: Route protection 등 X개 발견 / 없음 (그룹 A만)
- 주력 취급: [브랜드/카테고리 간략 설명]
- 권고 조치: 정상 크롤 / 채널 비활성화 / URL 업데이트 / 플랫폼 지원 추가 필요
- 메모: (기타 특이사항)
```

---

## 우선순위

1. **그룹 A** (3개): Route 필터 코드픽스(T-054)로 해결되나, 채널 자체 재분류 여부 확인
2. **그룹 B-1** (12개): 고가치 글로벌 채널 — Shopify이면 즉시 크롤 가능
3. **그룹 B-2** (15개): JP 비표준 플랫폼 — 플랫폼별 크롤러 지원 여부 결정
4. **그룹 B-3 우선** (9개): KR 유명 채널 — Cafe24/Shopify 확인 후 크롤
5. **그룹 B-3 나머지 + B-4**: 순차 확인

---

## 참고: 크롤러 현재 지원 플랫폼

| 플랫폼 | 방식 | 상태 |
|--------|------|------|
| Shopify | `/products.json?limit=250&page={n}` | ✅ 지원 |
| Cafe24 | HTML 파싱 `/category/{cate_no}` | ✅ 지원 |
| stores.jp / buyshop.jp / theshop.jp | 미지원 | ❌ 추가 개발 필요 |
| MakeShop (shop-pro.jp) | 미지원 | ❌ 추가 개발 필요 |
| ocnk.net | 미지원 | ❌ 추가 개발 필요 |

**필터 현황**: 가격 > 0 체크만, vendor/title/product_type 필터 없음
→ T-20260301-054 (PRODUCT_DENYLIST_01) 과업지시 완료 / Codex 구현 예정
