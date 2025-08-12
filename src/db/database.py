from __future__ import annotations

from builtins import getattr as getattr  # re-export for test monkeypatching
from collections.abc import AsyncGenerator
import inspect
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

if not settings.database:
    raise RuntimeError("Database configuration not initialized")

# Capture non-None database config for type checkers
DB_CFG = settings.database
assert DB_CFG is not None


def _to_async_dsn(url: str) -> str:
    if "+asyncpg" in url:
        return url
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


ASYNC_DATABASE_URL = _to_async_dsn(DB_CFG.url)

# Lazy engine/sessionmaker to avoid creating pools at import time.
# Public alias for tests: unit tests monkeypatch `db.database.engine`.
engine: AsyncEngine | None = None
_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global engine, _engine
    # If a test has monkeypatched the public `engine`, use it.
    if engine is not None:
        return engine
    if _engine is None:
        _engine = create_async_engine(
            ASYNC_DATABASE_URL,
            echo=DB_CFG.echo,
            pool_size=DB_CFG.pool_size,
            max_overflow=DB_CFG.max_overflow,
            pool_pre_ping=DB_CFG.pool_pre_ping,
            pool_timeout=DB_CFG.pool_timeout,
            pool_recycle=3600,
        )
        logger.debug("AsyncEngine created")
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            bind=get_engine(),
            autoflush=False,
            expire_on_commit=False,
        )
        logger.debug("Async sessionmaker created")
    return _session_maker


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with get_session_maker()() as session:
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
        engine = get_engine()
        ctx = engine.begin()
        # Support both real AsyncEngine (returns async context manager)
        # and test mocks that return a coroutine yielding a context manager
        if inspect.isawaitable(ctx):
            ctx = await ctx  # type: ignore[assignment]
        async with ctx as conn:  # type: ignore[func-returns-value]
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection is healthy")
        return True
    except Exception as e:
        logger.error("Database connection check failed: %s", e)
        return False


async def close_db_connections() -> None:
    global engine, _engine, _session_maker
    try:
        # Dispose monkeypatched public engine if present
        if engine is not None:
            try:
                await engine.dispose()  # type: ignore[func-returns-value]
            except Exception:
                # MockEngine in unit tests may not implement dispose; ignore
                pass
            logger.info("Database connections (public engine) closed")
    except Exception as e:
        logger.error("Error closing public engine connections: %s", e)
    try:
        if _engine is not None:
            await _engine.dispose()
            logger.info("Database connections (private engine) closed")
    except Exception as e:
        logger.error("Error closing private engine connections: %s", e)
    finally:
        engine = None
        _engine = None
        _session_maker = None


async def get_db_info() -> dict:
    try:
        engine = get_engine()
        status = getattr(engine, "status", "healthy")
        return {"status": status}
    except Exception as e:
        logger.error("Error getting database info: %s", e)
        return {"status": "error", "message": str(e)}
