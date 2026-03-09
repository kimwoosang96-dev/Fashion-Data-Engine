from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from fashion_engine.config import settings
from fashion_engine.database import AsyncSessionLocal
from fashion_engine.monitoring import record_response_time
from fashion_engine.api.watchlist import router as watchlist_router
from fashion_engine.api.search import router as search_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Fashion Search API",
    description="""
## 패션 브랜드 LLM 병렬 검색 API

GPT·Gemini·Claude 동시 웹 검색으로 최저가·판매링크를 실시간으로 제공합니다.

### 주요 엔드포인트
- `POST /api/search` — GPT·Gemini·Claude 병렬 검색 + 중복 제거
- `GET /api/watchlist` — 저장한 제품 목록
- `POST /api/watchlist` — 제품 저장
""",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_methods=["*"],
    allow_headers=["*", "X-OpenAI-Key", "X-Gemini-Key", "X-Claude-Key"],
)


@app.middleware("http")
async def record_response_metrics(request: Request, call_next):
    started = time.monotonic()
    response = await call_next(request)
    record_response_time(request.url.path, time.monotonic() - started)
    return response


app.include_router(search_router)
app.include_router(watchlist_router)


@app.get("/")
async def root():
    return {
        "service": "Fashion Search API",
        "version": "3.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok", "database": "ok"}


@app.get("/robots.txt", include_in_schema=False)
async def api_robots():
    return Response(
        content="User-agent: *\nAllow: /docs\nAllow: /openapi.json\n",
        media_type="text/plain",
    )
