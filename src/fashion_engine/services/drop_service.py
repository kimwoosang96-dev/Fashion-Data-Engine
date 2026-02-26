"""드롭(발매) 정보 서비스 — upsert, 상태 관리."""
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.models.drop import Drop
from fashion_engine.models.brand import Brand


async def upsert_drop(
    db: AsyncSession,
    product_name: str,
    source_url: str,
    product_key: str | None = None,
    brand_id: int | None = None,
    image_url: str | None = None,
    price_krw: int | None = None,
    status: str = "released",
) -> tuple[Drop, bool]:
    """
    source_url + product_key 기준으로 upsert.
    반환: (drop, is_new)
    """
    stmt = select(Drop).where(Drop.source_url == source_url)
    if product_key:
        stmt = select(Drop).where(
            (Drop.source_url == source_url) | (Drop.product_key == product_key)
        )
    result = await db.execute(stmt)
    drop = result.scalar_one_or_none()

    if drop:
        # 상태 업데이트만
        drop.status = status
        if image_url and not drop.image_url:
            drop.image_url = image_url
        if price_krw and not drop.price_krw:
            drop.price_krw = price_krw
        await db.commit()
        await db.refresh(drop)
        return drop, False
    else:
        drop = Drop(
            brand_id=brand_id,
            product_name=product_name,
            product_key=product_key,
            source_url=source_url,
            image_url=image_url,
            price_krw=price_krw,
            status=status,
            detected_at=datetime.utcnow(),
        )
        db.add(drop)
        await db.commit()
        await db.refresh(drop)
        return drop, True


async def mark_notified(db: AsyncSession, drop_id: int) -> None:
    result = await db.execute(select(Drop).where(Drop.id == drop_id))
    drop = result.scalar_one_or_none()
    if drop:
        drop.notified_at = datetime.utcnow()
        await db.commit()


async def get_upcoming_drops(db: AsyncSession, limit: int = 50) -> list[Drop]:
    result = await db.execute(
        select(Drop)
        .where(Drop.status == "upcoming")
        .order_by(Drop.detected_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_drops(
    db: AsyncSession,
    status: str | None = None,
    brand_slug: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Drop]:
    stmt = select(Drop)
    if status:
        stmt = stmt.where(Drop.status == status)
    if brand_slug:
        stmt = stmt.join(Brand, Brand.id == Drop.brand_id).where(Brand.slug == brand_slug)
    stmt = stmt.order_by(Drop.detected_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_drop_manual(db: AsyncSession, data: dict) -> Drop:
    """관리자 수동 드롭 추가."""
    drop = Drop(
        product_name=data["product_name"],
        source_url=data["source_url"],
        product_key=data.get("product_key"),
        brand_id=data.get("brand_id"),
        image_url=data.get("image_url"),
        price_krw=data.get("price_krw"),
        release_date=data.get("release_date"),
        status=data.get("status", "upcoming"),
        detected_at=datetime.utcnow(),
    )
    db.add(drop)
    await db.commit()
    await db.refresh(drop)
    return drop
