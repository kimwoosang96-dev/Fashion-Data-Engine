from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from fashion_engine.config import settings


engine = create_async_engine(
    settings.database_url,
    echo=settings.api_debug,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """개발 환경: 테이블 자동 생성 (Alembic 마이그레이션이 없을 때)"""
    # 모든 모델이 임포트된 상태에서 호출해야 함
    import fashion_engine.models  # noqa: F401 — 모든 모델 등록
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
