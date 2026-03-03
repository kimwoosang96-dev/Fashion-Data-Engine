# T-080 | INTEL_DISCORD_ALERT_01

> **목적**: Intel Hub critical/high severity 이벤트 생성 시 Discord webhook으로 즉시 알림 발송
> **우선순위**: P2 | **담당**: codex-dev

---

## 배경

Intel Hub 이벤트가 생성돼도 사용자가 `/intel` 페이지를 직접 열어봐야만 확인 가능.
critical/high severity 이벤트(세일 급등, 드롭 예고, 재입고 등)는 즉시 알림이 필요.
기존 `alert_service.py`의 Discord webhook과 별도로, intel 전용 webhook 채널을 분리 운영.

---

## 구현 요구사항

### Step 1: `src/fashion_engine/services/intel_service.py` — `notify_discord_if_warranted()` 추가

```python
import httpx
from fashion_engine.config import settings

LAYER_EMOJI = {
    "drops": "🚀",
    "collabs": "🤝",
    "news": "📰",
    "sale_start": "🔥",
    "sold_out": "⚫",
    "restock": "🟢",
    "sales_spike": "📈",
}

async def notify_discord_if_warranted(event: IntelEvent) -> None:
    """severity=critical/high 이벤트를 Discord webhook으로 즉시 발송."""
    if event.severity not in {"critical", "high"}:
        return
    if not settings.intel_discord_webhook_url:
        return

    emoji = LAYER_EMOJI.get(event.layer, "📌")
    color = 0xFF4444 if event.severity == "critical" else 0xFF8800

    payload = {
        "embeds": [{
            "color": color,
            "title": f"{emoji} {event.title[:200]}",
            "description": event.summary or "",
            "fields": [
                {"name": "Layer", "value": event.layer, "inline": True},
                {"name": "Severity", "value": event.severity, "inline": True},
                {"name": "Brand", "value": event.brand_name or "-", "inline": True},
            ],
            "url": f"https://fashion-data-engine.vercel.app/intel?event_id={event.id}",
            "timestamp": event.event_time.isoformat() if event.event_time else None,
        }]
    }

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(settings.intel_discord_webhook_url, json=payload)
            resp.raise_for_status()
    except Exception as exc:
        logger.warning("Discord intel alert 발송 실패: %s", exc)
```

---

### Step 2: `src/fashion_engine/config.py` — `intel_discord_webhook_url` 설정 추가

```python
class Settings(BaseSettings):
    ...
    intel_discord_webhook_url: str | None = None  # intel 전용 Discord webhook
```

> 기존 `discord_webhook_url`(일반 알림)과 분리하여 intel 전용 채널로 발송.

---

### Step 3: `_upsert_event()` 완료 후 자동 호출

`scripts/ingest_intel_events.py`의 `_upsert_event()` 함수 내:

```python
async def _upsert_event(db: AsyncSession, run: IntelIngestRun, ...) -> IntelEvent | None:
    ...
    # upsert 완료 후
    if event and is_new:
        # Discord 알림 (severity 필터는 내부에서 처리)
        await notify_discord_if_warranted(event)

    return event
```

`upsert_derived_product_event()` (`intel_service.py`) 완료 후도 동일하게 호출:

```python
async def upsert_derived_product_event(db, ...) -> IntelEvent | None:
    ...
    event = await _create_or_update_event(db, ...)
    if event and is_new:
        await notify_discord_if_warranted(event)
    return event
```

---

### Step 4: `.env.example` 환경변수 추가

```bash
# Intel Hub Discord 알림 (intel 전용 채널, 기존 DISCORD_WEBHOOK_URL과 분리)
INTEL_DISCORD_WEBHOOK_URL=
```

---

## DoD

- [ ] `notify_discord_if_warranted()` 구현 (severity=critical/high 필터, embed 포맷)
- [ ] `settings.intel_discord_webhook_url` 추가 (`config.py`)
- [ ] `_upsert_event()` 완료 후 자동 호출 (신규 이벤트만)
- [ ] `upsert_derived_product_event()` 완료 후 자동 호출
- [ ] `.env.example`에 `INTEL_DISCORD_WEBHOOK_URL` 추가
- [ ] Railway Variables에 `INTEL_DISCORD_WEBHOOK_URL` 설정 필요 (수동 — Codex 미처리)
- [ ] 예외 처리: Discord 발송 실패 시 `logger.warning`만 (이벤트 생성 롤백 없음)

---

## 검증

```bash
# 1. .env에 INTEL_DISCORD_WEBHOOK_URL 설정 후 테스트 이벤트 생성
uv run python -c "
import asyncio, sys; sys.path.insert(0,'src')
from fashion_engine.db import AsyncSessionLocal
from fashion_engine.services.intel_service import notify_discord_if_warranted
from fashion_engine.models.intel import IntelEvent
from datetime import datetime

async def test():
    evt = IntelEvent(
        id=9999,
        title='테스트 드롭 알림: Supreme SS2026',
        summary='coming-soon 태그 감지 — 테스트',
        layer='drops',
        severity='high',
        event_time=datetime.utcnow(),
    )
    await notify_discord_if_warranted(evt)
    print('Discord 알림 발송 완료')

asyncio.run(test())
"

# 2. mirror 잡 실행 후 critical/high 이벤트가 Discord로 전송되는지 확인
uv run python scripts/ingest_intel_events.py --job mirror

# 3. sale_start 파생 이벤트 수동 생성 후 Discord 수신 확인
uv run python scripts/ingest_intel_events.py --job derived_spike --window-hours 48
```

---

## 참고

- `event.brand_name`: `IntelEvent` 모델에 `brand_name` property 또는 JOIN으로 로드 필요 (없으면 `-` 표기)
- Discord embed color: `0xFF4444`(critical, 빨강), `0xFF8800`(high, 주황)
- `is_new` 플래그: upsert 시 INSERT vs UPDATE 구분 — UPDATE된 기존 이벤트는 알림 미발송
- Railway Variables 수동 등록: `INTEL_DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...`
