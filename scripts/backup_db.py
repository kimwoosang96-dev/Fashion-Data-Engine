from __future__ import annotations

import argparse
import asyncio
import gzip
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import boto3

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.config import settings
from fashion_engine.services.alert_service import send_backup_alert


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PostgreSQL pg_dump backup to S3/R2")
    parser.add_argument("--keep-days", type=int, default=30)
    return parser.parse_args()


def _pg_dump_dsn() -> str:
    raw = (
        os.environ.get("RAILWAY_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or settings.database_url
    )
    parsed = urlparse(raw)
    scheme = parsed.scheme.replace("+asyncpg", "")
    return urlunparse((scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


def _build_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )


async def run(*, keep_days: int) -> int:
    if "postgresql" not in settings.database_url:
        print("backup_db skipped: PostgreSQL only")
        return 0
    if not all([settings.s3_access_key, settings.s3_secret_key, settings.s3_bucket]):
        print("backup_db skipped: S3 settings incomplete")
        return 0

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dump_path = Path("/tmp") / f"fashion_db_{ts}.sql.gz"
    dump_dsn = _pg_dump_dsn()

    try:
        proc = subprocess.run(
            ["pg_dump", "--dbname", dump_dsn, "--no-owner", "--no-privileges"],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        print("backup_db skipped: pg_dump not installed")
        return 1
    with gzip.open(dump_path, "wb") as fh:
        fh.write(proc.stdout)

    s3 = _build_s3_client()
    object_key = f"backups/{ts}.sql.gz"
    s3.upload_file(str(dump_path), settings.s3_bucket, object_key)
    size_bytes = dump_path.stat().st_size
    await send_backup_alert(key=object_key, size_bytes=size_bytes)

    cutoff = datetime.utcnow() - timedelta(days=keep_days)
    response = s3.list_objects_v2(Bucket=settings.s3_bucket, Prefix="backups/")
    for item in response.get("Contents", []):
        last_modified = item.get("LastModified")
        if last_modified and last_modified.replace(tzinfo=None) < cutoff:
            s3.delete_object(Bucket=settings.s3_bucket, Key=item["Key"])

    print(f"Backup uploaded: s3://{settings.s3_bucket}/{object_key}")
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(asyncio.run(run(keep_days=args.keep_days)))
