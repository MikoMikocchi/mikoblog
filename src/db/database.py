import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import QueuePool

from core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

if not settings.database:
    raise RuntimeError("Database configuration not initialized")

engine = create_engine(
    settings.database.url,
    echo=settings.database.echo,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_timeout=settings.database.pool_timeout,
    pool_pre_ping=settings.database.pool_pre_ping,
    poolclass=QueuePool,
    pool_recycle=3600,
    connect_args={
        "options": "-c timezone=utc",
        "application_name": "mikoblog_api",
    },
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def init_db() -> None:
    try:
        logger.info("Initializing database...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {e}")
        raise


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        logger.debug("Database session created")
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database error in session: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in database session: {e}")
        db.rollback()
        raise
    finally:
        db.close()
        logger.debug("Database session closed")


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        logger.debug("Database context session created")
        yield db
        db.commit()
    except SQLAlchemyError as e:
        logger.error(f"Database error in context session: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in context session: {e}")
        db.rollback()
        raise
    finally:
        db.close()
        logger.debug("Database context session closed")


def check_db_connection() -> bool:
    try:
        with get_db_context() as db:
            db.execute(text("SELECT 1"))
        logger.info("Database connection is healthy")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def close_db_connections() -> None:
    try:
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


def get_db_info() -> dict:
    try:
        pool = engine.pool
        return {
            "pool_size": getattr(pool, "_pool_size", "N/A"),
            "checked_in": getattr(pool, "_checked_in", "N/A"),
            "checked_out": getattr(pool, "_checked_out", "N/A"),
            "overflow": getattr(pool, "_overflow", "N/A"),
            "status": "healthy",
        }
    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        return {"status": "error", "message": str(e)}
