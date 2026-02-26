from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.database import get_db
from fashion_engine.services import purchase_service
from fashion_engine.api.schemas import PurchaseIn, PurchaseOut, ScoreOut, PurchaseStatsOut

router = APIRouter(prefix="/purchases", tags=["purchases"])


@router.post("/", response_model=PurchaseOut, status_code=201)
async def create_purchase(
    body: PurchaseIn,
    db: AsyncSession = Depends(get_db),
):
    """구매 기록 추가."""
    return await purchase_service.create_purchase(db, body.model_dump())


@router.get("/stats", response_model=PurchaseStatsOut)
async def get_purchase_stats(db: AsyncSession = Depends(get_db)):
    """전체 구매 통계 — 총 절감액, 베스트 딜 등."""
    return await purchase_service.get_stats(db)


@router.get("/", response_model=list[PurchaseOut])
async def list_purchases(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """내 구매 목록 (최신순)."""
    return await purchase_service.list_purchases(db, limit=limit, offset=offset)


@router.get("/{purchase_id}/score", response_model=ScoreOut)
async def get_purchase_score(
    purchase_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    개별 구매 성공도 — PriceHistory 기반 실시간 계산.
    grade: S(역대 최저가권) / A / B / C / D(비쌈)
    """
    purchase = await purchase_service.get_purchase(db, purchase_id)
    if not purchase:
        raise HTTPException(status_code=404, detail="구매 기록을 찾을 수 없습니다.")
    score = await purchase_service.calc_score(db, purchase)
    return ScoreOut(
        purchase_id=purchase.id,
        product_key=purchase.product_key,
        product_name=purchase.product_name,
        paid_price_krw=purchase.paid_price_krw,
        **score,
    )


@router.delete("/{purchase_id}", status_code=204)
async def delete_purchase(
    purchase_id: int,
    db: AsyncSession = Depends(get_db),
):
    """구매 기록 삭제."""
    deleted = await purchase_service.delete_purchase(db, purchase_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="구매 기록을 찾을 수 없습니다.")
