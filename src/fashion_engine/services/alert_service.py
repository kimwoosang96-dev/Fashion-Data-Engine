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


async def _send_embed(payload: dict, *, webhook_url: str | None = None) -> bool:
    """Discord webhook POST."""
    target_url = webhook_url or settings.discord_webhook_url
    if not target_url:
        logger.debug("DISCORD_WEBHOOK_URL 미설정 — 알림 스킵")
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(target_url, json=payload)
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


async def send_coverage_report_alert(report: Any) -> bool:
    summary = getattr(report, "summary", {})
    delta = getattr(report, "week_over_week", {})
    fields = [
        {
            "name": "주간 요약",
            "value": (
                f"채널 {summary.get('active_channels', 0)}개 활성 / {summary.get('inactive_channels', 0)}개 비활성\n"
                f"제품 {summary.get('products_total', 0):,}개 ({delta.get('products_total_delta', 0):+d})\n"
                f"세일 {summary.get('sale_products', 0):,}개 ({summary.get('sale_ratio_pct', 0):.1f}%)\n"
                f"사이즈 재고 {summary.get('size_data_products', 0):,}개 / 역대 최저 {summary.get('all_time_low_products', 0):,}개"
            ),
            "inline": False,
        },
        {
            "name": "❌ 수집 불가 채널",
            "value": "\n".join(
                f"· {row.channel_name} ({row.note})" for row in report.dead_channels[:8]
            ) or "없음",
            "inline": False,
        },
        {
            "name": "⚠️ 수집률 급감 채널",
            "value": "\n".join(
                f"· {row.channel_name} ({row.previous_count} → {row.recent_count})"
                for row in report.degraded_channels[:8]
            ) or "없음",
            "inline": False,
        },
        {
            "name": "📝 Draft 채널",
            "value": "\n".join(
                f"· {row.channel_name}" for row in report.draft_channels[:8]
            ) or "없음",
            "inline": False,
        },
    ]
    if getattr(report, "output_path", None):
        fields.append(
            {
                "name": "CSV",
                "value": str(report.output_path),
                "inline": False,
            }
        )

    embed = {
        "title": "📊 채널 커버리지 리포트",
        "description": getattr(report, "generated_at", datetime.utcnow()).strftime("%Y-%m-%d %H:%M UTC"),
        "color": 0x5865F2,
        "fields": fields,
    }
    return await _send_embed(
        {"embeds": [embed]},
        webhook_url=settings.weekly_report_webhook or settings.discord_webhook_url,
    )


async def send_channel_reactivated_alert(*, count: int) -> bool:
    embed = {
        "title": "🔄 채널 자동 재활성화",
        "description": f"비활성 채널 {count}개를 재probe 후 다시 활성화했습니다.",
        "color": 0x57F287,
        "fields": [
            {"name": "재활성화 수", "value": str(count), "inline": True},
        ],
    }
    return await _send_embed({"embeds": [embed]})


async def send_performance_alert(*, endpoints: list[dict]) -> bool:
    if not endpoints:
        return False
    fields = [
        {
            "name": row["path"],
            "value": f"p95 {row['p95_ms']}ms · avg {row['avg_ms']}ms · count {row['count']}",
            "inline": False,
        }
        for row in endpoints[:8]
    ]
    embed = {
        "title": "🐢 Slow API Alert",
        "description": "p95 응답시간 1초 초과 엔드포인트가 감지되었습니다.",
        "color": 0xF39C12,
        "fields": fields,
    }
    return await _send_embed({"embeds": [embed]})


async def send_backup_alert(*, key: str, size_bytes: int) -> bool:
    embed = {
        "title": "🗄️ DB Backup Uploaded",
        "description": "주간 데이터베이스 백업이 업로드되었습니다.",
        "color": 0x5865F2,
        "fields": [
            {"name": "Object Key", "value": key, "inline": False},
            {"name": "Size", "value": f"{size_bytes:,} bytes", "inline": True},
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
