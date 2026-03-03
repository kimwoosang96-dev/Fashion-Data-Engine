# T-078 | INTEL_CRAWL_AUTO_TRIGGER_01

> **목적**: `crawl_products.py` 완료 후 intel derived 이벤트 자동 트리거
> **우선순위**: P1 | **담당**: codex-dev

---

## 배경

현재 `crawl_products.py`는 제품 크롤 중 sale_start/sold_out/restock 파생 이벤트를 `upsert_derived_product_event()`로 생성한다. 그런데 `derived_spike` 잡(브랜드 세일 급증 감지)은 별도 스케줄(07:30)에만 실행 — 크롤이 낮에 완료되어도 다음날 아침까지 sales_spike 이벤트가 생성되지 않음.

또한 Railway 스케줄러의 크롤 주기(03:00)와 intel_ingest(07:30) 사이 4시간 30분 공백 존재.

---

## 구현 요구사항

### Step 1: `scripts/crawl_products.py` — 크롤 완료 후 intel spike 자동 실행

`main()` 함수 맨 마지막 (CrawlRun 완료 처리 직후)에 추가:

```python
# crawl_products.py: main() 완료 직전

# Intel derived_spike 자동 트리거 (--no-intel 플래그로 비활성화 가능)
if not args.no_intel and total_upserted > 0:
    try:
        logger.info("[INTEL] 크롤 완료 → derived_spike 자동 실행")
        import sys as _sys
        from pathlib import Path as _Path
        _sys.path.insert(0, str(_Path(__file__).parent.parent / "src"))
        import ingest_intel_events
        result_code = await ingest_intel_events.run(job="derived_spike", window_hours=48)
        logger.info("[INTEL] derived_spike 완료 code=%s", result_code)
    except Exception as e:
        logger.warning("[INTEL] derived_spike 자동 실행 실패 (무시): %s", e)
```

**`--no-intel` 플래그 추가**:

`crawl_products.py`의 argparse(또는 typer) 파싱부에 추가:
```python
parser.add_argument(
    "--no-intel",
    action="store_true",
    default=False,
    help="크롤 완료 후 intel derived_spike 자동 실행 비활성화",
)
```

> **중요**: intel 실행 실패가 크롤 전체를 실패시키면 안 됨 → try/except로 감싸고 경고 로그만 출력.

---

### Step 2: `scripts/crawl_products.py` — mirror ingest도 연계

크롤 완료 후 새 제품/가격이 생겼으므로, sale_start 이벤트도 mirror ingest 실행하면 즉시 반영:

```python
# derived_spike 직후에 mirror도 실행
if not args.no_intel and total_upserted > 0:
    try:
        await ingest_intel_events.run(job="mirror")
    except Exception as e:
        logger.warning("[INTEL] mirror 자동 실행 실패: %s", e)
```

---

### Step 3: `scripts/scheduler.py` — 크롤 완료 훅 확인

Railway 스케줄러는 `crawl_products.py`를 서브프로세스로 실행하므로 `--no-intel` 플래그 없이 실행하면 자동으로 intel이 트리거됨.
Makefile의 `crawl` 타깃에도 `--no-intel` 없이 그대로 두어야 함.

스케줄러에서 별도로 intel 잡을 추가로 돌리는 건 T-077에서 처리 (derived_spike 4회/일). 크롤 완료 후 자동 트리거는 중복이지만 짧은 시간 내 2회 실행은 dedup_key로 중복 방지됨.

---

### Step 4: `ingest_intel_events.py` 재진입 안전성 확인

`run()` 함수가 동시 호출되어도 안전한지 확인:
- `IntelIngestRun` 레코드는 각 호출마다 독립 생성됨 ✅
- `dedup_key` 기반 중복 방지 ✅
- 추가 작업 불필요

---

## DoD

- [ ] `crawl_products.py`에 `--no-intel` argparse 플래그 추가
- [ ] `crawl_products.py` 크롤 완료 후 `derived_spike` 자동 실행 (try/except 보호)
- [ ] `crawl_products.py` 크롤 완료 후 `mirror` 자동 실행 (try/except 보호)
- [ ] `total_upserted == 0`이면 intel 트리거 스킵 (변경 없는 경우 불필요)
- [ ] `uv run python scripts/crawl_products.py --limit 2` 실행 후 intel 자동 트리거 로그 확인
- [ ] `uv run python scripts/crawl_products.py --limit 2 --no-intel` → intel 트리거 없음 확인

---

## 검증

```bash
# 크롤 실행 (--limit 2로 빠르게 테스트)
uv run python scripts/crawl_products.py --limit 2

# 로그에서 intel 트리거 확인
grep -i "intel" logs/crawl_*.log | tail -10

# intel_events에 최신 이벤트 생성 확인
sqlite3 data/fashion.db "
SELECT event_type, COUNT(*) as n, MAX(detected_at) as latest
FROM intel_events
WHERE detected_at >= datetime('now', '-1 hour')
GROUP BY event_type;
"

# --no-intel 플래그 테스트
uv run python scripts/crawl_products.py --limit 1 --no-intel
# → "[INTEL]" 로그 없어야 함
```

---

## 참고

- `crawl_products.py`의 현재 argparse 위치 확인 후 플래그 추가
- `ingest_intel_events.run()` 시그니처: `async def run(job: str, window_hours: int = 48) -> int`
- Railway 환경: `INTEL_INGEST_ENABLED=true` 설정 필요 (현재 false일 수 있음)
  → Railway Variables에서 `INTEL_INGEST_ENABLED=true` 설정 확인/추가 요청
