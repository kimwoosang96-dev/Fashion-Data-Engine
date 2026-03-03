# 배포 가이드 (Railway + Vercel)

## 1) 백엔드 Railway (Web Service)

- 서비스 타입: `Web Service`
- 리포지토리 루트 사용
- Start Command: `uv run uvicorn fashion_engine.api.main:app --host 0.0.0.0 --port ${PORT}`
- Health Check Path: `/health`
- 배포 설정 파일: `railway.json`

필수 환경변수:

- `DATABASE_URL=postgresql+asyncpg://...`
- `CORS_ALLOWED_ORIGINS=https://fashion-data-engine.vercel.app`
- `API_DEBUG=false`
- `ADMIN_BEARER_TOKEN=<strong-token>`

선택 환경변수:

- `DISCORD_WEBHOOK_URL=<webhook>` — 크롤/세일 알림
- `INTEL_DISCORD_WEBHOOK_URL=<webhook>` — intel 전용 Discord 알림
- `INTEL_INGEST_ENABLED=true`

## 2) Railway Worker (자동 크롤 스케줄러)

- 서비스 타입: `Worker`
- 같은 리포지토리/브랜치 사용
- Start Command: `uv run python scripts/scheduler.py`
- Worker는 HTTP 포트를 열 필요가 없음

필수 환경변수:

- `DATABASE_URL=postgresql+asyncpg://...`
- `TZ=Asia/Seoul`
- `INTEL_INGEST_ENABLED=true`

선택 환경변수:

- `DISCORD_WEBHOOK_URL=<webhook>` — 데이터 감사 알림
- `INTEL_DISCORD_WEBHOOK_URL=<webhook>` — intel critical/high 이벤트 즉시 알림
- `CRAWLER_DELAY_SECONDS=2.0`
- `CRAWLER_MAX_RETRIES=3`

자동 스케줄:

| 시간 | 작업 |
|------|------|
| 03:00 | 전체 제품 크롤 + intel 자동 트리거 |
| 00/06/12/18:00 | 뉴스 수집 (영문 4 + 한국 4) |
| 00/06/12/18:10 | Intel mirror (drops/collabs/news) |
| 03/09/15/21:00 | Intel spike (세일 급증 감지) |
| 07:00 | 환율 업데이트 |
| 매주 일요일 09:00 | 데이터 감사 |

로컬 검증:

```bash
make scheduler-dry
```

## 2-1) 초기 배포 후 환율 업데이트 필수

최초 배포 직후에는 환율 테이블이 비어 있을 수 있으므로, 아래 명령을 1회 실행해야 합니다.

```bash
make update-rates
```

권장: Worker 스케줄에 `update_exchange_rates.py`를 매일 1회 포함해 최신 환율을 유지합니다.

## 3) 프론트엔드 Vercel

- 루트 디렉터리: `frontend/`
- 설정 파일: `frontend/vercel.json`
- 환경변수:
  - `NEXT_PUBLIC_API_URL=https://<railway-backend-domain>`

## 4) SQLite -> PostgreSQL 시드 이전

`products/price_history/drops/purchases/watchlist/fashion_news` 는 제외하고,
시드 성격의 테이블만 이전합니다.

Dry-run:

```bash
uv run python scripts/migrate_sqlite_to_pg.py --dry-run
```

실행:

```bash
uv run python scripts/migrate_sqlite_to_pg.py \
  --target-url postgresql+asyncpg://fashion:password@localhost:5432/fashion_db
```

이후 제품 데이터는 크롤러로 재적재합니다.
