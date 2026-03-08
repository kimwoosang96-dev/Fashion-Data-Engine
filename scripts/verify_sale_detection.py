from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import case, func, select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.channel import Channel  # noqa: E402
from fashion_engine.models.product import Product  # noqa: E402


async def run() -> int:
    await init_db()
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(
                    Channel.platform,
                    func.sum(case((Product.is_sale == True, 1), else_=0)).label("sale_count"),  # noqa: E712
                    func.count(Product.id).label("total_count"),
                )
                .join(Product, Product.channel_id == Channel.id)
                .group_by(Channel.platform)
                .order_by(func.sum(case((Product.is_sale == True, 1), else_=0)).desc())  # noqa: E712
            )
        ).all()
    for platform, sale_count, total_count in rows:
        print(
            f"platform={platform or 'unknown'} sale_count={int(sale_count or 0)} total_count={int(total_count or 0)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
