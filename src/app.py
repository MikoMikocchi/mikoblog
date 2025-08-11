from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from api.handlers.exceptions import register_exception_handlers
from api.middleware.rate_limit import register_auth_rate_limit_middleware
from api.middleware.request_id import register_request_id_middleware
from api.middleware.security_headers import register_security_headers_middleware
from api.routes.system import router as system_router
from api.routes.v1 import router as v1_router
from core.config import settings
from core.logging import setup_logging
from db.database import check_db_connection, close_db_connections

# Initialize global logging configuration early
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting up MikoBlog API")

    try:
        # Optional DB health check controlled by environment flag DB_CHECK_ON_START
        db_check_env = os.getenv("DB_CHECK_ON_START", "true").lower() in ("1", "true", "yes")
        if db_check_env:
            ok = await check_db_connection()
            if ok:
                logger.info("Database connection verified")
            else:
                logger.error("Database connection failed")
                raise RuntimeError("Database connection failed")
        else:
            logger.debug("Skipping DB connection check on startup (DB_CHECK_ON_START=false)")

        logger.info("Application startup completed")

    except Exception as e:  # pragma: no cover - startup failures should be visible in logs
        logger.error(f"Application startup failed: {e}")
        raise

    yield

    logger.info("Shutting down MikoBlog API")

    try:
        await close_db_connections()
        logger.info("Database connections closed")
        logger.info("Application shutdown completed")

    except Exception as e:  # pragma: no cover
        logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description=settings.api_description,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        openapi_url="/openapi.json" if settings.environment != "production" else None,
    )

    # Routers
    app.include_router(v1_router)
    app.include_router(system_router)

    # CORS (from env CORS_ALLOW_ORIGINS comma-separated)
    _cors_env = os.getenv("CORS_ALLOW_ORIGINS", "")
    _cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
    if _cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=_cors_origins,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            allow_credentials=False,
            max_age=3600,
        )

    # Middlewares
    register_request_id_middleware(app)
    register_security_headers_middleware(app)
    register_auth_rate_limit_middleware(app)

    # Exception handlers
    register_exception_handlers(app)

    return app
