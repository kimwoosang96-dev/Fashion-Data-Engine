"""
자동 크롤 스케줄러.

사용법:
  uv run python scripts/scheduler.py
  uv run python scripts/scheduler.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import crawl_products  # noqa: E402
import crawl_drops  # noqa: E402
import crawl_news  # noqa: E402
import auto_switch_parser  # noqa: E402
import coverage_report  # noqa: E402
import data_audit  # noqa: E402
import ingest_intel_events  # noqa: E402
import manage_partitions  # noqa: E402
import reactivate_channels  # noqa: E402
import update_exchange_rates  # noqa: E402
import verify_image_urls  # noqa: E402
from fashion_engine.database import AsyncSessionLocal  # noqa: E402
from fashion_engine.models.crawl_run import CrawlRun  # noqa: E402
from fashion_engine.config import settings  # noqa: E402
from fashion_engine.services.alert_service import send_audit_alert, send_heartbeat_alert  # noqa: E402


def setup_logger() -> logging.Logger:
    log_dir = ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "scheduler.log"

    logger = logging.getLogger("fashion_scheduler")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


LOGGER = setup_logger()


async def run_exchange_rates_job() -> None:
    try:
        LOGGER.info("[JOB] exchange-rates started")
        await update_exchange_rates.run()
        LOGGER.info("[JOB] exchange-rates completed")
    except Exception:
        LOGGER.exception("[JOB] exchange-rates failed")


async def run_drop_crawl_job() -> None:
    try:
        LOGGER.info("[JOB] drops started")
        await crawl_drops.run(limit=0, all_types=False, no_alerts=False)
        LOGGER.info("[JOB] drops completed")
    except Exception:
        LOGGER.exception("[JOB] drops failed")


async def run_news_crawl_job() -> None:
    try:
        LOGGER.info("[JOB] news started")
        await crawl_news.run(per_feed=30)
        LOGGER.info("[JOB] news completed")
    except Exception:
        LOGGER.exception("[JOB] news failed")


async def run_product_crawl_job() -> None:
    try:
        LOGGER.info("[JOB] products started")
        await crawl_products.run(
            limit=0,
            channel_type=None,
            country=None,
            channel_id=None,
            channel_name=None,
            fast_poll=False,
            new_only=False,
            dry_run=False,
            no_alerts=False,
            skip_catalog=False,
            no_intel=False,
            no_watch=False,
            concurrency=2,
        )
        LOGGER.info("[JOB] products completed")
    except Exception:
        LOGGER.exception("[JOB] products failed")


async def run_fast_poll_job() -> None:
    try:
        LOGGER.info("[JOB] fast-poll started")
        await crawl_products.run(
            limit=50,
            channel_type=None,
            country=None,
            channel_id=None,
            channel_name=None,
            fast_poll=True,
            new_only=False,
            dry_run=False,
            no_alerts=False,
            skip_catalog=True,
            no_intel=False,
            no_watch=False,
            concurrency=2,
        )
        LOGGER.info("[JOB] fast-poll completed")
    except Exception:
        LOGGER.exception("[JOB] fast-poll failed")


async def run_new_products_job() -> None:
    try:
        LOGGER.info("[JOB] new-products started")
        await crawl_products.run(
            limit=50,
            channel_type=None,
            country=None,
            channel_id=None,
            channel_name=None,
            fast_poll=False,
            new_only=True,
            dry_run=False,
            no_alerts=False,
            skip_catalog=True,
            no_intel=False,
            no_watch=False,
            concurrency=2,
        )
        LOGGER.info("[JOB] new-products completed")
    except Exception:
        LOGGER.exception("[JOB] new-products failed")


async def run_data_audit_job() -> None:
    try:
        LOGGER.info("[JOB] data-audit started")
        result = await data_audit.run_audit(limit=20, print_report=True)
        LOGGER.info(
            "[JOB] data-audit completed (warning=%s error=%s elapsed=%.2fs)",
            result.warning_count,
            result.error_count,
            result.elapsed_sec,
        )
        if settings.discord_webhook_url:
            sent = await send_audit_alert(result.findings)
            LOGGER.info("[JOB] data-audit discord_alert=%s", sent)
    except Exception:
        LOGGER.exception("[JOB] data-audit failed")


async def run_coverage_report_job() -> None:
    try:
        LOGGER.info("[JOB] coverage-report started")
        path = ROOT / "reports" / f"coverage_report_{datetime.now().strftime('%Y-%m-%d')}.csv"
        report = await coverage_report.run(output_path=str(path), send_discord=True)
        LOGGER.info(
            "[JOB] coverage-report completed dead=%s degraded=%s draft=%s output=%s",
            len(report.dead_channels),
            len(report.degraded_channels),
            len(report.draft_channels),
            report.output_path,
        )
    except Exception:
        LOGGER.exception("[JOB] coverage-report failed")


async def run_auto_switch_parser_job() -> None:
    try:
        LOGGER.info("[JOB] auto-switch-parser started")
        code = await auto_switch_parser.run(apply=True)
        LOGGER.info("[JOB] auto-switch-parser completed code=%s", code)
    except Exception:
        LOGGER.exception("[JOB] auto-switch-parser failed")


async def run_verify_image_urls_job() -> None:
    try:
        LOGGER.info("[JOB] verify-image-urls started")
        code = await verify_image_urls.run(apply=True, limit=500, refetch_broken=True)
        LOGGER.info("[JOB] verify-image-urls completed code=%s", code)
    except Exception:
        LOGGER.exception("[JOB] verify-image-urls failed")


async def run_reactivate_channels_job() -> None:
    try:
        LOGGER.info("[JOB] reactivate-channels started")
        code = await reactivate_channels.run(limit=30, dry_run=False)
        LOGGER.info("[JOB] reactivate-channels completed code=%s", code)
    except Exception:
        LOGGER.exception("[JOB] reactivate-channels failed")


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
        LOGGER.info("[JOB] intel-spike skipped (INTEL_INGEST_ENABLED=false)")
        return
    try:
        LOGGER.info("[JOB] intel-spike started")
        code = await ingest_intel_events.run(job="derived_spike", window_hours=48)
        LOGGER.info("[JOB] intel-spike completed code=%s", code)
    except Exception:
        LOGGER.exception("[JOB] intel-spike failed")


async def _get_last_done_crawl_at() -> datetime | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CrawlRun.finished_at)
            .where(CrawlRun.status == "done", CrawlRun.finished_at.is_not(None))
            .order_by(CrawlRun.finished_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


async def run_partition_maintenance_job(*, startup: bool = False) -> None:
    try:
        target_years = None if startup else [datetime.now(ZoneInfo("Asia/Seoul")).year + 1]
        label = "partition-maintenance-startup" if startup else "partition-maintenance"
        LOGGER.info("[JOB] %s started", label)
        ensured = await manage_partitions.main(target_years or [])
        LOGGER.info("[JOB] %s completed ensured=%s", label, ensured)
    except Exception:
        LOGGER.exception("[JOB] partition-maintenance failed")


async def run_scheduler_heartbeat_job(scheduler: AsyncIOScheduler) -> None:
    try:
        LOGGER.info("[JOB] scheduler-heartbeat started")
        last_crawl_at = await _get_last_done_crawl_at()
        next_jobs = []
        for job in scheduler.get_jobs():
            if job.next_run_time is None:
                continue
            next_jobs.append(
                f"{job.id} — {job.next_run_time.astimezone(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}"
            )
        sent = await send_heartbeat_alert(last_crawl_at=last_crawl_at, next_jobs=next_jobs)
        LOGGER.info("[JOB] scheduler-heartbeat completed sent=%s", sent)
    except Exception:
        LOGGER.exception("[JOB] scheduler-heartbeat failed")


def register_jobs(scheduler: AsyncIOScheduler) -> None:
    scheduler.add_job(
        run_product_crawl_job,
        CronTrigger(hour=3, minute=0),
        id="product_crawl_daily_0300",
        replace_existing=True,
    )
    scheduler.add_job(
        run_exchange_rates_job,
        CronTrigger(hour=7, minute=0),
        id="exchange_rates_daily_0700",
        replace_existing=True,
    )
    scheduler.add_job(
        run_drop_crawl_job,
        CronTrigger(hour=7, minute=10),
        id="drops_daily_0710",
        replace_existing=True,
    )
    scheduler.add_job(
        run_fast_poll_job,
        CronTrigger(hour="*/2", minute=20),
        id="fast_poll_every_2h",
        replace_existing=True,
    )
    scheduler.add_job(
        run_new_products_job,
        CronTrigger(minute=40),
        id="new_products_hourly",
        replace_existing=True,
    )
    scheduler.add_job(
        run_news_crawl_job,
        CronTrigger(hour="0,6,12,18", minute=0),
        id="news_4x_daily",
        replace_existing=True,
    )
    scheduler.add_job(
        run_data_audit_job,
        CronTrigger(day_of_week="sun", hour=9, minute=0),
        id="audit_weekly_sun_0900",
        replace_existing=True,
    )
    scheduler.add_job(
        run_coverage_report_job,
        CronTrigger(day_of_week="sun", hour=9, minute=5),
        id="coverage_weekly_sun_0905",
        replace_existing=True,
    )
    scheduler.add_job(
        run_auto_switch_parser_job,
        CronTrigger(day_of_week="sun", hour=9, minute=30),
        id="auto_switch_parser_weekly_sun_0930",
        replace_existing=True,
    )
    scheduler.add_job(
        run_verify_image_urls_job,
        CronTrigger(day_of_week="sat", hour=5, minute=0),
        id="verify_image_urls_weekly_sat_0500",
        replace_existing=True,
    )
    scheduler.add_job(
        run_reactivate_channels_job,
        CronTrigger(day_of_week="tue", hour=4, minute=0),
        id="reactivate_channels_weekly_tue_0400",
        replace_existing=True,
    )
    scheduler.add_job(
        run_intel_mirror_job,
        CronTrigger(hour="0,6,12,18", minute=10),
        id="intel_mirror_4x_daily",
        replace_existing=True,
    )
    scheduler.add_job(
        run_intel_spike_job,
        CronTrigger(hour="3,9,15,21", minute=0),
        id="intel_spike_4x_daily",
        replace_existing=True,
    )
    scheduler.add_job(
        run_partition_maintenance_job,
        CronTrigger(month=12, day=1, hour=3, minute=30),
        id="partition_maintenance_yearly_1201",
        replace_existing=True,
    )
    scheduler.add_job(
        run_scheduler_heartbeat_job,
        CronTrigger(hour=9, minute=10),
        kwargs={"scheduler": scheduler},
        id="scheduler_heartbeat_daily_0910",
        replace_existing=True,
    )


def print_jobs(scheduler: AsyncIOScheduler) -> None:
    for job in scheduler.get_jobs():
        LOGGER.info("scheduled: id=%s next=%s", job.id, job.next_run_time)


async def main(dry_run: bool) -> None:
    tz_name = "Asia/Seoul"
    scheduler = AsyncIOScheduler(timezone=ZoneInfo(tz_name))
    register_jobs(scheduler)
    scheduler.start()
    LOGGER.info("scheduler started timezone=%s dry_run=%s", tz_name, dry_run)
    print_jobs(scheduler)

    if dry_run:
        scheduler.shutdown(wait=False)
        return

    try:
        await run_partition_maintenance_job(startup=True)
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        LOGGER.info("scheduler interrupted")
    finally:
        scheduler.shutdown(wait=False)
        LOGGER.info("scheduler stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fashion data scheduler")
    parser.add_argument("--dry-run", action="store_true", help="스케줄 등록만 수행")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
