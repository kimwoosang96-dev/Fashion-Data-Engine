# T-079 | INTEL_SHOPIFY_DROP_DETECT_01

> **목적**: Shopify 브랜드 스토어의 `coming-soon` 태그 상품 자동 감지 → intel `drops` 이벤트 생성
> **우선순위**: P2 | **담당**: codex-dev

---

## 배경

현재 intel `drops` 레이어는 `Drop` 모델(수동 시드)의 미러링 데이터뿐.
브랜드 공홈 Shopify 스토어에 `coming-soon` 태그 상품이 등록되면 실제 드롭 예고이지만 자동 감지가 없음.
`crawl_products.py`가 이미 `Product.tags` 필드에 Shopify 태그를 저장하므로, 이를 intel 이벤트로 변환하는 로직만 추가하면 됨.

---

## 구현 요구사항

### Step 1: `scripts/ingest_intel_events.py` — `_ingest_shopify_drops()` 추가

```python
COMING_SOON_TAGS = {"coming-soon", "coming soon", "preorder", "pre-order", "예약", "예약판매"}

async def _ingest_shopify_drops(db: AsyncSession, run: IntelIngestRun) -> None:
    """brand-store Shopify 채널의 coming-soon 태그 상품 → drops 이벤트."""
    # coming-soon 태그 보유 활성 상품 조회 (최근 7일 내 업데이트)
    since = utcnow() - timedelta(days=7)
    rows = (
        await db.execute(
            select(Product)
            .options(selectinload(Product.channel), selectinload(Product.brand))
            .join(Channel, Product.channel_id == Channel.id)
            .where(
                Product.is_active == True,
                Product.updated_at >= since,
                Product.tags.isnot(None),
                Channel.channel_type == "brand-store",
                Channel.platform == "shopify",
            )
        )
    ).scalars().all()

    drop_products = [
        p for p in rows
        if p.tags and any(
            tag.strip().lower() in COMING_SOON_TAGS
            for tag in p.tags.split(",")
        )
    ]

    for product in drop_products:
        channel = product.channel
        brand = product.brand
        brand_name = brand.name if brand else (channel.name if channel else "Unknown")

        await _upsert_event(
            db,
            run=run,
            source_table="products",
            source_pk=product.id,
            event_type="drop",
            layer="drops",
            title=f"{brand_name} 드롭 예고: {product.name[:80]}",
            summary=f"{channel.name if channel else '-'}에서 coming-soon 태그 감지",
            event_time=product.updated_at or utcnow(),
            brand_id=product.brand_id,
            channel_id=product.channel_id,
            source_url=product.url,
            source_type="crawler",
            source_domain=normalize_domain(product.url),
            severity="high",
            confidence="medium",
            geo_country=(channel.country or "").upper()[:2] or None if channel else None,
            details={
                "product_key": product.product_key,
                "tags": product.tags,
                "price_krw": product.price_krw,
                "image_url": product.image_url,
            },
            published_at=product.updated_at,
        )
```

`selectinload` 임포트 추가 (`from sqlalchemy.orm import selectinload`).

---

### Step 2: `run()` 함수에 `shopify_drops` 잡 추가

```python
async def run(job: str, window_hours: int = 48) -> int:
    ...
    if job in {"mirror", "drops_collabs_news"}:
        await _ingest_drops(db, run_row)
        await _ingest_collabs(db, run_row)
        await _ingest_news(db, run_row)
        await _ingest_shopify_drops(db, run_row)  # ← mirror에도 포함
    elif job == "shopify_drops":
        await _ingest_shopify_drops(db, run_row)
    elif job == "derived_spike":
        await _ingest_derived_spike(db, run_row, window_hours=window_hours)
    ...
```

> mirror 잡에 `_ingest_shopify_drops()` 포함시켜 별도 호출 없이도 동작.

---

### Step 3: `scripts/scheduler.py` — shopify_drops 잡 등록

T-077에서 추가한 `intel_mirror_4x_daily` 잡이 mirror를 실행하면 자동으로 포함됨.
별도 잡 불필요. (mirror → shopify_drops 포함 구조)

---

### Step 4: CLI `--job` 옵션에 추가

```python
# ingest_intel_events.py typer app
@app.command()
def main(
    job: str = typer.Option("mirror", help="mirror | derived_spike | shopify_drops"),
    window_hours: int = typer.Option(48),
):
```

---

## DoD

- [ ] `COMING_SOON_TAGS` 상수 정의 (영문 + 한국어 태그 포함)
- [ ] `_ingest_shopify_drops()` 구현 (coming-soon 태그 필터링 + 이벤트 생성)
- [ ] `run()` 함수의 `"mirror"` 분기에 `_ingest_shopify_drops()` 포함
- [ ] `--job shopify_drops` 단독 실행 지원
- [ ] `selectinload` 임포트 추가 확인
- [ ] 로컬 테스트: coming-soon 태그 보유 상품 있으면 이벤트 생성 확인

---

## 검증

```bash
# shopify_drops 단독 실행
uv run python scripts/ingest_intel_events.py --job shopify_drops

# 결과 확인
sqlite3 data/fashion.db "
SELECT title, source_type, confidence, detected_at
FROM intel_events
WHERE layer='drops' AND source_type='crawler'
ORDER BY detected_at DESC
LIMIT 10;
"

# coming-soon 태그 상품 직접 확인
sqlite3 data/fashion.db "
SELECT p.name, p.tags, c.name as channel
FROM products p
JOIN channels c ON p.channel_id = c.id
WHERE p.tags LIKE '%coming%' AND p.is_active = 1
LIMIT 20;
"
```

> coming-soon 태그 상품이 현재 DB에 없어도 구현은 완료 가능. 실제 크롤 실행 후 태그 포함 상품이 들어오면 자동 감지됨.

---

## 참고

- `Product.tags` 필드: Shopify 태그를 콤마 구분 문자열로 저장 (예: `"streetwear,coming-soon,ss2026"`)
- `channel_type == "brand-store"` + `platform == "shopify"` 조건 필수 (edit-shop 제외)
- 기존 `_ingest_drops()` 함수: `Drop` 모델(수동 시드) 미러링 — 유지, 병행 운영
