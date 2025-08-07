from __future__ import annotations

from collections.abc import AsyncGenerator
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

if not settings.database:
    raise RuntimeError("Database configuration not initialized")


def _to_async_dsn(url: str) -> str:
    if "+asyncpg" in url:
        return url
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


ASYNC_DATABASE_URL = _to_async_dsn(settings.database.url)

engine: AsyncEngine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.database.echo,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_pre_ping=settings.database.pool_pre_ping,
    pool_timeout=settings.database.pool_timeout,
    pool_recycle=3600,
)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            logger.debug("Async database session created")
            yield session
        except Exception as e:
            try:
                await session.rollback()
            except Exception:
                pass
            logger.error("Error in async DB session: %s", e)
            raise
        finally:
            logger.debug("Async database session closed")


async def check_db_connection() -> bool:
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection is healthy")
        return True
    except Exception as e:
        logger.error("Database connection check failed: %s", e)
        return False


async def close_db_connections() -> None:
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error("Error closing database connections: %s", e)


async def get_db_info() -> dict:
    try:
        return {"status": "healthy"}
    except Exception as e:
        logger.error("Error getting database info: %s", e)
        return {"status": "error", "message": str(e)}
