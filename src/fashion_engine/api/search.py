"""
POST /api/search — LLM 병렬 검색 라우터

사용자 API 키를 헤더(X-OpenAI-Key, X-Gemini-Key, X-Claude-Key)로 받아
GPT·Gemini·Claude를 동시에 호출하고 결과를 취합해서 반환한다.
"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from fashion_engine.services.llm_search_service import search_all

router = APIRouter(prefix="/api", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    """자연어 쿼리 또는 제품 URL"""


class SearchResponse(BaseModel):
    query: str
    results: list[dict]
    sources_used: list[str]


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, request: Request):
    """
    GPT·Gemini·Claude 병렬 웹 검색 후 결과 취합·중복 제거.

    헤더에 사용하는 AI 키를 포함:
    - `X-OpenAI-Key`: OpenAI API 키
    - `X-Gemini-Key`: Google Gemini API 키
    - `X-Claude-Key`: Anthropic Claude API 키

    최소 1개 키가 필요합니다.
    """
    openai_key = request.headers.get("X-OpenAI-Key") or None
    gemini_key = request.headers.get("X-Gemini-Key") or None
    claude_key = request.headers.get("X-Claude-Key") or None

    if not any([openai_key, gemini_key, claude_key]):
        raise HTTPException(
            status_code=400,
            detail="최소 1개의 AI API 키가 필요합니다. "
                   "헤더에 X-OpenAI-Key, X-Gemini-Key, X-Claude-Key 중 하나를 포함하세요.",
        )

    if not req.query.strip():
        raise HTTPException(status_code=400, detail="검색어를 입력하세요.")

    sources_used = []
    if openai_key:
        sources_used.append("gpt")
    if gemini_key:
        sources_used.append("gemini")
    if claude_key:
        sources_used.append("claude")

    results = await search_all(
        query=req.query,
        openai_key=openai_key,
        gemini_key=gemini_key,
        claude_key=claude_key,
    )

    return SearchResponse(
        query=req.query,
        results=results,
        sources_used=sources_used,
    )
