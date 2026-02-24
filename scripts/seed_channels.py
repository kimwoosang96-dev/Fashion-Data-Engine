"""
전처리된 채널 데이터를 DB에 저장하는 스크립트

사용법:
    uv run python scripts/seed_channels.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
from rich.console import Console
from rich.progress import track

from fashion_engine.database import init_db, AsyncSessionLocal
from fashion_engine.services.channel_service import upsert_channel

console = Console()
INPUT_FILE = Path("data/channels_cleaned.csv")


async def main():
    console.print("[bold blue]Fashion Data Engine — 채널 DB 저장[/bold blue]\n")

    if not INPUT_FILE.exists():
        console.print(f"[red]파일 없음: {INPUT_FILE}[/red]")
        console.print("먼저 scripts/preprocess_channels.py를 실행하세요.")
        sys.exit(1)

    await init_db()

    df = pd.read_csv(INPUT_FILE)
    df = df.where(pd.notnull(df), None)  # NaN → None

    async with AsyncSessionLocal() as db:
        for _, row in track(df.iterrows(), total=len(df), description="DB 저장 중..."):
            await upsert_channel(db, {
                "name": row["name"],
                "url": row["url"],
                "original_url": row.get("original_url") or None,
                "channel_type": row.get("channel_type") or None,
                "country": row.get("country") or None,
                "is_active": bool(row.get("is_active", True)),
            })

    console.print(f"\n[green]완료:[/green] {len(df)}개 채널 저장")


if __name__ == "__main__":
    asyncio.run(main())
