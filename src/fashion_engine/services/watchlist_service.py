"""WatchList CRUD — 관심 브랜드/채널/제품 관리."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.models.watchlist import WatchListItem

VALID_TYPES = {"brand", "channel", "product_key"}


async def add_item(db: AsyncSession, watch_type: str, watch_value: str, notes: str | None = None) -> tuple[WatchListItem, bool]:
    """추가. 이미 있으면 (item, False) 반환."""
    existing = (
        await db.execute(
            select(WatchListItem)
            .where(WatchListItem.watch_type == watch_type)
            .where(WatchListItem.watch_value == watch_value)
        )
    ).scalar_one_or_none()
    if existing:
        return existing, False
    item = WatchListItem(watch_type=watch_type, watch_value=watch_value, notes=notes)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item, True


async def list_items(db: AsyncSession, watch_type: str | None = None) -> list[WatchListItem]:
    stmt = select(WatchListItem)
    if watch_type:
        stmt = stmt.where(WatchListItem.watch_type == watch_type)
    return list((await db.execute(stmt.order_by(WatchListItem.watch_type, WatchListItem.watch_value))).scalars().all())


async def delete_item(db: AsyncSession, item_id: int) -> bool:
    result = await db.execute(select(WatchListItem).where(WatchListItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        return False
    await db.delete(item)
    await db.commit()
    return True


async def should_alert(
    db: AsyncSession,
    brand_slug: str | None,
    channel_url: str | None,
    product_key: str | None,
) -> bool:
    """
    WatchList에 등록된 항목과 매칭되면 True.
    WatchList가 비어있으면 False (미설정 = 알림 없음).
    """
    # 총 항목 수 확인 — 비어있으면 알림 없음
    count_result = await db.execute(select(WatchListItem))
    all_items = list(count_result.scalars().all())
    if not all_items:
        return False

    for item in all_items:
        if item.watch_type == "brand" and brand_slug and item.watch_value == brand_slug:
            return True
        if item.watch_type == "channel" and channel_url and item.watch_value == channel_url:
            return True
        if item.watch_type == "product_key" and product_key and item.watch_value == product_key:
            return True
    return False
