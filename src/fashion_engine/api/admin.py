from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.config import settings
from fashion_engine.database import get_db
from fashion_engine.models.channel import Channel
from fashion_engine.models.channel_brand import ChannelBrand
from fashion_engine.models.brand import Brand
from fashion_engine.models.brand_collaboration import BrandCollaboration
from fashion_engine.models.brand_director import BrandDirector
from fashion_engine.models.exchange_rate import ExchangeRate
from fashion_engine.models.price_history import PriceHistory
from fashion_engine.models.product import Product

router = APIRouter(prefix="/admin", tags=["admin"])

ROOT_DIR = Path(__file__).resolve().parents[3]
SCRIPT_MAP = {
    "brands": ["scripts/crawl_brands.py"],
    "products": ["scripts/crawl_products.py"],
    "drops": ["scripts/crawl_drops.py"],
    "channel": ["scripts/crawl_products.py"],
}


def _auth_bearer(authorization: str | None) -> None:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != settings.admin_bearer_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


async def require_admin(authorization: str | None = Header(None)) -> None:
    _auth_bearer(authorization)


@router.get("/stats")
async def get_admin_stats(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    counts = (
        await db.execute(
            select(
                func.count(Channel.id).label("channels"),
                select(func.count(ChannelBrand.channel_id)).scalar_subquery().label("channel_brands"),
                select(func.count(Product.id)).scalar_subquery().label("products"),
                select(func.count(PriceHistory.id)).scalar_subquery().label("price_history"),
            )
        )
    ).one()
    latest_crawls = (
        await db.execute(
            select(
                func.max(ChannelBrand.crawled_at).label("brands_latest"),
                func.max(PriceHistory.crawled_at).label("products_latest"),
            )
        )
    ).one()
    rates = (
        await db.execute(
            select(ExchangeRate.from_currency, ExchangeRate.rate, ExchangeRate.fetched_at)
            .where(ExchangeRate.to_currency == "KRW")
            .order_by(ExchangeRate.fetched_at.desc())
            .limit(20)
        )
    ).all()
    return {
        "counts": {
            "channels": int(counts.channels or 0),
            "channel_brands": int(counts.channel_brands or 0),
            "products": int(counts.products or 0),
            "price_history": int(counts.price_history or 0),
        },
        "latest_crawls": {
            "brands": latest_crawls.brands_latest.isoformat() if latest_crawls.brands_latest else None,
            "products": latest_crawls.products_latest.isoformat() if latest_crawls.products_latest else None,
        },
        "exchange_rates": [
            {
                "from_currency": row.from_currency,
                "rate": row.rate,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
            }
            for row in rates
        ],
    }


@router.get("/channels-health")
async def get_channels_health(
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(
                Channel.id,
                Channel.name,
                Channel.url,
                Channel.channel_type,
                Channel.country,
                func.count(func.distinct(ChannelBrand.brand_id)).label("brand_count"),
                func.count(func.distinct(Product.id)).label("product_count"),
                func.count(func.distinct(case((Product.is_sale == True, Product.id), else_=None))).label("sale_count"),
            )
            .outerjoin(ChannelBrand, ChannelBrand.channel_id == Channel.id)
            .outerjoin(Product, Product.channel_id == Channel.id)
            .group_by(Channel.id)
            .order_by(Channel.name.asc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    payload = []
    for row in rows:
        brand_count = int(row.brand_count or 0)
        product_count = int(row.product_count or 0)
        health = "ok" if (brand_count > 0 or product_count > 0) else "needs_review"
        payload.append(
            {
                "channel_id": row.id,
                "name": row.name,
                "url": row.url,
                "channel_type": row.channel_type,
                "country": row.country,
                "brand_count": brand_count,
                "product_count": product_count,
                "sale_count": int(row.sale_count or 0),
                "health": health,
            }
        )
    return payload


@router.post("/crawl-trigger")
async def trigger_crawl(
    job: str = Query(..., description="brands/products/drops/channel"),
    channel_id: int | None = Query(None, ge=1, description="job=channel일 때 대상 채널 ID"),
    dry_run: bool = Query(False),
    _: None = Depends(require_admin),
):
    if job not in SCRIPT_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown job: {job}")
    cmd = [sys.executable, *SCRIPT_MAP[job]]
    if job == "channel":
        if not channel_id:
            raise HTTPException(status_code=400, detail="job=channel에는 channel_id가 필요합니다.")
        cmd += ["--channel-id", str(channel_id)]
    if dry_run:
        return {
            "ok": True,
            "job": job,
            "channel_id": channel_id,
            "dry_run": True,
            "command": " ".join(cmd),
        }

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(ROOT_DIR),
    )
    return {
        "ok": True,
        "job": job,
        "channel_id": channel_id,
        "dry_run": False,
        "pid": proc.pid,
        "command": " ".join(cmd),
    }


@router.get("/crawl-status")
async def get_crawl_status(
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(
                Channel.id,
                Channel.name,
                Channel.url,
                Channel.channel_type,
                func.count(Product.id).label("product_count"),
                func.count(case((Product.is_active == True, 1), else_=None)).label("active_count"),
                func.count(case((Product.is_active == False, 1), else_=None)).label("inactive_count"),
                func.max(Product.created_at).label("last_crawled_at"),
            )
            .outerjoin(Product, Product.channel_id == Channel.id)
            .group_by(Channel.id)
            .order_by(Channel.name.asc())
            .limit(limit)
            .offset(offset)
        )
    ).all()

    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    payload = []
    for row in rows:
        last = row.last_crawled_at
        if last is None:
            status = "never"
        else:
            dt = last
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            status = "stale" if dt < stale_cutoff else "ok"

        payload.append(
            {
                "channel_id": row.id,
                "channel_name": row.name,
                "channel_url": row.url,
                "channel_type": row.channel_type,
                "product_count": int(row.product_count or 0),
                "active_count": int(row.active_count or 0),
                "inactive_count": int(row.inactive_count or 0),
                "last_crawled_at": last.isoformat() if last else None,
                "status": status,
            }
        )

    return payload


@router.get("/collabs")
async def admin_list_collabs(
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(
                BrandCollaboration.id,
                BrandCollaboration.brand_a_id,
                BrandCollaboration.brand_b_id,
                BrandCollaboration.collab_name,
                BrandCollaboration.collab_category,
                BrandCollaboration.release_year,
                BrandCollaboration.hype_score,
                BrandCollaboration.source_url,
                BrandCollaboration.notes,
                BrandCollaboration.created_at,
                Brand.name.label("brand_a_name"),
                Brand.slug.label("brand_a_slug"),
            )
            .join(Brand, Brand.id == BrandCollaboration.brand_a_id)
            .order_by(BrandCollaboration.hype_score.desc(), BrandCollaboration.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return [
        {
            "id": row.id,
            "brand_a_id": row.brand_a_id,
            "brand_b_id": row.brand_b_id,
            "collab_name": row.collab_name,
            "collab_category": row.collab_category,
            "release_year": row.release_year,
            "hype_score": row.hype_score,
            "source_url": row.source_url,
            "notes": row.notes,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "brand_a_name": row.brand_a_name,
            "brand_a_slug": row.brand_a_slug,
        }
        for row in rows
    ]


@router.post("/collabs")
async def admin_create_collab(
    payload: dict,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    brand_a_id = payload.get("brand_a_id")
    brand_b_id = payload.get("brand_b_id")
    if not brand_a_id and payload.get("brand_a_slug"):
        row = (
            await db.execute(select(Brand.id).where(Brand.slug == payload["brand_a_slug"]))
        ).first()
        brand_a_id = row[0] if row else None
    if not brand_b_id and payload.get("brand_b_slug"):
        row = (
            await db.execute(select(Brand.id).where(Brand.slug == payload["brand_b_slug"]))
        ).first()
        brand_b_id = row[0] if row else None

    if not brand_a_id or not brand_b_id:
        raise HTTPException(status_code=400, detail="brand_a_id/brand_b_id 또는 유효한 brand_slug가 필요합니다.")
    if int(brand_a_id) == int(brand_b_id):
        raise HTTPException(status_code=400, detail="같은 브랜드끼리는 협업으로 등록할 수 없습니다.")
    collab_name = str(payload.get("collab_name") or "").strip()
    if not collab_name:
        raise HTTPException(status_code=400, detail="collab_name은 필수입니다.")

    hype_score = payload.get("hype_score")
    if hype_score in (None, ""):
        overlap_channels = (
            await db.execute(
                select(func.count())
                .select_from(
                    select(ChannelBrand.channel_id)
                    .where(ChannelBrand.brand_id.in_([int(brand_a_id), int(brand_b_id)]))
                    .group_by(ChannelBrand.channel_id)
                    .having(func.count(func.distinct(ChannelBrand.brand_id)) == 2)
                    .subquery()
                )
            )
        ).scalar_one()
        hype_score = min(100, int(overlap_channels or 0) * 10)

    row = BrandCollaboration(
        brand_a_id=int(brand_a_id),
        brand_b_id=int(brand_b_id),
        collab_name=collab_name[:255],
        collab_category=(str(payload["collab_category"]).strip()[:50] if payload.get("collab_category") else None),
        release_year=(int(payload["release_year"]) if payload.get("release_year") not in (None, "") else None),
        hype_score=max(0, min(100, int(hype_score))),
        source_url=(str(payload["source_url"]).strip()[:500] if payload.get("source_url") else None),
        notes=(str(payload["notes"]).strip() if payload.get("notes") else None),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"ok": True, "id": row.id}


@router.delete("/collabs/{collab_id}")
async def admin_delete_collab(
    collab_id: int,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(select(BrandCollaboration).where(BrandCollaboration.id == collab_id))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="collab not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}


@router.get("/brand-channel-audit")
async def admin_brand_channel_audit(
    limit: int = Query(200, ge=1, le=1000),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(
                Channel.id,
                Channel.name,
                Channel.url,
                Channel.channel_type,
                func.count(func.distinct(ChannelBrand.brand_id)).label("brand_count"),
            )
            .outerjoin(ChannelBrand, ChannelBrand.channel_id == Channel.id)
            .group_by(Channel.id)
            .order_by(Channel.name.asc())
        )
    ).all()

    brand_names_by_channel: dict[int, list[str]] = {}
    linked = (
        await db.execute(
            select(ChannelBrand.channel_id, Brand.name)
            .join(Brand, Brand.id == ChannelBrand.brand_id)
            .order_by(ChannelBrand.channel_id.asc(), Brand.name.asc())
        )
    ).all()
    for channel_id, brand_name in linked:
        brand_names_by_channel.setdefault(channel_id, []).append(brand_name)

    suspicious: list[dict] = []
    seen: set[tuple[str, int]] = set()
    official_types = {"official", "brand-store"}
    multi_types = {"multi-brand", "edit-shop"}

    for row in rows:
        brand_count = int(row.brand_count or 0)
        channel_type = (row.channel_type or "").strip().lower()
        linked_brands = brand_names_by_channel.get(row.id, [])

        if channel_type in official_types and brand_count != 1:
            key = ("official_count_mismatch", row.id)
            if key not in seen:
                seen.add(key)
                suspicious.append(
                    {
                        "audit_type": "official_count_mismatch",
                        "channel_id": row.id,
                        "channel_name": row.name,
                        "channel_type": row.channel_type,
                        "channel_url": row.url,
                        "brand_count": brand_count,
                        "linked_brands": linked_brands[:8],
                        "reason": "공식몰/브랜드스토어인데 연결 브랜드 수가 1이 아님",
                        "suggestion": "해당 채널의 브랜드 매핑을 재검토하세요.",
                    }
                )

        if channel_type in multi_types and brand_count == 1:
            key = ("multi_brand_too_low", row.id)
            if key not in seen:
                seen.add(key)
                suspicious.append(
                    {
                        "audit_type": "multi_brand_too_low",
                        "channel_id": row.id,
                        "channel_name": row.name,
                        "channel_type": row.channel_type,
                        "channel_url": row.url,
                        "brand_count": brand_count,
                        "linked_brands": linked_brands[:8],
                        "reason": "멀티브랜드 채널인데 연결 브랜드가 1개뿐임",
                        "suggestion": "크롤러 셀렉터/전략을 재점검하거나 채널 유형을 확인하세요.",
                    }
                )

    name_collision_rows = (
        await db.execute(
            select(Channel.id, Channel.name, Channel.url, Channel.channel_type, Brand.id, Brand.slug)
            .join(Brand, func.lower(Channel.name) == func.lower(Brand.name))
            .where(Channel.channel_type.isnot(None))
            .where(func.lower(Channel.channel_type).notin_(tuple(official_types)))
            .limit(limit)
        )
    ).all()
    for row in name_collision_rows:
        key = ("name_collision", row[0])
        if key in seen:
            continue
        seen.add(key)
        suspicious.append(
            {
                "audit_type": "name_collision",
                "channel_id": row[0],
                "channel_name": row[1],
                "channel_type": row[3],
                "channel_url": row[2],
                "brand_count": len(brand_names_by_channel.get(row[0], [])),
                "linked_brands": brand_names_by_channel.get(row[0], [])[:8],
                "reason": f"채널명과 브랜드명이 동일(brand_slug={row[5]})",
                "suggestion": "브랜드/채널 엔티티 분리와 channel_type 적절성을 검토하세요.",
            }
        )

    suspicious.sort(key=lambda x: (x["audit_type"], x["channel_name"]))
    return {"total": len(suspicious), "items": suspicious[:limit]}


@router.get("/directors")
async def admin_list_directors(
    brand_id: int | None = Query(None, ge=1),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(BrandDirector, Brand.name, Brand.slug)
        .join(Brand, Brand.id == BrandDirector.brand_id)
        .order_by(BrandDirector.start_year.desc().nullslast(), BrandDirector.id.desc())
    )
    if brand_id:
        query = query.where(BrandDirector.brand_id == brand_id)
    rows = (await db.execute(query)).all()
    return [
        {
            "id": row[0].id,
            "brand_id": row[0].brand_id,
            "brand_name": row[1],
            "brand_slug": row[2],
            "name": row[0].name,
            "role": row[0].role,
            "start_year": row[0].start_year,
            "end_year": row[0].end_year,
            "note": row[0].note,
            "created_at": row[0].created_at.isoformat(),
        }
        for row in rows
    ]


@router.post("/directors")
async def admin_create_director(
    payload: dict,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    brand_id = payload.get("brand_id")
    if brand_id is None and payload.get("brand_slug"):
        brand = (
            await db.execute(select(Brand).where(Brand.slug == payload["brand_slug"]))
        ).scalar_one_or_none()
        brand_id = brand.id if brand else None
    if not brand_id:
        raise HTTPException(status_code=400, detail="brand_id 또는 유효한 brand_slug가 필요합니다.")
    if not payload.get("name"):
        raise HTTPException(status_code=400, detail="name은 필수입니다.")

    row = BrandDirector(
        brand_id=int(brand_id),
        name=str(payload["name"]).strip()[:255],
        role=str(payload.get("role") or "Creative Director").strip()[:100],
        start_year=int(payload["start_year"]) if payload.get("start_year") not in (None, "") else None,
        end_year=int(payload["end_year"]) if payload.get("end_year") not in (None, "") else None,
        note=(str(payload["note"]).strip() if payload.get("note") else None),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"ok": True, "id": row.id}


@router.delete("/directors/{director_id}")
async def admin_delete_director(
    director_id: int,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(select(BrandDirector).where(BrandDirector.id == director_id))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="director not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}


@router.patch("/brands/{brand_id}/instagram")
async def admin_patch_brand_instagram(
    brand_id: int,
    payload: dict,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    brand = (
        await db.execute(select(Brand).where(Brand.id == brand_id))
    ).scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="brand not found")
    brand.instagram_url = (payload.get("instagram_url") or None)
    await db.commit()
    return {"ok": True, "id": brand.id, "instagram_url": brand.instagram_url}


@router.patch("/channels/{channel_id}/instagram")
async def admin_patch_channel_instagram(
    channel_id: int,
    payload: dict,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    channel = (
        await db.execute(select(Channel).where(Channel.id == channel_id))
    ).scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="channel not found")
    channel.instagram_url = (payload.get("instagram_url") or None)
    await db.commit()
    return {"ok": True, "id": channel.id, "instagram_url": channel.instagram_url}
