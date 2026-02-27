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
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import crawl_products  # noqa: E402
import crawl_drops  # noqa: E402
import crawl_news  # noqa: E402
import update_exchange_rates  # noqa: E402


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
        await crawl_products.run(limit=0, channel_type=None, no_alerts=False)
        LOGGER.info("[JOB] products completed")
    except Exception:
        LOGGER.exception("[JOB] products failed")


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
        run_news_crawl_job,
        CronTrigger(hour=8, minute=0),
        id="news_daily_0800",
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
