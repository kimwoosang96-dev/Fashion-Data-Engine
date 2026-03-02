# 채널 리서치 결과 및 DB 구조 개선 제안
- 작성일: 2026-03-01 (Asia/Seoul)
- 대상: Fashion Data Engine (Shopify/Cafe24 크롤러 기반)
- 입력 문서: `channel_research_gpt.md` / `research.md`

---

## 0. Executive Summary

### 문제 1) Route 배송보험 제품 오인덱싱
- 원인: Shopify의 **closed-cart** 특성 때문에 Route(배송보험)가 **실제 “상품(Product)”으로 생성/노출**되는 구조.
- 영향: `/products.json` 기반 크롤러가 이를 “패션 상품”으로 오인하여 DB 저장 → 검색/추천/세일탐지 품질 저하.
- 권장 조치:
  1) **크롤 단계에서 vendor/title/product_type/handle/tag 기반 denylist**로 Route 상품 배제  
  2) 이미 적재된 데이터는 **후처리(soft delete 또는 분리 테이블로 이동)**  
  3) (선택) 머천트 측에서 **컬렉션/상품목록에서 Route 상품 숨김 처리** 가능

### 문제 2) 제품 0개 + 크롤 이력 never 채널 다수
- 관찰(의뢰서 기준): edit-shop + brand-store 중 “제품 0개 & 크롤 never” 채널이 다수 존재.
- 가장 가능성이 큰 원인 Top 3:
  1) **플랫폼 미지원/미감지** (Shopify/Cafe24가 아니어서 스케줄러 대상에서 제외)
  2) **URL 변경/리다이렉트/오입력** (DB URL이 더 이상 스토어가 아님)
  3) **봇 차단/지역 리다이렉트/자바스크립트 렌더링 의존**으로 수집 실패  
- 권장 조치:
  - 채널 생성/수정 시 **플랫폼 자동감지 + URL 정규화**를 강제하고,
  - **channels.platform NULL/unknown을 주기적으로 스캔하여 자동 분류**,
  - 미지원 플랫폼은 `active=false`로 운영(또는 신규 크롤러 backlog로 전환).

---

## 1. Route Package Protection 오인덱싱 — 원인과 해결

### 1.1 왜 Route가 “상품”으로 보이는가?
Route 머천트 문서에 따르면, Shopify의 closed-cart 시스템 때문에 Route Package Protection이 **스토어의 실제 상품으로 등록**되어 총 카트 금액에 포함될 수 있도록 구성됩니다.

### 1.2 머천트(스토어 운영자) 레벨에서 숨기는 방법(옵션)
Route 가이드는 **Route 상품을 모든 컬렉션에서 제외**하여 상품 목록에 노출되지 않게 숨기는 방식을 안내합니다.

> 참고: Route는 2023년경 업데이트로 “카트의 라인아이템(line item)으로 보이지 않게” 변경되었지만, 여전히 백엔드(상품/보험료 계산) 관점에서는 상품으로 존재할 수 있습니다.

### 1.3 크롤러/인덱서 레벨에서의 권장 픽스(필수)
의뢰서에 적힌 것처럼 denylist(차단 리스트) 기준을 추가하는 것이 가장 안전합니다.

**권장 denylist 시그널**
- vendor: `route`, `routeapp`, `Route`
- title: `Shipping Protection`, `Package Protection`, `Route Package Protection` 포함
- product_type: `Shipping Protection`, `Insurance` 유사
- tags/handle: `route` 포함
- 가격대가 매우 낮고(예: 0~몇천원), 옵션만 여러 개인 보험형 디지털 상품 패턴

**데이터 정리(이미 들어간 Route 상품)**
- 1차: products 테이블에서 `vendor ILIKE '%route%'` 또는 title 패턴 매칭으로 soft-delete/archived 처리
- 2차: price_history도 동일 product_id 기준으로 제거/분리

---

## 2. URL/플랫폼 확인 결과 (검증된 항목 위주)

> 아래는 “웹에서 확인된/근거가 확보된” 항목만 우선 정리했습니다.  
> 나머지 채널은 **부록의 자동 진단 스크립트**로 일괄 판별하는 것을 권장합니다(67개 전체를 사람 손으로 브라우징하면 누락/오판 위험이 큼).

| 그룹   | 채널                                  | DB_URL                              | 확인_URL                                                    | 플랫폼                              | 근거                                                                   | 액션                                                                                 |
|:-------|:--------------------------------------|:------------------------------------|:------------------------------------------------------------|:------------------------------------|:-----------------------------------------------------------------------|:-------------------------------------------------------------------------------------|
| A      | The Loop Running Supply               | thelooprunningsupply.com            | https://thelooprunning.com                                  | Shopify (확인)                      | 사이트 하단 'Powered by Shopify' 확인                                  | 채널 URL 최신화(리다이렉트/도메인 변경 여부 확인) + Route 제품 필터링 적용 후 재크롤 |
| A      | 18 East                               | 18east.com                          | https://18east.co (공식 스토어)                             | Shopify (추정)                      | 18east.com은 리테일 스토어가 아닌 다른 사이트로 노출                   | 채널 URL 교체 후 플랫폼 재감지/재크롤                                                |
| A      | Velour Garments                       | velourgarments.com                  | https://velourgarments.eu                                   | Shopify (확인: BuiltWith/AfterShip) | BuiltWith/AfterShip에서 Shopify 플랫폼으로 식별                        | 채널 URL 최신화(공식 스토어 도메인) + Route 제품 필터링 적용 후 재크롤               |
| B-1    | Bodega                                | https://bdgastore.com               | https://bdgastore.com                                       | Shopify (추정~확인)                 | myshopify 도메인/Shopify로 식별되는 정보 다수                          | platform=shopify로 세팅 후 크롤                                                      |
| B-1    | Warren Lotas                          | https://www.warrenlotas.com         | https://www.warrenlotas.com                                 | Shopify (확인)                      | 약관에 'Our store is hosted on Shopify Inc.' 명시                      | platform=shopify로 세팅 후 크롤                                                      |
| B-1    | Joe Freshgoods                        | https://www.joefreshgoods.com       | https://joefreshgoods.com                                   | Shopify (추정)                      | /collections 경로 및 전형적인 Shopify 스토어 정보구조(Shop/Terms) 확인 | platform 자동감지 로직으로 확정 후 크롤                                              |
| B-1    | Dover Street Market (store/brandshop) | https://store.doverstreetmarket.com | https://shop.doverstreetmarket.com (지역별 서브도메인 존재) | 비-Shopify 가능성 높음 (확인 필요)  | 페이지 HTML에서 Shopify 표식(Shopify/cdn.shopify/myshopify) 미검출     | 현 크롤러(Shopify/Cafe24) 지원범위 밖이면 비활성화 또는 신규 크롤러 설계             |

---

## 3. 제품 0개 + never 크롤 채널 — 원인 분류 프레임

> 이 파트는 “왜 never인지”를 **운영/데이터 관점에서 빠르게 좁히는 방법**입니다.  
> (의뢰서의 67개 채널 전체에 대해 동일한 체크리스트 적용 가능)

### 3.1 원인 유형 A — URL 문제
- 도메인이 만료/폐쇄
- 브랜드의 “브랜드 소개용” 사이트로 변경(스토어 기능 제거)
- 국가별 스토어로 이동(예: `shop-us.*`, `kr.*`, `jp.*` 등)

**진단 신호**
- 홈 접속 시 스토어가 아니라 agency/portfolio/landing page
- 리다이렉트가 반복되거나 지역 선택 강제

**조치**
- `channels.url` 최신화 + `original_url`에 이전 URL 보존
- 도메인 변경이 잦은 채널은 `channel_aliases`(별칭 테이블) 도입 고려

### 3.2 원인 유형 B — 플랫폼 미지원/미감지
현재 크롤러 지원: Shopify + Cafe24 (`research.md` 기준).

**진단 신호**
- HTML에 `cdn.shopify.com`/`myshopify.com` 같은 Shopify 흔적이 없음
- Cafe24 footer/스크립트 흔적이 없음
- 대신 Next.js/React headless, Salesforce Commerce Cloud, Magento 등 흔적

**조치**
- `channels.platform`을 명시적으로 유지(자동감지 + 운영자 override)
- 미지원 플랫폼은:
  - 단기: `active=false`로 제외
  - 중기: 플랫폼별 커넥터/크롤러 backlog로 전환

### 3.3 원인 유형 C — 봇 차단/비정상 응답
- Cloudflare/PerimeterX 등으로 HTML/JSON 접근 차단
- 특정 User-Agent/국가에서만 접근 가능

**진단 신호**
- 브라우저는 정상인데 크롤러는 403/429
- `products.json`이 404/403이거나 CAPTCHA 페이지 반환

**조치**
- httpx 요청 헤더/리트라이/레이트리밋 강화
- “채널 헬스”에 403/429 카운트 및 마지막 성공일 저장
- 필요 시 Playwright 기반 headless 수집(고비용)

---

## 4. 자동 진단 스크립트(권장) — 67개 채널을 1회에 판별

> 아래 스크립트는 로컬/서버에서 실행 가능하며, 결과를 CSV로 저장해  
> `channels.platform`, `channels.url` 업데이트의 근거 자료로 사용합니다.

```python
"""channel_probe.py
- 입력: channels.csv (channel,url)
- 출력: channel_probe_result.csv
"""

import csv
import asyncio
import httpx

SHOPIFY_MARKERS = [
    "cdn.shopify.com",
    "myshopify.com",
    "Shopify.theme",
    "shopify-section",
    "ShopifyPay",
    "window.Shopify",
]
CAFE24_MARKERS = [
    "cafe24",
    "EC_SDE",
    "EC$",
    "cafe24.ec",
    "cafe24.com",
]

def normalize_url(u: str) -> str:
    u = u.strip()
    if not u.startswith("http"):
        u = "https://" + u
    return u

async def fetch_text(client: httpx.AsyncClient, url: str) -> tuple[int, str]:
    try:
        r = await client.get(url, follow_redirects=True, timeout=20)
        return r.status_code, r.text[:200000]  # 과도한 메모리 사용 방지
    except Exception:
        return 0, ""

def detect_platform(html: str) -> tuple[str, float]:
    h = html.lower()
    if any(m.lower() in h for m in SHOPIFY_MARKERS):
        return "shopify", 0.9
    if any(m.lower() in h for m in CAFE24_MARKERS):
        return "cafe24", 0.85
    if "__next_data__" in h:
        return "nextjs(headless?)", 0.6
    return "unknown", 0.2

async def probe_one(client: httpx.AsyncClient, name: str, url: str):
    url = normalize_url(url)
    status, html = await fetch_text(client, url)
    platform, conf = detect_platform(html)

    # Shopify JSON 엔드포인트는 일부 스토어에서 차단될 수 있으므로 '확인용'으로만 사용
    products_json_status = ""
    if platform == "shopify":
        pj_url = url.rstrip("/") + "/products.json?limit=1"
        pj_status, _ = await fetch_text(client, pj_url)
        products_json_status = str(pj_status)

    return {
        "channel": name,
        "input_url": url,
        "http_status": status,
        "platform_guess": platform,
        "platform_confidence": conf,
        "products_json_status": products_json_status,
    }

async def main():
    rows = []
    async with httpx.AsyncClient(headers={
        "User-Agent": "Mozilla/5.0 (compatible; FashionDataEngineBot/1.0; +https://example.com/bot)"
    }) as client:
        with open("channels.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            tasks = [probe_one(client, r["channel"], r["url"]) for r in reader]
            for coro in asyncio.as_completed(tasks):
                rows.append(await coro)

    with open("channel_probe_result.csv", "w", newline="", encoding="utf-8") as f:
        fieldnames = list(rows[0].keys()) if rows else []
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 5. 데이터베이스 구조 — 좋은 사례(패턴) & 현재 프로젝트 적용안

> `research.md`에 정리된 현재 스키마(Channels, Products, PriceHistory, CrawlRun 등)를 기준으로,  
> **“크롤 기반 이커머스/가격추적”** 프로젝트에서 흔히 쓰는 설계 패턴을 추가 제안합니다.

### 5.1 가격/재고 같은 “관측값”은 Fact 테이블로, 메타데이터는 Dimension으로 분리
- 제품의 설명/카테고리/이미지/태그 등은 변하지만(또는 바뀐 것처럼 보이지만) “제품 정체성”은 유지됩니다.
- 반면 가격/세일여부/재고는 시계열로 계속 변합니다.

**권장 구조(요약 ERD)**

```text
Brand (dim)
  └─< ProductIdentity (dim)  -- normalized_key 기준의 '정규화된 제품'
         └─< ChannelListing (dim)  -- 채널별 상품(페이지/핸들/외부ID)
                └─< PriceObservation (fact)  -- observed_at, price, currency, is_sale, in_stock...
Channel (dim) ───────────────┘
CrawlRun (dim-ish) ──< CrawlChannelLog (fact-ish) ──< PriceObservation (fact)
```

> 현재 스키마에서도 Product + PriceHistory로 유사 구조를 갖고 있지만,  
> **“채널 상품(listing)”과 “정규화된 제품(identity)”를 분리**하면 교차채널 매칭/정확도/데이터 품질이 좋아집니다.

### 5.2 Slowly Changing Dimension(Type 2)로 “제품 메타 변화”를 역사로 남기기
예: 제품명이 바뀌거나 카테고리가 변경되는 경우, 단순 overwrite는 과거 분석을 깨뜨릴 수 있습니다.

- Kimball의 SCD Type 2는 변경 시 **새 행을 추가**하고, 유효기간/현재여부 컬럼을 둡니다.
- 적용 포인트: `ProductCatalog` 또는 `ProductIdentity`의 속성(카테고리, 성별, 서브카테고리 등)

### 5.3 PriceHistory/Observation 테이블은 파티셔닝(또는 Timescale) 고려
가격 이력은 데이터가 가장 빨리 커집니다. PostgreSQL은 range/list/hash 파티셔닝을 지원하고, 날짜 범위 파티셔닝은 가격 이력 테이블에 특히 잘 맞습니다.

- 예: `price_history_2026_03`, `price_history_2026_04` 처럼 월 단위 파티션
- 또는 TimescaleDB hypertable로 time-series 최적화(청크 간격 설정 등)

### 5.4 인덱스/제약조건(데이터 품질) 추천
- (채널별 상품) `UNIQUE(channel_id, external_product_id)` 혹은 `UNIQUE(channel_id, handle)`
- (정규화 제품) `UNIQUE(normalized_key)`
- (관측값) `UNIQUE(listing_id, observed_at)` 또는 업서트 정책 확립
- foreign key는 유지하되, 대규모 적재 시 배치 성능을 위해 일부는 deferred/validate 전략 고려

### 5.5 Raw Payload(원본 응답) 보관 — 디버깅/리프로세싱 비용 절감
- `/products.json` 응답 또는 Cafe24 HTML 파싱 결과를 JSONB로 `raw_payload` 컬럼에 보관하면
  - 파서 버그 수정 후 “재크롤 없이 재처리” 가능
  - 공급자(채널) 측 UI 변경에도 회복력이 좋아집니다

---

## 6. 실행 플랜(제안)

### D0~D1 (즉시)
- Route denylist 픽스 적용 + 이미 적재된 Route 상품 정리
- 위 표의 URL 교정(최소 3개: The Loop / 18 East / Velour Garments)
- `channels.platform IS NULL` + `active=true` 채널을 대상으로 자동감지 1회 실행

### D2~D7 (1주)
- `CrawlChannelLog`에 “실패 사유(code)” 표준화: 403/404/timeout/not_supported
- `/admin/channel-signals`에서 never 원인을 플랫폼/URL/차단으로 분류해 보여주기
- PriceHistory 대용량 대비 파티셔닝 전략 결정(월/주 단위)

### 2주~
- 비-Shopify/Cafe24 주요 플랫폼(예: Magento/SFCC/Next.js headless) 1~2개 우선 커넥터 설계
- “채널 온보딩” 프로세스(플랫폼 감지 → 테스트 크롤 → 활성화) 자동화

---
## 부록 A. 의뢰서 채널 목록(67개)

### 그룹 A: Route 배송보험 문제 확인된 채널 (3개)
- The Loop Running Supply — thelooprunningsupply.com
- 18 East — 18east.com
- Velour Garments — velourgarments.com

### 그룹 B-1: 글로벌 유명 채널 — Shopify 여부 우선 확인 (12개)
- Bodega — https://bdgastore.com
- Joe Freshgoods — https://www.joefreshgoods.com
- Warren Lotas — https://www.warrenlotas.com
- Dover Street Market — https://store.doverstreetmarket.com
- PALACE SKATEBOARDS — https://shop.palaceskateboards.com
- SEVENSTORE — https://www.sevenstore.com
- HIP — https://www.thehipstore.co.uk
- HBX — https://hbx.com
- AXEL ARIGATO — https://www.axelarigato.com
- Séfr — https://www.sefr-online.com
- KA-YO — https://www.ka-yo.com
- Camperlab — https://www.camperlab.com

### 그룹 B-2: 일본 채널 — 비표준 플랫폼 의심 (15개)
- SOMEIT — https://someit.stores.jp
- elephant TRIBAL fabrics — https://elephab.buyshop.jp
- UNDERCOVER Kanazawa — https://undercoverk.theshop.jp
- TITY — https://tity.ocnk.net
- Laid back — https://laidback0918.shop-pro.jp
- TIGHTBOOTH — https://shop.tightbooth.com
- TTTMSW — https://www.tttmsw.jp
- ACRMTSM — https://www.acrmtsm.jp
- CLESSTE — https://www.clesste.com
- F/CE — https://www.fce-store.com
- LTTT — https://www.lttt.life
- MaisonShunIshizawa store — https://www.maisonshunishizawa.online
- Pherrow's — https://www.pherrows.tokyo
- The Real McCoy's — https://www.therealmccoys.jp
- and wander — https://www.andwander.co.kr

### 그룹 B-3: 한국 채널 — Cafe24 또는 자체몰 (29개)
- Kasina — https://www.kasina.co.kr
- thisisneverthat — https://www.thisisneverthat.com
- CAYL — https://www.cayl.co.kr
- Unipair — https://www.unipair.com
- ECRU Online — https://www.ecru.co.kr
- GOOUTSTORE — https://gooutstore.cafe24.com
- obscura — https://www.obscura-store.com
- Casestudy — https://www.casestudystore.co.kr
- grds — https://www.grds.com
- 8DIVISION — https://www.8division.com
- ADEKUVER — https://www.adekuver.com
- APPLIXY — https://www.applixy.com
- Alfred — https://www.thegreatalfred.com
- BIZZARE — https://www.bizzare.co.kr
- COEVO — https://www.coevo.com
- EFFORTLESS — https://www.effortless-store.com
- ETC SEOUL — https://www.etcseoul.com
- MODE MAN — https://www.mode-man.com
- Meclads — https://www.meclads.com
- NOCLAIM — https://www.noclaim.co.kr
- Openershop — https://www.openershop.co.kr
- PARLOUR — https://www.parlour.kr
- Rino Store — https://www.rinostore.co.kr
- SCULP STORE — https://www.sculpstore.com
- THEXSHOP — https://www.thexshop.co.kr
- TUNE.KR — https://www.tune.kr
- a.dresser — https://www.adressershop.com
- empty — https://www.empty.seoul.kr
- Sun Chamber Society — https://www.sunchambersociety.com
- heritagefloss — https://www.heritagefloss.com
- nightwaks — https://www.nightwaks.com
- 브레슈 (Breche) — https://www.breche-online.com
- 블루스맨 (Bluesman) — https://www.bluesman.co.kr

### 그룹 B-4: 기타 글로벌 채널 (4개)
- Stone Island — https://www.stoneisland.com
- VINAVAST — https://www.vinavast.co
- The Trilogy Tapes — https://www.thetrilogytapes.com
- Goldwin — https://www.goldwin-global.com

---

## References (원문 링크)

```text
Route: Why is Route Package Protection appearing as a product?
https://merchants.help.route.com/hc/en-us/articles/360020712633-Why-is-Route-Package-Protection-appearing-as-a-product-in-my-store

Route: How to hide Route Package Protection as a product
https://merchants.help.route.com/hc/en-us/articles/360022095133-How-to-hide-Route-Package-Protection-as-a-product-in-my-store

Route product update (widget/cart line-item change)
https://route.com/product-updates/new-route-widget-same-great-protection

PostgreSQL Table Partitioning (official docs)
https://www.postgresql.org/docs/current/ddl-partitioning.html

TimescaleDB Hypertables (chunk interval best practices)
https://docs.timescale.com/use-timescale/latest/hypertables/

Kimball SCD Type 2 (Add New Row)
https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/type-2/

Shopify Ajax Product API (official docs)
https://shopify.dev/docs/api/ajax/reference/product
```
