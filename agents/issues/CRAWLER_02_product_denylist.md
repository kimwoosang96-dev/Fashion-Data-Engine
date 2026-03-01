# CRAWLER_02: 비패션 제품 필터링 (Product Denylist)

**Task ID**: T-20260301-054
**Owner**: codex-dev
**Priority**: P1
**Labels**: backend, crawler, data-quality

---

## 배경

Shopify 스토어에는 "Route Package Protection" 같은 비패션 앱 제품이 `/products.json` API에 일반 제품처럼 노출됩니다. 현재 크롤러는 이를 패션 제품으로 오인식하여 DB에 저장합니다.

**스크린샷에서 확인된 오인덱싱 사례:**
- "Shipping Protection by Route" (vendor: `route`, handle: `routeins`) — ₩1,398~₩1,400으로 3개 채널에서 발견
- 이 제품이 경쟁 페이지(`/compete`) 상단에 68%+ 스프레드로 노출되어 노이즈를 유발

**현재 필터링 현황** (`src/fashion_engine/crawler/product_crawler.py`):
- `_parse_product()`: 가격>0, title/handle 비어있지 않음 체크만 존재
- vendor, product_type, tags 기반 필터 없음

**참고 파일**: `AGENTS.md` → Coding Conventions, `src/fashion_engine/crawler/product_crawler.py`

---

## 요구사항

### 1. 모듈 상단에 거부 목록 상수 추가

`src/fashion_engine/crawler/product_crawler.py` 파일 내, import 블록 아래에 추가:

```python
# ── 비패션 제품 거부 목록 ────────────────────────────────────────────────────
_VENDOR_DENYLIST: frozenset[str] = frozenset({
    "route",        # Route Package Protection (배송보험)
    "routeins",
    "extend",       # Extend Warranty
    "clyde",        # Clyde Warranty
    "seel",         # Seel Return Guarantee
})

_TITLE_KEYWORD_DENYLIST: frozenset[str] = frozenset({
    "shipping protection",
    "package protection",
    "gift card",
    "gift certificate",
    "e-gift card",
    "digital gift",
    "warranty protection",
    "product protection",
    "return assurance",
})

_PRODUCT_TYPE_DENYLIST: frozenset[str] = frozenset({
    "gift cards",
    "gift card",
    "services",
    "insurance",
    "warranty",
})
```

### 2. `_parse_product()` 메서드 수정 (Shopify JSON 파서)

기존 `title`, `handle`, `price` 기본 검증 직후에 거부 목록 체크 추가:

```python
# ── 거부 목록 체크 ────────────────────────────────────────────
vendor_lower = vendor.lower().strip()
if vendor_lower in _VENDOR_DENYLIST:
    return None

product_type_lower = (product_type or "").lower().strip()
if product_type_lower and product_type_lower in _PRODUCT_TYPE_DENYLIST:
    return None

title_lower = title.lower()
if any(kw in title_lower for kw in _TITLE_KEYWORD_DENYLIST):
    return None
```

### 3. 기존 오인덱싱 제품 정리 스크립트 (선택)

`scripts/cleanup_route_products.py` 신규 작성 (DRY-RUN 기본):
- `product_key LIKE 'route:%'` 인 제품을 조회하여 목록 출력
- `--execute` 옵션 시 `is_active=False`, `archived_at=now()` 처리 (삭제 아닌 soft-delete)

---

## DoD (완료 기준)

- [ ] `_VENDOR_DENYLIST`, `_TITLE_KEYWORD_DENYLIST`, `_PRODUCT_TYPE_DENYLIST` 상수 존재
- [ ] `_parse_product()`에서 vendor/product_type/title 거부 목록 체크 후 `return None`
- [ ] 테스트: `uv run python scripts/crawl_products.py --limit 3 --channel-type brand-store` 실행 후 `product_key`에 `"route:"` 포함 항목 없음
- [ ] (선택) `cleanup_route_products.py` DRY-RUN 실행 결과 출력

## 참고: 위치 찾기

```bash
# _parse_product 위치 확인
grep -n "_parse_product\|def _parse" src/fashion_engine/crawler/product_crawler.py
# 현재 기본 검증 위치 확인
grep -n "not title\|not handle\|price <= 0" src/fashion_engine/crawler/product_crawler.py
```
