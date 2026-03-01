# Fashion Data Engine — Plan

> 이 파일은 계획 문서입니다.
> - Claude가 계획을 작성하고 업데이트합니다.
> - **승인 전까지 구현하지 않습니다.**
> - 승인 후 Codex가 GitHub 이슈로 구현합니다.
>
> **사용법**: 각 항목에 주석(→ 코멘트)을 달아주세요. Claude가 반영합니다.

---

## 현재 상황 요약 (문제 진단)

### 왜 데이터 품질이 낮은가?

현재 크롤링은 **Shopify 기반 채널만** 작동합니다.
`product_crawler.py`는 Shopify의 공개 API(`/products.json`)만 지원하도록 설계됐기 때문입니다.

```
채널 전체: 159개
  └─ brand-store (단일 브랜드 공식몰): 75개
       └─ 크롤 완료: 35개 ✅
       └─ 미크롤: 40개 (대부분 Shopify → 크롤 가능, 아직 미실행)
  └─ edit-shop (편집숍): 80개
       └─ 크롤 완료: 0개 ❌
       └─ 이유: 편집숍은 Shopify가 아닌 것도 많음

나머지 (백화점·마켓플레이스 등): 이 계획에서 제외
```

### 편집숍 플랫폼 분류 (핵심 과제)

편집숍 80개를 플랫폼별로 나누면 대략 3가지 유형입니다:

| 유형 | 특징 | 난이도 | 예시 |
|------|------|--------|------|
| **A. Shopify 편집숍** | `/products.json` API 자동 지원 | 쉬움 ✅ | bdgastore, sevenstore, DSM, Goodhood, HBX |
| **B. Cafe24 편집숍** | 한국 쇼핑몰 솔루션. 브랜드별 `cate_no` 파라미터로 분류 | 중간 🔶 | 8division, kasina, thexshop, unipair, 무신사일부 |
| **C. 완전 커스텀** | 자체 플랫폼. 별도 API나 heavy 스크래핑 필요 | 어려움 ❌ | 무신사, 29CM, W컨셉, LF몰 |

**현재 코드 상태:**
- `brand_crawler.py`: Shopify + Cafe24 + 일부 커스텀 → 브랜드 목록 수집은 됨
- `product_crawler.py`: **Shopify 전용** → Cafe24/커스텀 채널은 제품 수집 자체가 안 됨

---

## 계획 범위

**이 계획에서 다루는 것:**
- brand-store (단일 브랜드 공식몰) 전체 크롤 완성
- edit-shop 중 Shopify 기반 채널 제품 크롤
- edit-shop 중 Cafe24 기반 채널 제품 크롤 (신규 개발)
- 자동 크롤 스케줄 (Railway Worker 설정)

**이 계획에서 다루지 않는 것:**
- 완전 커스텀 플랫폼 (무신사, 29CM, W컨셉) — 추후 별도 계획
- 백화점, 마켓플레이스, 중고거래 — 추후 추가 예정
- 신규 기능 개발 (알람, 구매이력, 협업 등)

---

## Plan A — brand-store 크롤 완성

### 목표
나머지 40개 brand-store 채널 크롤 완료.
이미 크롤러가 다 만들어져 있으므로 **실행만 하면 됨.**

### 작업 내용

**A-1. 미크롤 brand-store 채널 목록 파악 및 크롤 실행**

현재 35개는 완료. 나머지 40개를 크롤하면 약 +10,000~20,000개 제품 추가 예상.

```bash
# 실행 방법 (현재도 가능, Railway에서도 가능)
make crawl                         # 전체 brand-store
# 또는 Railway에서:
DATABASE_URL="postgresql+asyncpg://..." uv run python scripts/crawl_products.py --channel-type brand-store
```

**A-2. 크롤 실패 채널 파악**

일부 brand-store는 Shopify가 아닌 경우도 있음.
크롤 실행 후 로그에서 "No products found" 채널 목록 확인 → 수동 검토.

### 예상 결과
- 크롤된 brand-store: 35개 → 75개 (100%)
- 신규 제품: 약 +10,000~20,000개

### 우선순위: **즉시 실행 가능** (코드 수정 없음)

---

## Plan B — edit-shop Shopify 채널 제품 크롤

### 목표
편집숍 중 Shopify 기반 채널의 제품을 수집.
`product_crawler.py`가 이미 처리 가능하므로 **채널 분류만 하면 됨.**

### 배경 설명

**편집숍(edit-shop)이 Shopify를 쓰는지 어떻게 아나?**

가장 간단한 방법:
```
GET https://{채널URL}/products.json?limit=1
→ 200 응답 + JSON이면 Shopify
→ 404 또는 HTML이면 비-Shopify
```

현재 `product_crawler.py`의 `crawl_channel()`이 이 방식으로 자동 감지함.
즉, Shopify가 아니면 그냥 "No products found"로 건너뜀.

### 작업 내용

**B-1. (Codex) edit-shop 채널에 Shopify 플랫폼 감지 + 크롤 지원**

현재 `crawl_products.py`는 `SKIP_TYPES = {"secondhand-marketplace", "non-fashion"}`을 제외한 모든 채널을 크롤 시도함.
즉, `--channel-type edit-shop` 플래그를 주면 이미 Shopify 편집숍은 크롤됨.

확인 사항:
- `channels` 테이블에 `platform` 컬럼이 없음 → Shopify 여부를 DB에 기록하지 않음
- 크롤 시도 후 실패 로그를 분석하는 도구가 없음

**B-2. (Codex) `channels` 테이블에 `platform` 컬럼 추가**

```python
# 추가할 컬럼
platform: Mapped[str | None]
# 값: "shopify" | "cafe24" | "custom" | None (미분류)
```

**자동 감지 로직 (crawl 시):**
- `GET /products.json` 성공 → platform = "shopify"
- `GET /product/list.html?cate_no=` 패턴 → platform = "cafe24"
- 둘 다 실패 → platform = "custom"

이 정보가 있어야:
- Admin 페이지에서 채널별 플랫폼 확인 가능
- 크롤 전략을 명확히 분기할 수 있음

**B-3. (중요) Shopify 편집숍도 normalized_key 필요**

현재 `product_key = "{brand_slug}:{handle}"` 구조의 문제:

```
bdgastore에서 2002R 크롤:  vendor="New Balance", handle="nb-2002r-mushroom"
Goodhood에서 2002R 크롤:   vendor="New Balance", handle="new-balance-m2002rca"
→ product_key 달라짐 → 같은 제품인데 교차 비교 불가 ❌
```

`handle`은 각 쇼핑몰이 독립적으로 붙인 URL slug → Shopify끼리도 다를 수 있음.

따라서 **Shopify 편집숍도 Plan C의 normalized_key 전략을 동일하게 적용해야 함**.

다만 Shopify는 Cafe24보다 데이터가 풍부하므로 추가로 활용 가능한 필드가 있음:

**현재 이미 수집하는 필드 중 아직 안 쓰는 것:**
```python
# product_crawler.py _parse_product() 참고
sku   → vendor의 공식 스타일 코드가 들어있는 경우 많음 (예: "M2002RCA")
tags  → 모델코드·컬러웨이·시즌 정보 포함 (예: ["M2002R", "Mushroom", "FW23"])
       현재는 gender/subcategory 분류에만 씀 → normalized_key 생성에도 활용 가능
```

**B-3 추가 작업 (Codex)**:
- `_parse_product()`: SKU 필드에서 공식 스타일 코드 패턴 감지 → normalized_key 1순위
- `_parse_product()`: tags에서 모델코드 추출 → normalized_key 2순위 보조 재료
- 나머지는 Plan C의 레퍼런스 매칭 + 정규식 fallback 공유

### 예상 결과
- Shopify 편집숍: 약 20~30개 (80개 중 추정)
- 신규 제품: 약 +15,000~30,000개 (편집숍은 제품 수가 많음)
- normalized_key 적용 시 Shopify ↔ Shopify 교차 비교도 가능

### 우선순위: **높음** (코드 최소 변경)

---

## Plan C — edit-shop Cafe24 채널 제품 크롤 (핵심 신규 개발)

### 목표
Cafe24 기반 편집숍의 제품을 수집.
**현재 제품 크롤러가 Cafe24를 전혀 지원하지 않음 → 신규 개발 필요.**

### 배경 설명: Cafe24가 무엇인가?

Cafe24는 한국 기반 이커머스 플랫폼으로, 많은 국내 편집숍이 사용합니다.
URL 구조 예시:
```
브랜드 목록 페이지: /product/maker.html
브랜드별 제품 목록: /product/list.html?cate_no=123&page=1
제품 상세:         /product/상품명/456/category/123/
```

**Shopify vs Cafe24 제품 크롤 비교:**

| 항목 | Shopify | Cafe24 |
|------|---------|--------|
| API 방식 | REST JSON (`/products.json`) | HTML 파싱 (페이지 스크래핑) |
| 페이지 접근 | httpx (빠름) | httpx 또는 Playwright |
| 브랜드 구분 | vendor 필드 | cate_no (카테고리 번호) |
| 표준화 | 매우 표준화됨 | 쇼핑몰마다 HTML 구조 약간 다름 |

### 작업 내용

**C-1. (Codex) `product_crawler.py`에 Cafe24 크롤 전략 추가**

```python
# 추가할 메서드 (product_crawler.py)
async def _try_cafe24_products(
    self, channel_url: str, cate_no: int, brand_name: str
) -> list[ProductInfo]:
    """
    Cafe24 브랜드 카테고리에서 제품 목록 수집.

    /product/list.html?cate_no={cate_no}&page=N 순회
    → 제품 카드 HTML 파싱:
        - 제품명 (.prdList .description h3 등)
        - 가격 (.price 등)
        - 이미지 URL
        - 제품 상세 URL (/product/XXX/product_no=YYY)
    """
```

필요한 파싱 항목:
```
제품명      → Product.name
가격        → PriceHistory.price (항상 KRW)
정가        → PriceHistory.original_price
이미지 URL  → Product.image_url
제품 URL    → Product.url
brand_name  → vendor로 사용 → product_key 생성
product_no  → handle로 사용 (Shopify의 handle과 동일 역할)
```

**product_key 생성 (Cafe24) — 2단계 키 전략:**

Cafe24는 `product_no`라는 숫자 ID를 씁니다. 이 숫자는 각 쇼핑몰이 독립 발급하므로, Shopify의 `handle`처럼 교차채널 식별자로 쓸 수 없습니다.

```
8division의 2002R:  product_no = 12345  (8division 내부 번호)
kasina의 2002R:     product_no = 67890  (kasina 내부 번호)
→ 숫자가 달라 같은 제품인지 알 수 없음
```

**해결책: `product_key`와 `normalized_key` 분리**

| 컬럼 | 역할 | 예시 |
|------|------|------|
| `product_key` | 채널 내 고유 식별 (기존) | `new-balance:12345` |
| `normalized_key` | 교차채널 매칭용 (신규) | `new-balance:m2002r` |

`normalized_key`는 크롤 후 **제품명에서 모델코드를 추출**해 생성합니다:

```python
# 우선순위 순서로 normalized_key 생성
# 1순위: SKU가 있으면 → "{brand_slug}:{sku}"
#   → "new-balance:mr2002rca"  (브랜드 공식 코드, 채널 무관하게 동일)

# 2순위: 제품명에서 모델코드 추출 → "{brand_slug}:{model_code}"
#   "New Balance M2002RCA Mushroom"  →  "new-balance:m2002r"
#   "NB 2002R 머쉬룸"                →  "new-balance:m2002r"
#   "2002R"                          →  "new-balance:m2002r"

# 3순위: 제품명 전체 정규화 → "{brand_slug}:{title_slug}"
#   "Air Force 1 Low White"  →  "nike:air-force-1-low"
```

**모델코드 추출 원리**: 패션 제품의 모델코드는 거의 항상 `영문+숫자 조합` 패턴입니다.
정규식으로 추출하면 대부분의 주요 제품 커버 가능:
```
M2002R, M990V6, U9060  (New Balance)
AF1, AM90, AJ1         (Nike)
YZY350, NMD_R1         (Adidas)
```

**정확도 예상**: SKU 매칭 ~30% + 모델코드 추출 ~50% + 제목 정규화 ~20% → **전체 80~90% 커버**

---

**레퍼런스 기반 매칭 (3단계 개선안)**

> 아이디어 출처: 편집숍 제품명은 대부분 공식 브랜드몰의 제품명을 그대로 따라갑니다.
> 따라서 **공식몰 제품 목록을 기준 카탈로그로 활용**하면 더 높은 정확도의 매칭이 가능합니다.

**전제 조건**: Plan A (brand-store 전체 크롤) 완료 후 사용 가능.

**매칭 순서 (정확도 높은 순)**:

| 단계 | 방법 | 정확도 | 설명 |
|------|------|--------|------|
| 1단계 | SKU 직접 매칭 | ~100% | Cafe24 제품에 SKU가 있으면 공식몰 SKU와 비교 → 일치 시 normalized_key 상속 |
| 2단계 | 레퍼런스 이름 매칭 | ~85% | 같은 브랜드의 공식몰 제품명과 토큰 유사도 비교 → 임계값(0.75) 초과 시 normalized_key 상속 |
| 3단계 | 모델코드 정규식 추출 | ~50% | 공식몰 레퍼런스 없을 때 → 제품명에서 영문+숫자 패턴 추출해 자체 생성 (fallback) |

**2단계 예시 (레퍼런스 이름 매칭)**:
```
공식몰(Patta KR)에 "New Balance M2002RCA" 있음 → normalized_key = "new-balance:m2002r"
8division에서 "뉴발란스 2002R 머쉬룸" 크롤
 → 브랜드: New Balance (일치)
 → 제품명 토큰 유사도: ["2002R"] 매칭 → 유사도 0.82 > 0.75
 → normalized_key = "new-balance:m2002r" 상속 ✅
```

**3단계 예시 (fallback)**:
```
공식몰에 해당 제품 없음 (신규 편집숍 한정 제품)
 → 제품명 "Air Max 97 Silver Bullet"에서 정규식으로 "air-max-97" 추출
 → normalized_key = "nike:air-max-97" 자체 생성
```

**왜 이 방식이 더 좋은가**:
- 모델코드만 추출하면 동일 모델의 컬러웨이/사이즈 변형을 구분 못 함
- 공식몰 레퍼런스가 있으면 컬러웨이까지 포함한 정확한 매칭 가능
- 비영어권(한국어 제품명)에서도 공식몰과 토큰을 비교하면 더 잘 매칭됨

**구현 라이브러리**: `rapidfuzz` (빠른 퍼지 문자열 매칭, Python 표준 `difflib`보다 약 10배 빠름)


---

**가격 비교 쿼리 변경:**
```sql
-- 기존 (Shopify끼리만 비교 가능)
WHERE product_key = "new-balance:new-balance-2002r"

-- 변경 후 (Cafe24 포함 교차채널 비교)
WHERE normalized_key = "new-balance:m2002r"
```

**C-4. (Codex) `products` 테이블에 `normalized_key` 컬럼 추가**

```python
# Product 모델에 추가
normalized_key: Mapped[str | None] = mapped_column(
    String(300), nullable=True, index=True
)
```

- 크롤 시 자동 생성 (Shopify 제품도 소급 적용)
- Alembic migration 필요
- 기존 `/products/compare/{product_key}` 엔드포인트: `normalized_key`도 검색 대상에 추가

**C-2. (Codex) `scripts/crawl_products.py`에 Cafe24 채널 처리 추가**

```python
# 기존 흐름 (Shopify만):
result = await crawler.crawl_channel(channel_url, country)

# 변경 후 (플랫폼 분기):
if channel.platform == "cafe24":
    brand_cate_map = get_cafe24_brand_cate_map(channel)  # brand_crawler로 이미 수집된 cate_no 매핑 활용
    result = await crawler.crawl_cafe24_channel(channel_url, brand_cate_map)
else:
    result = await crawler.crawl_channel(channel_url, country)  # 기존 Shopify 방식
```

**C-3. Cafe24 cate_no 매핑 활용**

brand_crawler.py는 이미 Cafe24의 브랜드 목록 페이지에서 `cate_no`를 수집합니다.
이 정보를 channel_brands 테이블에 저장하면, 제품 크롤 시 재활용할 수 있습니다.

```python
# channel_brands 테이블에 추가할 컬럼
cate_no: Mapped[int | None]  # Cafe24 전용, 브랜드 카테고리 번호
```

### C-5. 리서치 인사이트: 업계 사례에서 배운 것

> 가격비교 플랫폼(PriceRunner, Google Shopping)과 패션 애그리게이터(Lyst, FARFETCH),
> 스니커즈 리세일(StockX, Kream)의 실제 구현 사례 조사 결과.

**인사이트 1: 블로킹 전략 (필수)**

퍼지 매칭을 모든 제품에 적용하면 느립니다. 먼저 범위를 줄여야 합니다:
```
1. 브랜드 일치 (필수)  → 검색 범위 50배 축소
2. 가격 ±30% 이내      → 명백한 이상값 제외
3. 카테고리 일치       → 신발 ≠ 의류 분리
```

**인사이트 2: Token Sort Ratio — 패션 제품명에 더 적합**

기본 유사도 측정은 단어 순서 차이에 취약합니다:
```
"Air Max 97 Black"  vs  "Black Air Max 97"
→ 기본 유사도: 낮은 점수 ❌  (같은 제품인데)
→ Token Sort Ratio: 1.0 ✅  (단어 정렬 후 비교)
```
한국어 편집숍 특히 중요: "2002R 뉴발란스" vs "New Balance M2002R"
→ 영문 정규화 후 Token Sort Ratio 사용 권장 (`rapidfuzz.process.token_sort_ratio`).

**인사이트 3: 신뢰도 구간 + 관리자 검토 큐**

매칭 결과를 3구간으로 분류하는 것이 업계 표준입니다:

| 신뢰도 | 처리 | 예상 비율 |
|--------|------|----------|
| 0.90+ | 자동 적용 | ~70% |
| 0.75~0.90 | Admin 검토 큐 | ~20% |
| 0.75 미만 | 미매칭 처리 | ~10% |

→ `normalized_key` 저장 시 `match_confidence: float` 컬럼도 함께 저장.
→ Admin 페이지에 "매칭 검토" 탭 추가 필요 (Codex 이슈로 등록 예정).

**인사이트 4: 공식 스타일 코드 활용 (SKU에 숨어있음)**

많은 브랜드가 SKU 필드에 공식 코드를 넣습니다:
```
Nike:        DD9336-641   (앞 6자리=모델, 뒤 3자리=컬러웨이)
Adidas:      GZ6094       (10자리 영숫자, 컬러 포함)
New Balance: M2002RCA     (모델+컬러 통합 코드)
```
현재 Shopify 크롤 시 `sku` 필드 이미 수집 중 → 정규식으로 패턴 감지 후 `normalized_key` 1순위 재료로 활용.

**인사이트 5: 재출시 제품 주의 (연도 다름 = 다른 제품)**

StockX/Kream의 중요한 교훈:
```
"Air Jordan 1 Chicago" (2015 출시) ≠ "Air Jordan 1 Chicago" (2022 재출시)
→ 같은 이름인데 다른 제품 (중고 가격 2배 차이)
```
→ `normalized_key`에 출시 연도 포함 방안 검토 (단, 연도 확인 어려운 일반 제품은 미적용).
(출시연도가 중요한 경우는 한정판 제품 특히 스니커즈가 중요해. 다만, 우리는 새제품 그리고 리셀 가능한 한정판이 주요 타겟이 아니어서 재출시 제품에 대한 것은 고려하지 않음)

**인사이트 6: 한국어 브랜드명 정규화 선행 필수**

Cafe24 편집숍 제품명 예시:
```
"나이키" → "Nike"  /  "뉴발란스" → "New Balance"  /  "아디다스" → "Adidas"
```
→ 브랜드명 한→영 매핑 테이블 별도 관리. `brands` 테이블에 `name_ko` 컬럼 추가 검토.

**인사이트 7: 이미지 유사도 (장기 옵션)**

텍스트 매칭이 실패하는 케이스(브랜드명 없는 제품 등)를 위해:
- `CLIP` 모델 (오픈소스) — 이미지 벡터화 유사도 비교
- 크롤 시 이미지 URL 이미 수집 중 → 나중에 추가 가능
- 도입 시점: 전체 제품 10,000개+ 이후 (MVP에서는 불필요)

---

### 예상 결과
- Cafe24 편집숍: 약 30~40개
- 신규 제품: 약 +30,000~60,000개 (국내 편집숍은 수천 개 제품 보유)

### 우선순위: **중간** (신규 크롤러 개발 필요, 상당한 작업)

---

## Plan D — 자동 크롤 스케줄 (Railway Worker)

### 목표
크롤/환율업데이트/감사가 자동으로 실행되도록 Railway에 스케줄러 Worker 설정.

### 배경 설명: 왜 지금 자동으로 안 도는가?

현재 Railway에는 **API 서버 1개만** 배포됨:
```
Railway 프로젝트
  └─ API 서비스 (uvicorn) ← 지금 배포됨
  └─ Worker 서비스 (scheduler.py) ← 미설정 ❌
```

`scripts/scheduler.py`는 이미 완성되어 있으나, Railway에서 실행할 서비스가 없음.
결과: 환율, 크롤, 감사 모두 수동으로 로컬에서 실행해야 함.

### 크롤 주기 계획

크롤 주기를 얼마나 자주 할지는 **신선도 vs 서버 부하 vs 크롤 시간** 의 균형입니다.

| 작업 | 현재 | 제안 주기 | 이유 |
|------|------|----------|------|
| brand-store 제품 크롤 | 수동 | **매일 03:00** | 세일/신상품 하루 단위로 변함 |
| edit-shop Shopify 크롤 | 미구현 | **매일 04:00** | brand-store 완료 후 연속 실행 |
| edit-shop Cafe24 크롤 | 미구현 | **매일 05:00** | 더 느리므로 별도 시간대 |
| 환율 업데이트 | 수동 | **매일 07:00** | 환율은 하루 1회면 충분 |
| 드롭 감지 | 수동 | **매일 07:10** | 신제품 빠른 감지 |
| 뉴스 수집 | 수동 | **매일 08:00** | 하루 1회 충분 |
| 데이터 감사 | 수동 | **매주 일요일 09:00** | 주 1회 품질 체크 |

**총 크롤 시간 추정 (전체 채널 크롤 완성 후):**
- brand-store 75채널 × 채널당 약 2분 = 약 2.5시간
- Shopify 편집숍 ~25채널 × 채널당 약 3분 = 약 1.25시간
- Cafe24 편집숍 ~35채널 × 채널당 약 10분 = 약 6시간
- **총: 약 10시간**

→ 매일 03:00 시작하면 13:00~14:00에 완료. 충분한 여유.

### 작업 내용

**D-1. Railway Worker 서비스 추가 (사용자가 직접 해야 함)**

코드는 이미 완성됨(`scripts/scheduler.py`). Railway 콘솔에서 설정만 하면 됨:

```
Railway 대시보드 → 프로젝트 → + New Service → GitHub 레포
Start Command: uv run python scripts/scheduler.py
환경변수: API 서비스와 동일하게 DATABASE_URL, DISCORD_WEBHOOK_URL 등 복사
```

**D-2. (Codex) scheduler.py에 Cafe24 크롤 Job 추가**

Plan C 완료 후, scheduler.py에 Cafe24 채널 크롤 job 추가:

```python
# 추가 (scripts/scheduler.py)
scheduler.add_job(
    crawl_cafe24_job,
    CronTrigger(hour=5, minute=0, timezone="Asia/Seoul"),
    id="cafe24_crawl_daily",
    name="Cafe24 편집숍 제품 크롤",
)
```

**D-3. (Codex) 크롤 실패 채널 자동 재시도 로직**

현재 크롤 실패 시 그냥 넘어감.
실패 채널을 기록하고, 다음 날 자동 재시도하는 로직 추가.

```python
# channels 테이블에 추가
last_crawl_error: Mapped[str | None]  # 마지막 크롤 에러 메시지
crawl_fail_count: Mapped[int] = mapped_column(default=0)  # 연속 실패 횟수
```

### 우선순위: **높음** (스케줄러 코드는 이미 있음, Railway 설정만 하면 됨)

---

## 실행 순서 (권장)

```
즉시 (코드 수정 없음):
  └─ Plan A: brand-store 40개 크롤 실행
  └─ Plan D-1: Railway Worker 설정

단기 (Codex 구현):
  └─ Plan B: edit-shop Shopify 분류 + platform 컬럼 + 크롤
  └─ Plan D-2/3: 스케줄러 job 추가

중기 (Codex 구현):
  └─ Plan C: Cafe24 제품 크롤러 개발
```

---

## 완료 기준 (DoD)

| Plan | 완료 조건 |
|------|----------|
| A | brand-store 75개 중 크롤 성공 채널 60개+ |
| B | Shopify 편집숍 platform="shopify" 분류 완료, 제품 수집 |
| C | Cafe24 채널 최소 5개 이상 제품 정상 수집 |
| D | Railway Worker 배포 후 익일 크롤 로그 자동 생성 확인 |

---

## 데이터 품질 지표 (크롤 완성 후 목표치)

| 지표 | 현재 | 목표 |
|------|------|------|
| 크롤된 채널 수 | 35/159 (22%) | 100/159 (63%) |
| 총 제품 수 (Railway) | 12,733 | 80,000+ |
| brand_id NULL 비율 | 41% | 20% 이하 |
| 자동 크롤 여부 | ❌ 수동 | ✅ 자동 (Railway Worker) |

---

*최종 업데이트: 2026-03-01*
*다음 업데이트: 검토 주석 반영 시*
