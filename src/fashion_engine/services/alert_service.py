"""
Discord webhook 알림 서비스.

3가지 알림 유형:
  🔥 sale_alert       — 세일 전환 감지 (is_sale False → True)
  🚀 new_product_alert — 신제품 첫 등장 (product_key DB 신규)
  📉 price_drop_alert  — 가격 10%+ 하락
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from fashion_engine.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AlertPayload:
    product_name: str
    product_key: str
    channel_name: str
    product_url: str
    image_url: str | None
    price_krw: int
    original_price_krw: int | None = None
    discount_rate: int | None = None
    prev_price_krw: int | None = None   # price_drop_alert용


async def _send_embed(payload: dict) -> bool:
    """Discord webhook POST."""
    if not settings.discord_webhook_url:
        logger.debug("DISCORD_WEBHOOK_URL 미설정 — 알림 스킵")
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(settings.discord_webhook_url, json=payload)
            if resp.status_code in (200, 204):
                return True
            logger.warning(f"Discord webhook 응답 오류: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Discord webhook 전송 실패: {e}")
    return False


def _format_krw(amount: int) -> str:
    return f"₩{amount:,}"


async def sale_alert(alert: AlertPayload) -> bool:
    """🔥 세일 전환 알림."""
    discount_str = f" ({alert.discount_rate}% 할인)" if alert.discount_rate else ""
    fields = [
        {"name": "채널", "value": alert.channel_name, "inline": True},
        {"name": "세일가", "value": _format_krw(alert.price_krw), "inline": True},
    ]
    if alert.original_price_krw:
        fields.append({"name": "정가", "value": _format_krw(alert.original_price_krw), "inline": True})

    embed = {
        "title": f"🔥 세일 감지{discount_str}",
        "description": f"**[{alert.product_name}]({alert.product_url})**",
        "color": 0xFF4500,  # 오렌지-레드
        "fields": fields,
        "footer": {"text": f"product_key: {alert.product_key}"},
    }
    if alert.image_url:
        embed["thumbnail"] = {"url": alert.image_url}

    return await _send_embed({"embeds": [embed]})


async def new_product_alert(alert: AlertPayload) -> bool:
    """🚀 신제품 발매 알림."""
    embed = {
        "title": "🚀 신제품 발매!",
        "description": f"**[{alert.product_name}]({alert.product_url})**",
        "color": 0x00BFFF,  # 딥스카이블루
        "fields": [
            {"name": "채널", "value": alert.channel_name, "inline": True},
            {"name": "가격", "value": _format_krw(alert.price_krw), "inline": True},
        ],
        "footer": {"text": f"product_key: {alert.product_key}"},
    }
    if alert.image_url:
        embed["thumbnail"] = {"url": alert.image_url}

    return await _send_embed({"embeds": [embed]})


async def price_drop_alert(alert: AlertPayload) -> bool:
    """📉 가격 하락 알림."""
    drop_amount = (alert.prev_price_krw or alert.price_krw) - alert.price_krw
    drop_pct = (
        round(drop_amount / alert.prev_price_krw * 100, 1)
        if alert.prev_price_krw
        else 0
    )
    embed = {
        "title": f"📉 가격 {drop_pct}% 하락!",
        "description": f"**[{alert.product_name}]({alert.product_url})**",
        "color": 0x2ECC71,  # 그린
        "fields": [
            {"name": "채널", "value": alert.channel_name, "inline": True},
            {"name": "현재가", "value": _format_krw(alert.price_krw), "inline": True},
            {"name": "이전가", "value": _format_krw(alert.prev_price_krw or 0), "inline": True},
            {"name": "절감액", "value": _format_krw(drop_amount), "inline": True},
        ],
        "footer": {"text": f"product_key: {alert.product_key}"},
    }
    if alert.image_url:
        embed["thumbnail"] = {"url": alert.image_url}

    return await _send_embed({"embeds": [embed]})


async def send_audit_alert(findings: list[Any]) -> bool:
    """데이터 감사 결과 알림. ERROR>=1 또는 WARNING>=3일 때만 전송."""
    err_items = [f for f in findings if getattr(f, "severity", "") == "ERROR"]
    warn_items = [f for f in findings if getattr(f, "severity", "") == "WARNING"]
    err_count = len(err_items)
    warn_count = len(warn_items)

    if err_count == 0 and warn_count < 3:
        logger.info("audit alert skip: err=%s warn=%s", err_count, warn_count)
        return False

    color = 0xE74C3C if err_count > 0 else 0xF1C40F
    top_items = (err_items + warn_items)[:8]
    fields = []
    for item in top_items:
        fields.append(
            {
                "name": f"[{getattr(item, 'severity', '-')}] {getattr(item, 'section', '-')}",
                "value": str(getattr(item, "message", "-"))[:900],
                "inline": False,
            }
        )

    embed = {
        "title": "🧪 Data Audit Alert",
        "description": f"ERROR {err_count}개 / WARNING {warn_count}개",
        "color": color,
        "fields": fields or [{"name": "결과", "value": "알림 조건 충족", "inline": False}],
    }
    return await _send_embed({"embeds": [embed]})


async def send_heartbeat_alert(
    *,
    last_crawl_at: datetime | None,
    next_jobs: list[str],
) -> bool:
    """스케줄러 heartbeat 알림."""
    last_crawl_text = (
        last_crawl_at.strftime("%Y-%m-%d %H:%M:%S")
        if last_crawl_at
        else "기록 없음"
    )
    next_jobs_text = "\n".join(next_jobs[:6]) if next_jobs else "예정 작업 없음"
    embed = {
        "title": "💓 Scheduler Heartbeat",
        "description": "스케줄러가 정상 가동 중입니다.",
        "color": 0x3498DB,
        "fields": [
            {"name": "마지막 크롤 시각", "value": last_crawl_text, "inline": False},
            {"name": "다음 예정 작업", "value": next_jobs_text[:1000], "inline": False},
        ],
    }
    return await _send_embed({"embeds": [embed]})


async def send_test_alert() -> bool:
    """Discord 연결 테스트용 알림."""
    payload = AlertPayload(
        product_name="Fashion Data Engine — 테스트 알림",
        product_key="test:test-product",
        channel_name="Test Channel",
        product_url="https://example.com",
        image_url=None,
        price_krw=134000,
        original_price_krw=309000,
        discount_rate=57,
    )
    ok = await sale_alert(payload)
    if ok:
        logger.info("Discord 테스트 알림 전송 성공")
    else:
        logger.warning("Discord 테스트 알림 전송 실패 (webhook URL 미설정 또는 오류)")
    return ok
