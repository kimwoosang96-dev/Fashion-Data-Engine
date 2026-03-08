import time

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from fashion_engine.config import settings
from fashion_engine.monitoring import record_slow_query


engine = create_async_engine(
    settings.database_url,
    echo=settings.api_debug,
)


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
    conn.info.setdefault("query_start_time", []).append(time.monotonic())


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
    starts = conn.info.get("query_start_time") or []
    if not starts:
        return
    elapsed_ms = (time.monotonic() - starts.pop()) * 1000
    if elapsed_ms >= 500:
        record_slow_query(statement=statement, elapsed_ms=elapsed_ms)


@event.listens_for(engine.sync_engine, "handle_error")
def _handle_error(exception_context):  # type: ignore[no-untyped-def]
    starts = exception_context.connection.info.get("query_start_time") or []
    if starts:
        starts.pop()

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
    """로컬 SQLite 개발용 테이블 자동 생성. 운영/Railway에서는 Alembic을 사용한다."""
    # 모든 모델이 임포트된 상태에서 호출해야 함
    import fashion_engine.models  # noqa: F401 — 모든 모델 등록
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
