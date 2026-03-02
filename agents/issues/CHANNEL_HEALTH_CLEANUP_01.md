# CHANNEL_HEALTH_CLEANUP_01: 크롤 불가 채널 자동 감지 + 비활성화 스크립트

**Task ID**: T-20260302-063
**Owner**: codex-dev
**Priority**: P2
**Labels**: backend, script, data-quality, maintenance

---

## 배경

CrawlRun #1 결과: 136채널 `not_supported`, 4채널 `timeout`.

이 중 상당수는:
- HTTP 404/410 → 스토어 자체가 사망
- 연속 크롤 실패 → 크롤 자체가 불가능한 구조
- platform=NULL + 제품 0개 + 오래된 채널 → 유효하지 않은 채널

이런 채널이 매 크롤에 포함되면:
- 불필요한 HTTP 요청으로 크롤 시간 증가
- 로그 노이즈 증가
- deadlock 위험 증가 (timeout 채널)

**해결**: 크롤 불가 채널을 자동 감지하고 `is_active=False`로 비활성화하는 스크립트.

---

## 요구사항

### 파일: `scripts/deactivate_dead_channels.py`

#### 비활성화 후보 기준 (OR 조건)

```python
CRITERIA = {
    # 기준 1: 최근 N회 crawl_channel_logs가 모두 'failed'
    "consecutive_failures": 3,

    # 기준 2: HTTP 메인 URL이 404/410 반환
    "dead_http_codes": {404, 410},

    # 기준 3: platform=NULL + 제품=0 + 오래된 채널
    "null_platform_age_days": 30,
}

# 안전장치: brand-store 채널은 제외
EXCLUDE_CHANNEL_TYPES = {"brand-store"}
```

#### CLI 인터페이스

```bash
# dry-run: 비활성화 후보 목록만 출력
uv run python scripts/deactivate_dead_channels.py --dry-run

# apply: is_active=False 처리
uv run python scripts/deactivate_dead_channels.py --apply

# HTTP 탐색 포함 (기준 2 활성화)
uv run python scripts/deactivate_dead_channels.py --dry-run --probe-http

# 특정 기준만 적용
uv run python scripts/deactivate_dead_channels.py --dry-run --criteria consecutive_failures
```

#### 구현 예시

```python
"""크롤 불가 채널 감지 + 비활성화 스크립트."""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from rich.console import Console
from rich.table import Table
from sqlalchemy import func, select, text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db
from fashion_engine.models.channel import Channel
from fashion_engine.models.crawl_run import CrawlChannelLog
from fashion_engine.models.product import Product

console = Console()


@dataclass
class DeadChannelCandidate:
    channel_id: int
    name: str
    url: str
    channel_type: str
    reason: str          # "consecutive_failures" | "dead_http" | "null_platform_stale"
    detail: str          # 상세 설명


async def _find_consecutive_failure_channels(
    db,
    min_failures: int = 3,
) -> list[DeadChannelCandidate]:
    """최근 N회 crawl_channel_logs가 모두 failed인 채널."""
    # 서브쿼리: 채널별 최근 N개 로그에서 failed 비율
    stmt = text("""
        SELECT c.id, c.name, c.url, c.channel_type,
               COUNT(*) as total_logs,
               SUM(CASE WHEN ccl.status = 'failed' THEN 1 ELSE 0 END) as failed_logs
        FROM channels c
        JOIN crawl_channel_logs ccl ON ccl.channel_id = c.id
        WHERE c.is_active = 1
          AND c.channel_type NOT IN ('brand-store')
          AND ccl.created_at >= datetime('now', '-30 days')
        GROUP BY c.id
        HAVING total_logs >= :min_failures
           AND failed_logs = total_logs
    """)
    rows = (await db.execute(stmt, {"min_failures": min_failures})).all()
    return [
        DeadChannelCandidate(
            channel_id=r.id,
            name=r.name,
            url=r.url,
            channel_type=r.channel_type,
            reason="consecutive_failures",
            detail=f"최근 {r.total_logs}회 모두 failed",
        )
        for r in rows
    ]


async def _find_null_platform_stale_channels(
    db,
    age_days: int = 30,
) -> list[DeadChannelCandidate]:
    """platform=NULL + 제품=0 + 생성 N일 이상 경과."""
    cutoff = datetime.utcnow() - timedelta(days=age_days)
    stmt = (
        select(
            Channel.id,
            Channel.name,
            Channel.url,
            Channel.channel_type,
            Channel.created_at,
            func.count(Product.id).label("product_count"),
        )
        .outerjoin(Product, (Product.channel_id == Channel.id) & (Product.is_active == True))
        .where(Channel.is_active == True)
        .where(Channel.platform.is_(None))
        .where(Channel.channel_type.notin_(["brand-store"]))
        .where(Channel.created_at < cutoff)
        .group_by(Channel.id)
        .having(func.count(Product.id) == 0)
    )
    rows = (await db.execute(stmt)).all()
    return [
        DeadChannelCandidate(
            channel_id=r.id,
            name=r.name,
            url=r.url,
            channel_type=r.channel_type,
            reason="null_platform_stale",
            detail=f"platform=NULL + 제품=0 + 생성 {age_days}일 이상",
        )
        for r in rows
    ]


async def _probe_http(
    candidates: list[DeadChannelCandidate],
) -> list[DeadChannelCandidate]:
    """HTTP 404/410 채널 추가 감지."""
    dead_http = []
    async with httpx.AsyncClient(follow_redirects=True) as client:
        sem = asyncio.Semaphore(10)
        async def _check(cand):
            async with sem:
                try:
                    resp = await client.get(cand.url, timeout=8)
                    if resp.status_code in {404, 410}:
                        return DeadChannelCandidate(
                            channel_id=cand.channel_id,
                            name=cand.name,
                            url=cand.url,
                            channel_type=cand.channel_type,
                            reason="dead_http",
                            detail=f"HTTP {resp.status_code}",
                        )
                except Exception:
                    pass
                return None

        results = await asyncio.gather(*[_check(c) for c in candidates])
        dead_http = [r for r in results if r]
    return dead_http


async def _apply_deactivation(candidates: list[DeadChannelCandidate]) -> int:
    """is_active=False 처리."""
    ids = [c.channel_id for c in candidates]
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("UPDATE channels SET is_active=0 WHERE id IN :ids"),
            {"ids": tuple(ids)},
        )
        await db.commit()
    return len(ids)
```

#### 출력 예시 (dry-run)

```
비활성화 후보: 12개
┌─────────────────────────────────────────────────────────────────┐
│ ID  │ 채널           │ 이유                    │ 상세            │
├─────┼────────────────┼─────────────────────────┼─────────────────┤
│  42 │ Harrods        │ consecutive_failures     │ 최근 3회 모두 failed │
│  71 │ A.A. Spectrum  │ consecutive_failures     │ 최근 3회 모두 failed │
│ 123 │ Mercari        │ null_platform_stale      │ platform=NULL + 제품=0 + 생성 45일 |
└─────┴────────────────┴─────────────────────────┴─────────────────┘
실행: --apply 추가 시 is_active=False 처리
```

---

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `scripts/deactivate_dead_channels.py` | 신규 작성 |
| `src/fashion_engine/models/channel.py` | Channel.is_active 필드 확인 |
| `src/fashion_engine/models/crawl_run.py` | CrawlChannelLog 쿼리 |

---

## 안전장치

1. `brand-store` 타입 채널은 절대 제외 (핵심 데이터 소스)
2. dry-run이 기본값 (`--apply` 명시 필요)
3. 후보 목록 출력 후 확인 프롬프트 (--apply 시)
4. 단일 채널 처리 불가 (최소 2개 채널 비활성화 시에만 실행)

---

## DoD (완료 기준)

- [ ] `scripts/deactivate_dead_channels.py` 존재
- [ ] `--dry-run` 기본값, `--apply` 명시 필요
- [ ] 기준 1: 최근 N회 연속 failed 채널 감지
- [ ] 기준 2 (`--probe-http`): HTTP 404/410 채널 감지
- [ ] 기준 3: platform=NULL + 제품=0 + 30일 이상 채널 감지
- [ ] brand-store 타입 자동 제외
- [ ] `--apply` 시 is_active=False 처리 + 변경 수 출력

## 검증

```bash
# dry-run 실행
uv run python scripts/deactivate_dead_channels.py --dry-run

# HTTP 탐색 포함
uv run python scripts/deactivate_dead_channels.py --dry-run --probe-http

# apply 실행
uv run python scripts/deactivate_dead_channels.py --apply

# 결과 확인
sqlite3 data/fashion.db "SELECT COUNT(*) FROM channels WHERE is_active=1;"
sqlite3 data/fashion.db "SELECT COUNT(*) FROM channels WHERE is_active=0;"
```
