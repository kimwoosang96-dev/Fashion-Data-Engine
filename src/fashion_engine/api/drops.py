from fastapi import APIRouter, Depends, Query

from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.database import get_db
from fashion_engine.services import drop_service
from fashion_engine.api.schemas import DropIn, DropOut

router = APIRouter(prefix="/drops", tags=["drops"])


@router.get("/upcoming", response_model=list[DropOut])
async def get_upcoming_drops(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """예정 발매(upcoming) 목록."""
    return await drop_service.get_upcoming_drops(db, limit=limit)


@router.get("/", response_model=list[DropOut])
async def list_drops(
    status: str | None = Query(None, description="upcoming | released | sold_out"),
    brand: str | None = Query(None, description="브랜드 slug"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """전체 드롭 목록 (status·brand 필터 지원)."""
    return await drop_service.list_drops(
        db, status=status, brand_slug=brand, limit=limit, offset=offset
    )


@router.post("/", response_model=DropOut, status_code=201)
async def create_drop(
    body: DropIn,
    db: AsyncSession = Depends(get_db),
):
    """수동 드롭 추가 (관리용)."""
    return await drop_service.create_drop_manual(db, body.model_dump())
