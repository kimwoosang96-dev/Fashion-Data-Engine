# CRAWLER_01: 자동 크롤 스케줄러 (일 1회 가격 업데이트)

**Task ID**: T-20260228-001
**Owner**: codex-dev
**Priority**: P1
**Labels**: backend, crawler, automation

---

## 배경

현재 제품·가격 크롤은 수동 실행(`uv run python scripts/crawl_products.py`)에 의존함.
80,096개 제품 데이터가 쌓인 지금, 가격 데이터를 매일 자동 갱신하지 않으면 세일 탐지와 가격 비교 기능이 무의미해짐.

> 참고: `AGENTS.md` → Data Pipeline, scripts/crawl_products.py

---

## 요구사항

- [ ] `scripts/scheduler.py` 신규 스크립트 작성
- [ ] APScheduler 사용: `pip install apscheduler` (uv 추가 필요)
- [ ] 스케줄: 매일 새벽 3시 (KST) 전체 채널 제품 크롤
- [ ] 스케줄: 매일 오전 7시 환율 업데이트
- [ ] 스케줄: 매일 오전 7시 10분 드롭 크롤
- [ ] 실행 중 에러는 로그 파일(`logs/scheduler.log`)에 기록, 프로세스 종료하지 않음
- [ ] `--dry-run` 플래그: 스케줄 등록만 하고 즉시 실행 안 함 (테스트용)

---

## 기술 스펙

**신규 파일**: `scripts/scheduler.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

# 환율: 매일 07:00
scheduler.add_job(run_exchange_rates, CronTrigger(hour=7, minute=0))

# 드롭 크롤: 매일 07:10
scheduler.add_job(run_drop_crawl, CronTrigger(hour=7, minute=10))

# 제품 크롤: 매일 03:00 (WatchList 알림 포함)
scheduler.add_job(run_product_crawl, CronTrigger(hour=3, minute=0))
```

**pyproject.toml에 의존성 추가**:
```toml
"apscheduler>=3.10",
```

**실행 방법**:
```bash
uv run python scripts/scheduler.py           # 스케줄러 시작 (프로세스 유지)
uv run python scripts/scheduler.py --dry-run  # 스케줄 확인만
```

**재사용할 기존 스크립트**:
- `scripts/crawl_products.py` — 메인 크롤 로직
- `scripts/update_exchange_rates.py`
- `scripts/crawl_drops.py`

---

## 완료 조건

- [ ] `uv run python scripts/scheduler.py --dry-run` 실행 후 스케줄 3개 출력
- [ ] `logs/` 디렉터리 자동 생성
- [ ] `.env.example`에 `TZ=Asia/Seoul` 항목 추가
- [ ] `AGENTS.md` Data Pipeline 섹션에 scheduler 실행 방법 추가

---

## 참고

- `AGENTS.md` → Data Pipeline, Coding Conventions
- APScheduler docs: https://apscheduler.readthedocs.io
- 기존 async 패턴: `scripts/crawl_products.py` (asyncio.run 방식)
