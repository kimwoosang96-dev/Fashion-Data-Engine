from contextlib import asynccontextmanager

from fastapi import FastAPI

from fashion_engine.database import init_db
from fashion_engine.api.channels import router as channels_router
from fashion_engine.api.brands import router as brands_router


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

app.include_router(channels_router)
app.include_router(brands_router)


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
