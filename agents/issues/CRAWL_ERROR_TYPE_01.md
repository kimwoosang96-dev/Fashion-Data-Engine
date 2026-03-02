# CRAWL_ERROR_TYPE_01: CrawlChannelLog error_type 필드 추가

**Task ID**: T-20260302-059
**Owner**: codex-dev
**Priority**: P2
**Labels**: backend, database, admin

---

## 배경

`CrawlChannelLog.error_msg`는 현재 자유형식 문자열입니다.
운영관리 어드민에서 에러 유형별 필터링·집계가 불가능합니다.
표준화된 `error_type` 필드를 추가해 `channel-signals` API에 노출합니다.

**참고 파일**: `AGENTS.md`, `src/fashion_engine/models/crawl_run.py`, `src/fashion_engine/api/admin.py`, `src/fashion_engine/crawler/product_crawler.py`

---

## 요구사항

### 1. `CrawlChannelLog` 모델 필드 추가

**파일**: `src/fashion_engine/models/crawl_run.py`

```python
class CrawlChannelLog(Base):
    ...
    error_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )
    # 가능한 값:
    # "http_403"       — 403 Forbidden
    # "http_404"       — 404 Not Found
    # "http_429"       — 429 Too Many Requests
    # "http_5xx"       — 500/502/503 등 서버 에러
    # "timeout"        — 요청 타임아웃
    # "parse_error"    — JSON/HTML 파싱 실패
    # "not_supported"  — 플랫폼 미지원 (Cafe24 아님, Shopify 아님)
    # "zero_products"  — 크롤 성공했으나 제품 0개
    # None             — 에러 없음 (success/skipped)
```

### 2. Alembic 마이그레이션

```python
# alembic/versions/xxxx_add_error_type_to_crawl_channel_log.py
def upgrade():
    op.add_column(
        "crawl_channel_logs",
        sa.Column("error_type", sa.String(30), nullable=True)
    )

def downgrade():
    op.drop_column("crawl_channel_logs", "error_type")
```

### 3. `crawl_channel()` 함수에서 error_type 분류

**파일**: `src/fashion_engine/crawler/product_crawler.py`

크롤 실패 시 에러 유형 분류:

```python
def _classify_error(exc: Exception, http_status: int | None = None) -> str:
    if http_status == 403:
        return "http_403"
    if http_status == 404:
        return "http_404"
    if http_status == 429:
        return "http_429"
    if http_status and http_status >= 500:
        return "http_5xx"
    if isinstance(exc, (httpx.TimeoutException, asyncio.TimeoutError)):
        return "timeout"
    if isinstance(exc, (json.JSONDecodeError, ValueError, KeyError)):
        return "parse_error"
    return "parse_error"  # 기본값
```

`CrawlChannelLog` 저장 시 `error_type` 포함:

```python
log = CrawlChannelLog(
    run_id=run_id,
    channel_id=channel_id,
    status="failed",
    error_msg=str(exc)[:500],
    error_type=_classify_error(exc, http_status),
    ...
)
```

### 4. `/admin/channel-signals` 응답에 `error_type` 필드 추가

**파일**: `src/fashion_engine/api/admin.py`

```python
# 응답 payload에 추가
"error_type": last_error_type,  # 최근 failed 로그의 error_type

# last_error_type 계산
last_error_type = next(
    (l.error_type for l in channel_logs if l.status == "failed"), None
)
```

### 5. `ChannelSignalOut` 스키마 업데이트

**파일**: `src/fashion_engine/api/schemas.py` (또는 `admin.py` 내 Pydantic 스키마)

```python
class ChannelSignalOut(BaseModel):
    ...
    error_type: str | None = None  # 신규 필드
```

### 6. 프론트엔드 타입 업데이트

**파일**: `frontend/src/lib/types.ts`

```typescript
export interface ChannelSignalOut {
  ...
  error_type: string | null;  // 신규 필드
}
```

어드민 채널 테이블에서 `error_type` 뱃지 표시 (선택):
- `http_403` → 회색 "403"
- `http_429` → 주황 "429"
- `timeout` → 노랑 "TO"
- `parse_error` → 빨강 "ERR"

---

## DoD (완료 기준)

- [ ] `CrawlChannelLog.error_type` 필드 존재
- [ ] Alembic 마이그레이션 적용 (`alembic upgrade head`)
- [ ] 크롤 실패 시 `error_type` 자동 분류 및 저장
- [ ] `/admin/channel-signals` 응답에 `error_type` 포함
- [ ] `ChannelSignalOut` TypeScript 타입에 `error_type` 추가
- [ ] TypeScript 타입 체크 통과 (`tsc --noEmit`)

## 검증

```bash
# 마이그레이션 적용
uv run alembic upgrade head

# 스키마 확인
sqlite3 data/fashion.db "PRAGMA table_info(crawl_channel_logs)"
# → error_type 컬럼 존재

# API 응답 확인
curl "http://localhost:8000/admin/channel-signals?limit=5" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.[].error_type'

# TypeScript 타입 체크
cd frontend && node_modules/.bin/tsc --noEmit
```
