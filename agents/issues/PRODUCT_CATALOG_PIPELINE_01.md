# PRODUCT_CATALOG_PIPELINE_01: ProductCatalog 자동 빌드 파이프라인

**Task ID**: T-20260302-058
**Owner**: codex-dev
**Priority**: P2
**Labels**: backend, script, data-quality

---

## 배경

`build_product_catalog.py`는 현재 수동 실행 전용입니다.
전체 크롤이 완료될 때마다 catalog를 자동으로 증분 갱신하는 파이프라인이 필요합니다.

**참고 파일**: `AGENTS.md`, `scripts/build_product_catalog.py`, `scripts/crawl_products.py`, `src/fashion_engine/models/product_catalog.py`

---

## 요구사항

### 1. `build_product_catalog.py`에 `--since` 옵션 추가

**목적**: 증분 업데이트 — 특정 시각 이후에 updated_at이 변경된 products만 처리

```bash
# 전체 빌드 (기존)
uv run python scripts/build_product_catalog.py --apply

# 증분 빌드 (최근 24시간)
uv run python scripts/build_product_catalog.py --apply --since "2026-03-01T00:00:00"

# 크롤 완료 시점 기준 자동 증분 (인수 없이 호출 시 마지막 CrawlRun 완료 시각 기준)
uv run python scripts/build_product_catalog.py --apply --since-last-crawl
```

#### 증분 모드 SQL 변경

```python
# --since 모드: 해당 시각 이후 updated_at 제품의 normalized_key만 대상
if since:
    where_clause = f"""
        WHERE COALESCE(p.normalized_key, p.product_key) IN (
            SELECT DISTINCT COALESCE(normalized_key, product_key)
            FROM products
            WHERE updated_at > '{since}'
              AND COALESCE(normalized_key, product_key) IS NOT NULL
        )
    """
```

---

### 2. `crawl_products.py`에 크롤 완료 후 catalog 증분 빌드 훅 추가

**파일**: `scripts/crawl_products.py`

크롤 완료 이후 자동 호출:

```python
# crawl_products.py 크롤 완료 후 (main() 함수 끝)
if not args.skip_catalog:
    logger.info("▶ ProductCatalog 증분 빌드 시작...")
    from fashion_engine.services.catalog_service import build_catalog_incremental
    await build_catalog_incremental(since=crawl_run.started_at)
    logger.info("✅ ProductCatalog 증분 빌드 완료")
```

CLI 옵션 추가:

```bash
# catalog 빌드 건너뜀 (디버그용)
uv run python scripts/crawl_products.py --skip-catalog
```

---

### 3. `src/fashion_engine/services/catalog_service.py` 서비스 레이어 추출

**목적**: `build_product_catalog.py`의 핵심 로직을 서비스 함수로 추출해 `crawl_products.py`와 API에서 재사용 가능하게 함

```python
# catalog_service.py

async def build_catalog_full(db: AsyncSession, batch_size: int = 1000) -> int:
    """전체 product_catalog 재빌드. 반환값: 처리된 레코드 수."""
    ...

async def build_catalog_incremental(
    since: datetime, batch_size: int = 1000
) -> int:
    """지정 시각 이후 변경된 제품만 catalog 갱신. 반환값: 처리된 레코드 수."""
    async with AsyncSessionLocal() as db:
        ...
```

---

### 4. `GET /admin/catalog-stats` 엔드포인트 추가 (선택)

**파일**: `src/fashion_engine/api/admin.py`

```python
@router.get("/catalog-stats")
async def get_catalog_stats(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """ProductCatalog 현황 요약."""
    return {
        "total": ...,
        "with_brand": ...,
        "multi_channel": ...,
        "last_updated": ...,
    }
```

---

## DoD (완료 기준)

- [ ] `scripts/build_product_catalog.py --since` 옵션 작동
- [ ] `scripts/build_product_catalog.py --since-last-crawl` 옵션 작동 (마지막 CrawlRun 완료 시각 조회)
- [ ] `scripts/crawl_products.py` 완료 후 자동 증분 빌드 호출
- [ ] `scripts/crawl_products.py --skip-catalog` 옵션으로 건너뜀 가능
- [ ] `src/fashion_engine/services/catalog_service.py` 존재 (`build_catalog_full`, `build_catalog_incremental`)

## 검증

```bash
# 증분 빌드 테스트 (최근 1시간)
uv run python scripts/build_product_catalog.py --apply \
  --since "$(date -v-1H +%Y-%m-%dT%H:%M:%S)"

# 크롤 + 자동 증분 빌드
uv run python scripts/crawl_products.py --limit 2

# catalog 수 확인
sqlite3 data/fashion.db "SELECT COUNT(*) FROM product_catalog"
```
