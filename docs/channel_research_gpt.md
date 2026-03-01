# 채널 리서치 의뢰서 — GPT Pro용
> 작성일: 2026-03-01 | 담당: Claude PM → GPT Pro 조사 의뢰

---

## 배경 및 목적

Fashion Data Engine은 Shopify/Cafe24 기반 패션 편집샵과 브랜드 스토어의 제품·가격 데이터를 수집합니다.
현재 두 가지 문제가 발견되어, 아래 채널들의 실태를 정확히 파악해야 합니다.

**문제 1: Route 배송보험 제품 오인덱싱**
Shopify 스토어에 설치된 Route Package Protection 앱이 `/products.json` API에 일반 제품처럼 노출됩니다.
크롤러가 이를 패션 제품으로 오인식하여 DB에 저장하고 있습니다.
- 예시: "Shipping Protection by Route" (vendor: route, ₩1,398~₩1,400)
- 영향 채널: The Loop Running Supply, 18 East, Velour Garments (스크린샷 확인)

**문제 2: 크롤 불가 채널 파악 필요**
78개 채널이 제품 0개 상태입니다. 웹사이트 구조 변경, 도메인 이전, 폐쇄 등의 원인이 있을 수 있습니다.
이 중 패션 편집샵(edit-shop)과 브랜드스토어(brand-store)를 우선 조사합니다.

---

## 조사 채널 목록

### 그룹 A: Route 배송보험 문제 확인된 채널 (3개)

| 채널명 | 타입 | 국가 | URL (추정) | 문제 |
|--------|------|------|-----------|------|
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

### 그룹 B: 크롤 실패 / 제품 0개 의심 채널 (주요 후보)

> **참고**: 아래는 크롤 이력 없거나 제품 0개인 채널 중 패션 관련성이 높은 것들입니다.
> T-20260301-055 구현 완료 후, 트래픽 라이트 🔴(red) 채널 목록으로 업데이트 예정.

| 채널명 | 타입 | 국가 | 예상 문제 |
|--------|------|------|----------|
| (T-055 구현 후 트래픽 라이트 🔴 채널로 채움) | - | - | - |

**조사 항목 (그룹 B 각 채널):**
1. 도메인/URL 현재 유효 여부 (HTTP 상태 코드)
2. Shopify 플랫폼 여부 (`/products.json` 접근 가능 여부)
3. Cafe24 플랫폼 여부 (한국 쇼핑몰인 경우)
4. 사이트 이전/리뉴얼 여부 (최근 공지, SNS 확인)
5. 현재 폐쇄되었는지, 도메인만 바뀌었는지 여부

---

## 공통 조사 방법

각 채널에 대해 다음 방법으로 조사하세요:

### Shopify 여부 확인
```
[채널URL]/products.json?limit=5
→ 200 응답 + JSON이면 Shopify
→ 404/redirect이면 Shopify 아님 또는 보안 설정
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
- 플랫폼: Shopify / Cafe24 / 기타
- /products.json 접근: 가능 / 불가
- Route 앱: 사용 중 / 미사용 / 확인 불가
- 비패션 제품: Route protection 등 X개 발견 / 없음
- 주력 취급: [브랜드/카테고리 간략 설명]
- 권고 조치: 정상 유지 / 채널 비활성화 / URL 업데이트 / 필터 추가
- 메모: (기타 특이사항)
```

---

## 우선순위

1. **즉시 처리**: 그룹 A 3개 채널 (Route 문제 → 코드 필터 추가로 해결 가능하나, 채널 자체 재분류 필요 여부 확인)
2. **T-055 구현 후**: 그룹 B 확장 (트래픽 라이트 🔴 채널 목록)

---

## 참고: 크롤러 현재 처리 방식

- **Shopify**: `[URL]/products.json?limit=250&page={n}` 순차 페이지네이션
- **Cafe24**: HTML 파싱 (`/category/{cate_no}`)
- **필터 현황**: 가격 > 0 체크만, vendor/title/product_type 필터 없음 (T-054로 해결 예정)
- **제품 저장**: `product_key = "{vendor_slug}:{handle}"` 형식으로 교차채널 매칭
