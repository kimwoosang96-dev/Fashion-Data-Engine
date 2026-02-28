from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fashion_engine.config import settings
from fashion_engine.database import init_db
from fashion_engine.api.channels import router as channels_router
from fashion_engine.api.brands import router as brands_router
from fashion_engine.api.collabs import router as collabs_router
from fashion_engine.api.products import router as products_router
from fashion_engine.api.purchases import router as purchases_router
from fashion_engine.api.drops import router as drops_router
from fashion_engine.api.watchlist import router as watchlist_router
from fashion_engine.api.admin import router as admin_router
from fashion_engine.api.news import router as news_router
from fashion_engine.api.directors import router as directors_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 DB 테이블 자동 생성
    await init_db()
    yield


app = FastAPI(
    title="Fashion Data Engine",
    description="패션 판매채널·브랜드 데이터 플랫폼 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(channels_router)
app.include_router(brands_router)
app.include_router(collabs_router)
app.include_router(products_router)
app.include_router(purchases_router)
app.include_router(drops_router)
app.include_router(watchlist_router)
app.include_router(admin_router)
app.include_router(news_router)
app.include_router(directors_router)


@app.get("/")
async def root():
    return {
        "service": "Fashion Data Engine",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
