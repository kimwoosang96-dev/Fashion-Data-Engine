# Fashion Data Engine v2 — 계획서

> 작성일: 2026-03-14
> **승인 전까지 구현하지 않습니다.**

---

## 1. 프로젝트 방향

### 한 줄 포지셔닝

> **"국내 중소형 편집샵이 직수입하는 브랜드들을, 한 곳에서 가격 비교한다."**

### 왜 중소형 편집샵인가

- 무신사는 가품·택깔이 이슈로 신뢰도 하락 중
- 중소형 편집샵은 직접 바잉(직수입) → 진품 보장, 큐레이션 품질 높음
- 그러나 채널이 분산되어 있어 소비자가 일일이 확인해야 함
- **소비자 문제**: 어디서 사는 게 싸고, 재고 있나?
- **공급자(샵) 문제**: 좋은 물건을 바잉해도 노출이 부족함

이 서비스가 중간에서 두 문제를 동시에 해결한다.

### v1 vs v2 차이

| 항목 | v1 | v2 |
|------|----|----|
| 채널 | 전세계 Shopify 중심 | **국내 중소형 편집샵** |
| 타겟 상품 | 전체 (국내 브랜드 포함) | **수입브랜드 중심** |
| 기능 | 가격비교 + Intel + 뉴스 + 협업... | **가격비교 + 재고 추적** |
| 다음 단계 | 없음 | 국내 유통 브랜드 → 일본 스톡키스트 |

---

## 2. 타겟 채널 (국내 중소형 수입 편집샵)

### 2.1 조사 결과 요약

- v1 프로젝트에서 이미 **국내 편집샵 28개**가 등록되어 있었음 → 전부 재활용
- 신규 조사로 발굴한 채널 추가 (슬로우스테디클럽, 아이앰샵, 라이커샵, 아이디룩 등)
- 국내 편집샵의 압도적 다수가 **Cafe24** 기반
- Shopify는 애딕티드 서울 1개만 확인
- 커스텀 플랫폼: 카시나(Next.js), 비이커(삼성 SSF)

---

### 2.2 전체 채널 목록 (Codex 조사 완료 — 2026-03-14)

#### Cafe24 기반 — cate_no 확인 완료 (즉시 크롤 가능)

| 채널 | URL | 전체 cate_no | 세일 cate_no | 주요 수입 브랜드 |
|------|-----|------------|------------|----------------|
| **더엑스샵** | thexshop.co.kr | 24 | 26 | Carhartt WIP(375), Stüssy(571), Gramicci(745), Arc'teryx(1544), Salomon(1062), Snow Peak(1515) |
| **슬로우스테디클럽** | slowsteadyclub.com | 671 | 723 | Auralee(259), New Balance(275), Ciota(1763), Graphpaper(172), mfpen(406) |
| **아이앰샵** | iamshop-online.com | 5801 | 6746 | Auralee(842), Teatora(947), Columbia(7268), Remi Relief(7274), Repro.Found(5346), Taion(967) |
| **Meclads** | meclads.com | 70 | - | Adidas(202), Ancellm(188), Aton Tokyo(119), Batoner(53), Casey Casey(140), Ciota(147), F/CE(88), Goldwin(156), Guidi(99) |
| **a.dresser** | adressershop.com | 59 | - | Niceness(52), Auberge(76), Herill(48), Heugn(47), Le Yucca's(54), Maatee&Sons(49), Outil(73), Phigvel(50) |
| **SCULP STORE** | sculpstore.com | 255 | - | Arc'teryx(811), 424(315), Afield Out(388), Anachronorm(793), BAL(166), Clarks(306), DESCENTE ALLTERRAIN(1512) |
| **BIZZARE** | bizzare.co.kr | 162 | - | Dairiku(370), JieDa(367), Faccies(371), Aliveform(405), ASKYURSELF(457), Levi's(417), Praying(465) |
| **Rino Store** | rinostore.co.kr | 405 | 511 | Anatomica(401), Andersen-Andersen(94), Batoner(369), Camiel Fortgens(393), Ciota(523), EG(544), Filson(546), Gramicci(98) |
| **ADEKUVER** | adekuver.com | 59 | 1 | 1017 ALYX(78), A-COLD-WALL(384), Ann Demeulemeester(83), Hyke(277), Jean Paul Gaultier(1866), Julius(1285) |
| **EFFORTLESS** | effortless-store.com | - | 134 | EG(334), EG Workaday(243), orSlow(394), mfpen(177), kolor(246), John Mason Smith(54) |
| **NOCLAIM** | noclaim.co.kr | 52 | 544 | New Balance(1733), Needles(868), Nanamica(867), Danton(840), Ciota(1158), Brain Dead(1929) |
| **Casestudy** | casestudystore.co.kr | 125 | - | Auralee(216), Carhartt WIP(145), C.P. Company(211), Aries(55), Casablanca(56), Brain Dead(432) |
| **하이츠스토어** | heights-store.com | 1986 | - | Stüssy(206), Arc'teryx(1760), Asics(3753), Carne Bollente(2635), Camper Lab(2638) |
| **8DIVISION** | 8division.com | - | 533 | Gimaguas(3227), KAMIYA(3447), Gramicci(273), Arc'teryx(2646) |
| **블루스맨** | bluesman.co.kr | 25 | 75 | Gramicci, Ordinary Fits, Paraboot, Resolute, Battenwear, orSlow, Post O'Alls |

#### Cafe24 기반 — 전체 cate_no만 확인 (브랜드별 추가 탐색 필요)

| 채널 | URL | 전체 cate_no | 세일 cate_no | 바잉 성격 |
|------|-----|------------|------------|----------|
| **ETC Seoul** | etcseoul.com | 24 | 1519 | 아웃도어·미니멀 (Arc'teryx 1088, Salomon 917, Mont-Bell 1967 확인) |
| **옵스큐라** | obscura-store.com | 28 | 401 | 아웃도어·아방가르드 |
| **에크루** | ecru.co.kr | 1795 | 1817 | 컨템포러리 (A.Presse 1531, Neighborhood 1375 확인) |
| **아이디룩** | idlook.co.kr | 32 | - | 유럽 컨템포러리 여성 (Sandro, Maje, A.P.C.) |
| **라이커샵** | rhykershop.co.kr | 493 | 495 | 유럽·일본 니치 (Gimaguas 565, Diemme 500 확인) |
| **MODE MAN** | mode-man.com | 50 | 965 | 아메카지·데님 (Nigel Cabourn, Buzz Rickson's, orSlow, Red Wing) |
| **Unipair** | unipair.com | 64 | 150 | 슈즈 편집 (Joe's Garage, Green Door Newman) |
| **GOOUTSTORE** | gooutstore.cafe24.com | - | - | 아웃도어·캠핑 (Fashion 26, Outdoor 27) |
| **Alfred** | thegreatalfred.com | 44 | 51 | 컨템포러리 |
| **Openershop** | openershop.co.kr | 828 | 1119 | 해외 디자이너 브랜드 편집샵 |
| **empty** | empty.seoul.kr | - | 868 | 컨템포러리 (Mad Frenzy 750, Florentina Leitner 783 확인) |
| **PARLOUR** | parlour.kr | 99 | - | 남성 구두 (Alden, Crockett & Jones, J.M. Weston, Sanders) |

---

#### Shopify 기반

| 채널 | URL | 상태 | 주요 브랜드 |
|------|-----|------|-----------|
| **애딕티드 서울** | addictedseoul.com | `/products.json` 200 ✅ | Our Legacy, Acne Studios, Marni, Craig Green, J.W.Anderson, Wales Bonner, 100+ |

---

#### 커스텀 플랫폼

| 채널 | URL | 플랫폼 | 크롤 방식 | 주요 브랜드 | 도입 시기 |
|------|-----|--------|----------|-----------|---------|
| **COEVO** | coevo.com | 자체몰 (PHP) | `goods_list.php?brandCd=149` | Stone Island, C.P. Company, Acronym | Phase 2 |
| **카시나** | kasina.co.kr | Next.js 커스텀 | HTML 파싱 | Nike 공인, Stüssy 국내 공식, NB | Phase 2 |
| **비이커** | ssfshop.com/beaker | 삼성 SSF | HTML 파싱 | A.P.C., Lemaire, Maison Kitsuné, Carhartt WIP | Phase 2 |
| **분더샵** | boontheshop.com | WordPress | HTML 파싱 | Lemaire, Acne, Marni, Loewe 500+ | Phase 2 |

---

#### 제외 확정

| 채널 | URL | 제외 사유 |
|------|-----|---------|
| **grds** | grds.com | 자체 슈즈 라인 전용 — 수입 편집샵 아님 |
| **APPLIXY** | applixy.com | 세컨핸드 플랫폼 — 편집샵 구조 아님 |
| **TUNE.KR** | tune.kr | Shopify지만 `/products.json` 403 — API 막힘 |

---

### 2.3 대형 플랫폼 처리 방침

| 채널 | 판단 | 이유 |
|------|------|------|
| 무신사 | ❌ 제외 | 가품·택깔이 이슈, 국내 브랜드 중심, 수입브랜드 추출 어려움 |
| 29CM | ❌ 제외 | 국내 브랜드 비중 높음, WAF 강함 |
| W컨셉 | ❌ 제외 | 국내 디자이너 중심 |
| 하고/SSF (비이커 제외) | ❌ 제외 | 국내 자사 브랜드 중심 |
| 코오롱몰 | ❌ 제외 | 국내 계열사 중심 |

---

### 2.4 채널별 주요 브랜드 커버리지 (확인된 것만)

| 브랜드 | ETC | XShop | Obscura | IAM | SSC | Rhyker | Addicted | IDlook |
|--------|-----|-------|---------|-----|-----|--------|----------|--------|
| Auralee | ✅ | - | - | ✅ | ✅ | - | - | - |
| Gramicci | ✅ | ✅ | - | - | - | - | - | - |
| Carhartt WIP | - | ✅ | - | - | - | - | - | - |
| Stüssy | - | ✅ | - | - | - | - | - | - |
| Our Legacy | - | - | - | - | - | - | ✅ | - |
| Acne Studios | - | - | - | - | - | - | ✅ | - |
| A.P.C. | - | - | - | - | - | - | - | ✅ |
| Sandro / Maje | - | - | - | - | - | - | - | ✅ |
| Salomon | ✅ | ✅ | - | - | - | - | - | - |
| Arc'teryx | ✅ | ✅ | - | - | - | - | - | - |
| New Balance | - | - | - | - | ✅ | - | - | - |
| Montbell | ✅ | ✅ | ✅ | - | - | ✅ | - | - |
| Engineered Garments | ✅ | - | - | ✅ | - | - | - | - |
| Guidi | ✅ | - | ✅ | - | - | - | - | - |
| And Wander | ✅ | - | ✅ | - | - | - | - | - |
| Helinox | - | ✅ | ✅ | - | - | - | - | - |

---

## 3. Scrapling 기반 크롤링 설계

### 3.1 Scrapling Fetcher 3종 배정

```
Fetcher (httpx + TLS 지문 위장)
  └─ Cafe24 편집샵 (Tier A 전체)
  └─ Shopify 편집샵 (애딕티드 서울)
  → 빠름, 서버 부하 최소

StealthyFetcher (Playwright 스텔스 + Cloudflare 자동 우회)
  └─ 카시나 (Next.js 커스텀, Phase 2)
  └─ Cloudflare 감지 시 자동 업그레이드

DynamicFetcher (풀 브라우저)
  └─ 비이커/분더샵 (Phase 2, 필요 시)
```

### 3.2 크롤러 아키텍처

```python
src/fashion_engine/crawler/
├── base.py          # BaseCrawler: rate limit, retry, 차단 감지
├── shopify.py       # Fetcher — /products.json
├── cafe24.py        # Fetcher — /category/{cate_no} HTML 파싱
├── stealth.py       # StealthyFetcher — Cloudflare 우회
└── strategies/
    ├── __init__.py
    ├── cafe24_channels.py   # 채널별 cate_no 매핑
    └── shopify_channels.py  # Shopify 채널 목록
```

### 3.3 Cafe24 채널 전략 (핵심)

각 Cafe24 편집샵마다 브랜드별 카테고리 번호(`cate_no`)를 사전 조사해야 함.

```python
CAFE24_STRATEGIES = {
    "etcseoul": {
        "base_url": "https://etcseoul.com",
        "fetcher": "basic",
        "brand_categories": {
            # 직접 조사 후 채워야 함
            "auralee":    "cate_no=101",
            "gramicci":   "cate_no=102",
            "salomon":    "cate_no=103",
            # ...
        },
        "rate_limit": 2.0,      # 초
        "concurrency": 3,
        "crawl_days": ["mon", "thu"],  # 2회/주
    },
    "slowsteadyclub": {
        "base_url": "https://slowsteadyclub.com",
        "fetcher": "basic",
        "rate_limit": 2.0,
        "concurrency": 3,
        "crawl_days": ["mon", "thu"],
    },
    "thexshop": {
        "base_url": "https://thexshop.co.kr",
        "fetcher": "basic",
        "rate_limit": 2.0,
        "concurrency": 3,
        "crawl_days": ["mon", "fri"],
    },
    # ...
}
```

---

## 4. 차단 리스크 최소화

### 4.1 리스크 vs 대책

| 리스크 | 대책 |
|--------|------|
| IP 차단 (과다 요청) | 도메인당 rate limit 2~3초, 새벽 크롤 |
| UA/TLS 핑거프린팅 | Scrapling `Fetcher(impersonate='chrome')` |
| Cloudflare 챌린지 | `StealthyFetcher` (자동 우회) |
| Accept-Language → 가격 왜곡 | **헤더 제거** (T-101 재발 방지) |
| 개인화 편향 | 비로그인 상태 강제 크롤 |
| 연속 실패 | 5회 실패 → 채널 일시 비활성 + Discord 알림 |

### 4.2 Rate Limit 정책

```
Cafe24 채널 (중소형):
  - 요청 간격: 2초
  - 동시 요청: 3
  - 크롤 시각: 새벽 3:00~5:00

Shopify 채널 (애딕티드 서울):
  - 요청 간격: 1초
  - 동시 요청: 5

카시나 (커스텀, Phase 2):
  - 요청 간격: 4초
  - 동시 요청: 1
```

### 4.3 Cafe24 특이사항

Cafe24는 CloudFlare CDN을 사용하지만 중소형 쇼핑몰은 WAF 강도가 약함.
`Fetcher(impersonate='chrome')`만으로 대부분 통과 예상.
막힐 경우 `StealthyFetcher`로 자동 업그레이드.

```python
async def fetch_with_fallback(url, channel):
    try:
        return await Fetcher(impersonate='chrome').get(url)
    except BlockedError:
        logger.warning(f"{channel}: Fetcher 차단 → StealthyFetcher 전환")
        return await StealthyFetcher().fetch(url)
```

---

## 5. 데이터 모델 정리

### 5.1 유지

```
Channel         — 국내 중소형 편집샵 (channel_type: edit-shop)
Brand           — 수입 브랜드
Product         — 제품 (is_active, is_sale, archived_at)
PriceHistory    — 가격 이력
ExchangeRate    — 환율 (KRW 기준)
ChannelBrand    — 채널-브랜드 연결
WatchListItem   — 관심 목록
CrawlRun        — 크롤 실행 단위
CrawlChannelLog — 채널별 결과
```

### 5.2 제거

```
Intel 관련 4개 테이블
FashionNews
BrandDirector
BrandCollaboration
Drop
Purchase
ChannelNote
ProductCatalog
Category
```

### 5.3 Channel 모델 변경

```python
channel_type: "edit-shop"          # 이 프로젝트는 편집샵만
country: "KR"                       # 초기 국내 한정
platform: "cafe24" | "shopify" | "custom"
import_focus: bool                  # 수입브랜드 특화 여부 (신규 필드)
```

---

## 6. API 엔드포인트 정리

### 유지

```
GET /products/sales-highlights   — 세일 중인 수입브랜드 제품
GET /products/search             — 브랜드/제품명 검색
GET /products/compare/{key}      — 채널별 가격 비교 ← 핵심
GET /channels/                   — 편집샵 목록
GET /brands/                     — 수입 브랜드 목록
GET /watchlist/                  — 관심 목록
POST /watchlist/                 — 관심 등록
GET /health
GET /admin/crawl-runs
GET /admin/crawl-trigger
```

### 제거

```
/intel/*  /news/*  /directors/*  /collabs/*
/drops/*  /purchases/*  /catalog/*
```

---

## 7. 업데이트 주기

| 채널 유형 | 빈도 | 시각 |
|-----------|------|------|
| 전체 Cafe24 채널 | 2회/주 (월·목) | 새벽 3:00 |
| 애딕티드 서울 (Shopify) | 2회/주 (월·목) | 새벽 3:30 |
| 환율 업데이트 | 매일 | 07:00 |
| 데이터 감사 | 매주 일요일 | 09:00 |

> 대형 플랫폼 제외 후 크롤 부하가 크게 줄어 2회/주로도 충분.
> 신규 상품/세일 감지 시 Discord 알림.

---

## 8. 구현 Phase

### Phase A — 클린업 (v1 → v2)

- [ ] 불필요 모델 제거 (Intel, FashionNews, BrandDirector 등 8개)
- [ ] 불필요 API 라우터 제거 (intel, news, directors, collabs, drops, purchases, catalog)
- [ ] 불필요 스크립트 제거
- [ ] 채널 DB: 국내 중소형 편집샵 외 비활성화
- [ ] Alembic 마이그레이션: 제거된 테이블 drop
- [ ] pyproject.toml: 불필요 의존성 제거 + `scrapling` 추가

### Phase B — Scrapling 크롤러 구현

- [ ] `scrapling` 설치 및 환경 검증
- [ ] `BaseCrawler` (rate limit, retry, 차단 감지, 로깅)
- [ ] `ShopifyCrawler` → Scrapling `Fetcher` 교체
- [ ] `Cafe24Crawler` → Scrapling `Fetcher` 교체
- [ ] 차단 시 `StealthyFetcher` 자동 fallback

### Phase C — 채널별 파싱 전략 수립 (실조사)

각 채널 직접 방문해서 cate_no / 셀렉터 확정:

- [ ] ETC Seoul — 브랜드별 cate_no 매핑
- [ ] 슬로우스테디클럽 — 브랜드별 cate_no 매핑
- [ ] 더엑스샵 — 브랜드별 cate_no 매핑
- [ ] 아이앰샵 — 브랜드별 cate_no 매핑
- [ ] 라이커샵 — 브랜드별 cate_no 매핑
- [ ] 옵스큐라 — 브랜드별 cate_no 매핑
- [ ] 아이디룩 — 브랜드별 cate_no 매핑
- [ ] 하이츠스토어 — 브랜드별 cate_no 매핑
- [ ] 에크루 — 브랜드별 cate_no 매핑
- [ ] 애딕티드 서울 — /products.json 검증

### Phase D — 데이터 수집 및 검증

- [ ] 채널별 테스트 크롤 (--limit 1)
- [ ] 브랜드 DB 시딩 (수입 브랜드 목록)
- [ ] 가격 단위/통화 정합성 검증
- [ ] product_key / normalized_key 정합성
- [ ] 차단 감지 및 fallback 테스트

### Phase E — 스케줄러 + 알림

- [ ] APScheduler: 2회/주 크롤 + 환율 일간
- [ ] 세일 감지 → Discord 알림
- [ ] Railway 재배포 (API 서비스만, Worker 분리)

### Phase F — 프론트엔드 정리

- [ ] 불필요 페이지 제거 (intel, news, drops, collabs, directors, purchases, map)
- [ ] 유지 페이지: 대시보드, 세일, 채널, 브랜드, 관심목록, 가격비교
- [ ] "국내 직수입 편집샵" 포지셔닝으로 UI 카피 수정

---

## 9. 로드맵 (Phase G 이후)

| 단계 | 내용 |
|------|------|
| Phase G | 국내 편집샵 안정화 후 → 국내 유통 수입 브랜드 목록 분석 |
| Phase H | 해당 브랜드의 일본 스톡키스트 추가 (Beams, United Arrows, SHIPS, Urban Research 등) |
| Phase I | KR vs JP 동일 브랜드 가격 비교 (환율 반영) |
| Phase J | 비이커/카시나 등 커스텀 플랫폼 추가 (크롤링 난이도 해결 후) |

---

*작성: 2026-03-14 | 승인 후 Phase A부터 시작*
