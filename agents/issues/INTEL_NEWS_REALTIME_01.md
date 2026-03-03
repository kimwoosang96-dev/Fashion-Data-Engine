# T-077 | INTEL_NEWS_REALTIME_01

> **목적**: 뉴스 수집 주기를 하루 1회 → 6시간마다 4회로 강화, 한국 패션 매체 RSS 4개 추가
> **우선순위**: P1 | **담당**: codex-dev

---

## 배경

현재 `crawl_news.py` + `ingest_intel_events.py --job mirror`는 07:00/07:30 하루 1회 실행.
뉴스는 낮~저녁에도 계속 올라오지만 다음날 07:00까지 수집 안 됨 → intel 피드가 최대 24시간 오래된 정보만 표시.
또한 RSS 소스가 영문 4개(Hypebeast·Highsnobiety·SneakerNews·Complex)뿐 — 한국 패션 매체 없음.

---

## 구현 요구사항

### Step 1: `scripts/crawl_news.py` — 한국 매체 RSS 추가

`RSS_FEEDS` 리스트에 한국 패션 매체 추가:

```python
RSS_FEEDS = [
    # 영문 (기존 유지)
    "https://hypebeast.com/feed",
    "https://www.highsnobiety.com/feed/",
    "https://sneakernews.com/feed/",
    "https://www.complex.com/style/rss",
    # 한국 추가
    "https://hypebeast.kr/feed",          # Hypebeast 한국판
    "https://www.vogue.co.kr/feed/",      # 보그 코리아
    "https://www.wkorea.com/rss/rss.asp", # W Korea
    "https://magazine.boon.so/rss",       # Boon 매거진 (스트리트 패션)
]
```

> **주의**: 각 RSS URL은 실제로 응답하는지 확인 후 추가. 404 응답 시 해당 URL 제외하고 대체 URL 탐색.
> `feedparser.parse(url)` 결과의 `bozo` 값이 True이면 파싱 오류 — 해당 피드 스킵 처리 추가.

---

### Step 2: `scripts/scheduler.py` — 수집 주기 4회/일로 변경

**기존 구조** (제거 대상):
```python
# 07:00 뉴스 크롤
scheduler.add_job(run_news_job, CronTrigger(hour=7, minute=0), ...)
# 07:30 intel ingest (mirror + spike 통합)
scheduler.add_job(run_intel_ingest_job, CronTrigger(hour=7, minute=30), id="intel_ingest_0730")
```

**변경 후**:
```python
# 뉴스 크롤: 00:00 / 06:00 / 12:00 / 18:00 (4회/일)
scheduler.add_job(
    run_news_job,
    CronTrigger(hour="0,6,12,18", minute=0),
    id="news_4x_daily",
    replace_existing=True,
)

# intel mirror ingest: 뉴스 크롤 10분 후 (00:10 / 06:10 / 12:10 / 18:10)
scheduler.add_job(
    run_intel_mirror_job,          # ← 새 함수 (mirror 잡만 실행)
    CronTrigger(hour="0,6,12,18", minute=10),
    id="intel_mirror_4x_daily",
    replace_existing=True,
)

# derived_spike: 독립 주기 (03:00 / 09:00 / 15:00 / 21:00)
scheduler.add_job(
    run_intel_spike_job,           # ← 새 함수 (derived_spike 잡만 실행)
    CronTrigger(hour="3,9,15,21", minute=0),
    id="intel_spike_4x_daily",
    replace_existing=True,
)
```

`run_intel_mirror_job` 신규 함수:
```python
async def run_intel_mirror_job() -> None:
    if not settings.intel_ingest_enabled:
        LOGGER.info("[JOB] intel-mirror skipped (INTEL_INGEST_ENABLED=false)")
        return
    try:
        LOGGER.info("[JOB] intel-mirror started")
        code = await ingest_intel_events.run(job="mirror")
        LOGGER.info("[JOB] intel-mirror completed code=%s", code)
    except Exception:
        LOGGER.exception("[JOB] intel-mirror failed")

async def run_intel_spike_job() -> None:
    if not settings.intel_ingest_enabled:
        return
    try:
        LOGGER.info("[JOB] intel-spike started")
        code = await ingest_intel_events.run(job="derived_spike", window_hours=48)
        LOGGER.info("[JOB] intel-spike completed code=%s", code)
    except Exception:
        LOGGER.exception("[JOB] intel-spike failed")
```

기존 `intel_ingest_0730` 잡 및 `run_intel_ingest_job` 함수 제거.

---

## DoD

- [ ] `RSS_FEEDS`에 한국 매체 4개 추가 (응답 확인 후)
- [ ] feedparser `bozo` 오류 스킵 처리 추가
- [ ] 스케줄러 뉴스 크롤 4회/일 변경 (`news_4x_daily`)
- [ ] 스케줄러 intel mirror 4회/일 변경 (`intel_mirror_4x_daily`)
- [ ] 스케줄러 intel spike 4회/일 분리 (`intel_spike_4x_daily`)
- [ ] 기존 `intel_ingest_0730` 잡 + `run_intel_ingest_job` 함수 제거
- [ ] `uv run python scripts/crawl_news.py --per-feed 5` 실행 후 한국 매체 기사 수집 확인

---

## 검증

```bash
# 뉴스 크롤 테스트 (피드당 5건)
uv run python scripts/crawl_news.py --per-feed 5

# DB에서 한국 매체 기사 확인
sqlite3 data/fashion.db "
SELECT source_domain, COUNT(*) as n
FROM fashion_news
GROUP BY source_domain
ORDER BY n DESC
LIMIT 20;
"

# intel mirror ingest 테스트
uv run python scripts/ingest_intel_events.py --job mirror

# intel_events에서 뉴스 이벤트 확인
sqlite3 data/fashion.db "
SELECT layer, COUNT(*) as n, MAX(detected_at) as latest
FROM intel_events
GROUP BY layer;
"
```

---

## 참고

- 기존 파일: `scripts/crawl_news.py` (141줄), `scripts/scheduler.py`
- 스케줄러 함수명 패턴: `run_*_job()` async 함수
- `INTEL_INGEST_ENABLED` 환경변수 gate 반드시 유지
