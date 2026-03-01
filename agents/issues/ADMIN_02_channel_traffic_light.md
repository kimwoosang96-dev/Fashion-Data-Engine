# ADMIN_02: 채널 크롤 건강도 트래픽 라이트

**Task ID**: T-20260301-055
**Owner**: codex-dev
**Priority**: P1
**Labels**: backend, frontend, admin, data-quality

---

## 배경

현재 운영관리 "채널 관리" 탭의 헬스 표시는 단순 ok/needs_review 텍스트 배지뿐입니다.
`/crawl-status` 엔드포인트도 7일 기준 ok/stale/never만 판단하며 `CrawlChannelLog` 실패 이력을 반영하지 않습니다.

운영자가 **즉각적으로** 크롤 문제 채널을 파악할 수 있도록 트래픽 라이트(🔴🟡🟢)가 필요합니다.

**참고 파일**: `AGENTS.md`, `src/fashion_engine/api/admin.py`, `src/fashion_engine/models/crawl_run.py`

---

## 요구사항

### 1. 백엔드: 새 엔드포인트 `GET /admin/channel-signals`

**파일**: `src/fashion_engine/api/admin.py`

#### 응답 스키마 (dict per channel)

```python
{
    "channel_id": int,
    "name": str,
    "channel_type": str | None,
    "country": str | None,
    "product_count": int,
    "active_count": int,
    "inactive_count": int,
    "last_crawled_at": str | None,           # ISO 8601
    "crawl_status": "ok" | "stale" | "never",
    "recent_success_rate": float,            # 최근 5회 중 성공 비율 0.0~1.0
    "last_error_msg": str | None,            # 최근 failed 로그의 error_msg (max 200자)
    "traffic_light": "red" | "yellow" | "green",
}
```

#### SQL 전략 (SQLAlchemy async, SQLite 호환)

```python
from sqlalchemy import text

# Step 1: 기존 crawl-status 쿼리와 동일하게 채널 집계
rows = await db.execute(
    select(
        Channel.id,
        Channel.name,
        Channel.channel_type,
        Channel.country,
        func.count(Product.id).label("product_count"),
        func.count(case((Product.is_active == True, 1), else_=None)).label("active_count"),
        func.count(case((Product.is_active == False, 1), else_=None)).label("inactive_count"),
        func.max(Product.created_at).label("last_crawled_at"),
    )
    .outerjoin(Product, Product.channel_id == Channel.id)
    .group_by(Channel.id)
    .order_by(Channel.name.asc())
    .limit(limit)
    .offset(offset)
)

# Step 2: CrawlChannelLog에서 채널별 최근 5개 로그 (ROW_NUMBER 윈도우 함수)
recent_logs_rows = await db.execute(
    text("""
        SELECT channel_id, status, error_msg, crawled_at
        FROM (
            SELECT channel_id, status, error_msg, crawled_at,
                   ROW_NUMBER() OVER (PARTITION BY channel_id ORDER BY crawled_at DESC) AS rn
            FROM crawl_channel_logs
        ) sub
        WHERE rn <= 5
    """)
)
# channel_id → list[row] 딕셔너리로 변환
from collections import defaultdict
logs_by_channel: dict[int, list] = defaultdict(list)
for log in recent_logs_rows:
    logs_by_channel[log.channel_id].append(log)
```

#### 트래픽 라이트 판정 함수

```python
def _compute_traffic_light(
    crawl_status: str,
    recent_logs: list,       # CrawlChannelLog-like rows, ordered desc by crawled_at
    inactive_rate: float,
) -> str:
    # RED 조건
    if crawl_status == "never":
        return "red"
    last_3 = recent_logs[:3]
    if len(last_3) >= 3 and all(l.status == "failed" for l in last_3):
        return "red"
    if crawl_status == "stale" and inactive_rate >= 0.8:
        return "red"
    # YELLOW 조건
    if crawl_status == "stale":
        return "yellow"
    if any(l.status == "failed" for l in recent_logs):
        return "yellow"
    if inactive_rate >= 0.5:
        return "yellow"
    # GREEN
    return "green"
```

#### 엔드포인트 전체 구조

```python
@router.get("/channel-signals")
async def get_channel_signals(
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # ... (위 SQL 전략 실행)
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    payload = []
    for row in rows:
        product_count = int(row.product_count or 0)
        active_count = int(row.active_count or 0)
        inactive_count = int(row.inactive_count or 0)

        last = row.last_crawled_at
        if last is None:
            crawl_status = "never"
        else:
            dt = last if last.tzinfo else last.replace(tzinfo=timezone.utc)
            crawl_status = "stale" if dt < stale_cutoff else "ok"

        channel_logs = logs_by_channel.get(row.id, [])
        inactive_rate = (inactive_count / product_count) if product_count > 0 else 0.0
        success_count = sum(1 for l in channel_logs if l.status == "success")
        recent_success_rate = (success_count / len(channel_logs)) if channel_logs else 0.0

        # 최근 failed 로그의 error_msg
        last_error = next((l.error_msg for l in channel_logs if l.status == "failed"), None)

        traffic_light = _compute_traffic_light(crawl_status, channel_logs, inactive_rate)

        payload.append({
            "channel_id": row.id,
            "name": row.name,
            "channel_type": row.channel_type,
            "country": row.country,
            "product_count": product_count,
            "active_count": active_count,
            "inactive_count": inactive_count,
            "last_crawled_at": last.isoformat() if last else None,
            "crawl_status": crawl_status,
            "recent_success_rate": round(recent_success_rate, 2),
            "last_error_msg": (last_error or "")[:200] if last_error else None,
            "traffic_light": traffic_light,
        })
    return payload
```

---

### 2. 프론트엔드: `frontend/src/lib/types.ts`에 타입 추가

```typescript
export interface ChannelSignalOut {
  channel_id: number;
  name: string;
  channel_type: string | null;
  country: string | null;
  product_count: number;
  active_count: number;
  inactive_count: number;
  last_crawled_at: string | null;
  crawl_status: "ok" | "stale" | "never";
  recent_success_rate: number;
  last_error_msg: string | null;
  traffic_light: "red" | "yellow" | "green";
}
```

---

### 3. 프론트엔드: `frontend/src/lib/api.ts`에 함수 추가

기존 `adminFetch` 헬퍼 사용:

```typescript
import type { ..., ChannelSignalOut } from "./types";

export const getChannelSignals = (token: string, limit = 500) =>
  adminFetch<ChannelSignalOut[]>(`/admin/channel-signals?limit=${limit}`, token);
```

---

### 4. 프론트엔드: `frontend/src/app/admin/page.tsx` 수정

**"채널 관리" 탭** 수정 — `getAdminChannelsHealth()` 호출을 `getChannelSignals()`로 교체:

#### TrafficLight 컴포넌트 (파일 상단 또는 별도 인라인 컴포넌트)

```tsx
const TrafficLight = ({ signal }: { signal: "red" | "yellow" | "green" }) => (
  <span
    className={`inline-block w-2.5 h-2.5 rounded-full shrink-0 ${
      signal === "red"
        ? "bg-red-500"
        : signal === "yellow"
        ? "bg-amber-400"
        : "bg-emerald-500"
    }`}
  />
);
```

#### 채널 목록 테이블 변경 포인트

1. 상태 변수 타입: `channelsHealth` → `ChannelSignalOut[]`
2. 데이터 fetch: `getAdminChannelsHealth(token)` → `getChannelSignals(token)`
3. 헬스 배지 컬럼 → 트래픽 라이트 도트 + 텍스트:

```tsx
{/* 기존 health 배지 대체 */}
<td className="px-4 py-3">
  <div className="flex items-center gap-2">
    <TrafficLight signal={ch.traffic_light} />
    <span className={`text-xs font-medium ${
      ch.traffic_light === "red" ? "text-red-600" :
      ch.traffic_light === "yellow" ? "text-amber-600" : "text-emerald-700"
    }`}>
      {ch.traffic_light === "red" ? "RED" : ch.traffic_light === "yellow" ? "YELLOW" : "GREEN"}
    </span>
  </div>
  {(ch.traffic_light === "red" || ch.traffic_light === "yellow") && ch.last_error_msg && (
    <p className="text-xs text-gray-400 mt-0.5 truncate max-w-[200px]" title={ch.last_error_msg}>
      {ch.last_error_msg.slice(0, 60)}{ch.last_error_msg.length > 60 ? "…" : ""}
    </p>
  )}
</td>
```

4. `크롤 성공률` 열 추가 (테이블 헤더 + 각 행):

```tsx
{/* 테이블 헤더에 추가 */}
<th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">크롤 성공률</th>

{/* 각 행에 추가 */}
<td className="px-4 py-3 text-sm text-gray-600">
  {ch.crawl_status === "never" ? "-" : `${Math.round(ch.recent_success_rate * 100)}%`}
</td>
```

5. `crawl_status` 배지도 그대로 유지 (ok/stale/never):

```tsx
<span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
  ch.crawl_status === "ok" ? "bg-green-100 text-green-700" :
  ch.crawl_status === "stale" ? "bg-yellow-100 text-yellow-700" :
  "bg-gray-100 text-gray-500"
}`}>
  {ch.crawl_status}
</span>
```

---

## DoD (완료 기준)

- [ ] `GET /admin/channel-signals` 엔드포인트 존재, 인증 필요
- [ ] 응답에 `traffic_light: "red" | "yellow" | "green"` 필드 포함
- [ ] 응답에 `recent_success_rate` (0.0~1.0), `last_error_msg` 필드 포함
- [ ] 프론트엔드 "채널 관리" 탭에 트래픽 라이트 도트 + 텍스트 표시
- [ ] red/yellow 채널에서 `last_error_msg` (max 60자) 표시
- [ ] `크롤 성공률` 열 추가
- [ ] TypeScript 타입 오류 없음 (`tsc --noEmit`)

## 검증

```bash
# 백엔드 검증
curl "http://localhost:8000/admin/channel-signals?limit=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.[].traffic_light'
# → "red" / "yellow" / "green" 값들 확인

# RED 채널 조회
curl "http://localhost:8000/admin/channel-signals?limit=500" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '[.[] | select(.traffic_light == "red")] | length'

# TypeScript 타입 체크
cd frontend && node_modules/.bin/tsc --noEmit
```

## 참고: 위치 찾기

```bash
# 기존 channels-health 엔드포인트 위치
grep -n "channels-health\|crawl-status" src/fashion_engine/api/admin.py

# CrawlChannelLog 모델 필드 확인
grep -n "class CrawlChannelLog\|status\|error_msg\|crawled_at" src/fashion_engine/models/crawl_run.py

# 프론트엔드 기존 채널 관리 탭 위치
grep -n "channelsHealth\|channels-health\|채널 관리" frontend/src/app/admin/page.tsx
```
