# [Codex] Phase 1 완료: 크롤러 품질 개선 + 전체 파이프라인 실행

> **Context**: `AGENTS.md` 참조. 현재 브랜치 `main`.
> 이 이슈의 목표는 브랜드 크롤러를 75개 edit-shop 전체에 대해 신뢰성 있게 실행하는 것.

---

## 현재 상태 (2026-02-25 기준)

### 완료된 것
- 154개 채널 DB 저장 (`channels` 테이블)
  - `channel_type`: `brand-store` 75개 / `edit-shop` 75개
  - `country`: KR 36, JP 61, US 15, UK 14 등 16개국
- 크롤러 전략 3가지 구현:
  - **Shopify**: `/products.json` API → vendor 필드 추출 (정확도 높음)
  - **Cafe24**: `/brand` 페이지 `cate_no=` 파라미터 필터링
  - **Generic**: `/brands` HTML 파싱 → 네비게이션 분석 fallback

### 알려진 문제

#### 1. Cafe24 편집샵 — 브랜드 추출 불안정
다음 채널들이 Cafe24 기반이며 현재 결과가 부정확:

| 채널 | URL | 문제 |
|------|-----|------|
| 8DIVISION | https://www.8division.com | ~796개 → 콜라보 서브카테고리 혼입 |
| ADEKUVER | https://m.adekuver.com | 2개 → 가격 정렬 링크만 잡힘 |
| Kasina | https://www.kasina.co.kr | 미테스트 |
| obscura | https://www.obscura-store.com | 미테스트 |
| BIZZARE | https://www.bizzare.co.kr | 미테스트 |
| ECRU Online | https://www.ecru.co.kr | 미테스트 |
| Rino Store | https://www.rinostore.co.kr | 미테스트 |
| COEVO | https://www.coevo.com | 미테스트 |
| GOOUTSTORE | https://gooutstore.cafe24.com | 미테스트 |
| EFFORTLESS | https://www.effortless-store.com | 미테스트 |
| nightwaks | https://www.nightwaks.com | 미테스트 |

#### 2. 0 결과 채널 예상
네비게이션 fallback으로 0 결과가 예상되는 채널들:
- Cafe24 기반 한국 편집샵 다수
- 일본 편집샵 중 커스텀 플랫폼 사용 샵

#### 3. 중복 브랜드 엔트리
- `1017 Alyx 9sm` + `1017 알릭스 9SM` 같은 영문/한국어 중복
- `Adidas Originals By Wales Bonner` 같은 콜라보 세부 항목

---

## 해야 할 작업

### Task 1: Cafe24 브랜드 추출 개선

**파일**: `src/fashion_engine/crawler/brand_crawler.py`

현재 `_try_cafe24_brands()` 메서드는 `/brand` 페이지에서
`href`에 `cate_no=` 포함 + `product_no=` 미포함인 링크를 추출.

개선 방향:
1. **네비게이션 depth 필터**: Cafe24 메인 카테고리(1depth)만 추출.
   - `<ul class="xans-layout-navigation">` 또는 `<ul class="depth1">` 하위 링크
   - 하위 `<ul class="depth2">` 이하는 제외
2. **텍스트 길이 필터**: 브랜드명은 일반적으로 50자 이하
3. **8DIVISION 전용 전략 추가** (CHANNEL_STRATEGIES에):
   ```python
   "8division.com": {
       "brand_list_url": "https://www.8division.com/brand",
       "brand_selector": "...",  # 실제 구조 파악 후 작성
   }
   ```

테스트 방법:
```bash
uv run python scripts/crawl_brands.py --limit 3
# 8DIVISION이 100개 이하면 성공
```

### Task 2: 브랜드 중복 정규화

**파일**: `src/fashion_engine/services/brand_service.py`

현재 `upsert_brand()`는 이름 완전 일치로만 중복 처리.
다음 케이스 처리 필요:
1. 한글/영문 동일 브랜드 (예: `1017 Alyx 9sm` ↔ `1017 알릭스 9SM`)
   - slug 기준 중복 검사 추가
2. 콜라보 이름 필터 (`X`, `×`, `By`, `x ` 포함 + 길이 > 40자 → 건너뜀)
   - `_is_valid_brand_name()` 에 콜라보 패턴 필터 추가

### Task 3: 전체 파이프라인 실행

```bash
# 전체 edit-shop 75개 크롤
uv run python scripts/crawl_brands.py
```

결과 확인:
```bash
uv run python -m fashion_engine.cli brands
# 0 결과 채널 목록 출력
```

0 결과 채널이 10개 이상이면 해당 채널 URL 목록을 이슈 댓글로 남길 것.

### Task 4: 0 결과 채널 수동 전략 추가

Task 3 이후 0 결과 채널 목록 기반으로 상위 10개 채널에 대해
`CHANNEL_STRATEGIES` 에 커스텀 전략 추가.

우선순위 (규모 큰 편집샵):
1. Kasina (`kasina.co.kr`)
2. THEXSHOP (`thexshop.co.kr`)
3. Unipair (`unipair.com`)
4. PARLOUR (`parlour.kr`)

---

## 개발 환경

```bash
source /Users/kim-usang/.local/bin/env
cd /Users/kim-usang/fashion-data-engine
uv sync
uv run playwright install chromium

# 테스트
uv run python scripts/crawl_brands.py --limit 5
uv run pytest
```

## 주의사항

- `data/fashion.db` 는 gitignore (로컬 상태)
- 크롤러 테스트 시 반드시 `--limit 3~5` 먼저 실행
- `BaseCrawler` 에 rate limit 내장 → 별도 sleep 추가 금지
- 새 전략 추가 전 반드시 `--limit 1` 로 테스트
