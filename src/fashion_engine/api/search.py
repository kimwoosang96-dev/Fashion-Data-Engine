"""
검색 라우터

POST /api/search   — 브라우저 자동화로 AI 서비스에 병렬 쿼리
GET  /api/login-status — 각 AI 서비스 로그인 상태 확인
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from fashion_engine.services.browser_shopper import query_all, check_login

router = APIRouter(prefix="/api", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    enabled_ais: list[str] = ["claude", "gpt", "gemini"]
    profile_dir: str | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[dict]
    sources_used: list[str]


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    """
    브라우저 자동화로 Claude·GPT·Gemini에 병렬 쿼리.

    - `enabled_ais`: 사용할 AI 목록 (기본: 셋 다)
    - `profile_dir`: Chrome 프로필 경로 (기본: 자동 감지)
    - API 키 불필요, 기존 구독 사용
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="검색어를 입력하세요.")
    if not req.enabled_ais:
        raise HTTPException(status_code=400, detail="최소 1개의 AI를 활성화하세요.")

    results = await query_all(
        query=req.query,
        enabled=req.enabled_ais,
        profile_dir=req.profile_dir,
    )

    return SearchResponse(
        query=req.query,
        results=results,
        sources_used=req.enabled_ais,
    )


@router.get("/login-status")
async def login_status(profile_dir: str | None = None):
    """각 AI 서비스의 로그인 상태를 확인한다."""
    services = ["claude", "gpt", "gemini"]
    import asyncio
    statuses = await asyncio.gather(
        *[check_login(s, profile_dir) for s in services],
        return_exceptions=True,
    )
    return {
        s: (st if not isinstance(st, Exception) else {"service": s, "logged_in": False, "error": str(st)})
        for s, st in zip(services, statuses)
    }
