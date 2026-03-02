# CAFE24_SOLDOUT_FILTER_01: Cafe24 SOLD OUT 플레이스홀더 제품 필터링 강화

**Task ID**: T-20260302-060
**Owner**: codex-dev
**Priority**: P1
**Labels**: backend, crawler, bug-fix, data-quality

---

## 배경

CrawlRun #1에서 THEXSHOP (Cafe24 플랫폼) 크롤 결과:
- **duration_ms**: 1,897,613ms (31분!)
- **수집된 제품**: 45,242개, 전부 `is_active=False`, `name="SOLD OUT"`
- 전량 삭제 처리 완료 (DB 수동 삭제)

**근본 원인**: `product_crawler.py`의 `_try_cafe24_products()` 내부 `is_available` 검출 로직이 카드 전체 텍스트를 사용함:

```python
# 현재 (BUG): src/fashion_engine/crawler/product_crawler.py 약 line 423-424
text = card.get_text(" ", strip=True).lower()
is_available = not ("품절" in text or "sold out" in text or "soldout" in text)
```

THEXSHOP은 품절 제품을 `name="SOLD OUT"`인 플레이스홀더 카드로 표시하는데, 해당 카드의 전체 텍스트에 "sold out"이 포함되어 `is_available=False`로 올바르게 설정되지만, 제품 자체는 여전히 INSERT됨.

두 번째 문제: **이름 기반 필터 없음** — `product name="SOLD OUT"`이더라도 denylist 미적용으로 insert됨.

---

## 요구사항

### 변경 파일: `src/fashion_engine/crawler/product_crawler.py`

#### 수정 1: `_TITLE_KEYWORD_DENYLIST` 확장

```python
_TITLE_KEYWORD_DENYLIST: frozenset[str] = frozenset({
    # ... 기존 항목들 ...
    "sold out",          # 이름이 "SOLD OUT"인 Cafe24 플레이스홀더
    "품절",              # 한국어 품절 플레이스홀더
})
```

#### 수정 2: `is_available` 검출 로직 개선

`_try_cafe24_products()` 내부에서 카드 전체 텍스트 대신 품절 배지 셀렉터 우선 사용:

```python
# 개선안: 품절 배지/버튼 클래스 우선 탐색
sold_out_badge = card.select_one(
    ".icon-soldout, .soldout, [class*='soldout'], "
    ".sold-out-label, .btn-soldout, [class*='sold-out']"
)
if sold_out_badge:
    is_available = False
else:
    # 폴백: 타이틀 엘리먼트만 체크 (카드 전체 텍스트 X)
    title_el = card.select_one(".prdName, .name, h3, h4, .prd_name")
    title_text = (title_el.get_text(strip=True).lower()
                  if title_el else "")
    is_available = not (
        "품절" in title_text or "sold out" in title_text or "soldout" in title_text
    )
```

#### 수정 3: 연속 품절 카드 조기 중단 (선택)

카테고리 내에서 `is_available=False` + 제품명이 의미없는 카드가 연속 50개 이상이면 해당 cate_no 조기 중단:

```python
# _try_cafe24_products() 내부 루프에 추가
consecutive_unavailable = 0
MAX_CONSECUTIVE_UNAVAILABLE = 50

for card in cards:
    # ... 파싱 ...
    if not is_available:
        consecutive_unavailable += 1
        if consecutive_unavailable >= MAX_CONSECUTIVE_UNAVAILABLE:
            logger.warning(
                f"[cafe24] {base_url}: cate_no={cate_no} "
                f"연속 품절 {consecutive_unavailable}개 → 조기 중단"
            )
            break
    else:
        consecutive_unavailable = 0
```

---

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `src/fashion_engine/crawler/product_crawler.py` | 변경 대상 — `_TITLE_KEYWORD_DENYLIST`, `_try_cafe24_products()` |

### 코드 위치 참고

- `_TITLE_KEYWORD_DENYLIST`: 파일 상단 frozenset 정의 (약 line 70~85)
- `_try_cafe24_products()`: Cafe24 HTML 파싱 함수 (약 line 353~465)
- `is_available` 검출: 약 line 423~424

---

## DoD (완료 기준)

- [ ] `_TITLE_KEYWORD_DENYLIST`에 `"sold out"`, `"품절"` 추가
- [ ] `is_available` 검출: 배지 셀렉터 우선 → 제목 텍스트 폴백
- [ ] 연속 품절 50개 이상 시 cate_no 조기 중단 로직 추가
- [ ] THEXSHOP 재크롤 시 0개 또는 실제 재고 제품만 수집

## 검증

```bash
# THEXSHOP 채널 ID 확인
sqlite3 data/fashion.db "SELECT id, name FROM channels WHERE name LIKE '%THEXSHOP%';"

# THEXSHOP 단일 채널 재크롤 (channel_id 확인 후 대입)
uv run python scripts/crawl_products.py --channel-id <THEXSHOP_ID>

# 결과 확인 (0개이거나 실제 제품명)
sqlite3 data/fashion.db "
SELECT name, COUNT(*) FROM products
WHERE channel_id=<THEXSHOP_ID>
GROUP BY name ORDER BY COUNT(*) DESC LIMIT 10;"
```
