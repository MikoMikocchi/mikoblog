from contextlib import asynccontextmanager
from datetime import datetime
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from api.auth_controller import auth_router
from api.post_controller import posts_router
from api.user_controller import users_router
from core.config import settings
from core.exceptions import AuthenticationError, BlogException, map_exception_to_http
from core.logging import setup_logging
from db.database import check_db_connection, close_db_connections

# Initialize global logging configuration early
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up MikoBlog API")

    try:
        # Optional DB health check controlled by environment flag DB_CHECK_ON_START
        import os as _os

        db_check_env = _os.getenv("DB_CHECK_ON_START", "true").lower() in (
            "1",
            "true",
            "yes",
        )
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

    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise

    yield

    logger.info("Shutting down MikoBlog API")

    try:
        await close_db_connections()
        logger.info("Database connections closed")
        logger.info("Application shutdown completed")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


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


app.include_router(users_router, prefix="/api/v1")
app.include_router(posts_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")


# Global handler for domain exceptions
@app.exception_handler(BlogException)
async def blog_exception_handler(request: Request, exc: BlogException):
    # Log the exception for debugging purposes
    logger.error("BlogException occurred: %s", exc, exc_info=True)
    http_exc = map_exception_to_http(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content={
            "success": False,
            "message": http_exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "error": {"type": exc.__class__.__name__},
        },
        headers=getattr(http_exc, "headers", None) or {},
    )


# Special handler for auth errors (if raised explicitly)
@app.exception_handler(AuthenticationError)
async def auth_exception_handler(request: Request, exc: AuthenticationError):
    # Log the exception for debugging purposes
    logger.error("AuthenticationError occurred: %s", exc, exc_info=True)
    http_exc = map_exception_to_http(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content={
            "success": False,
            "message": http_exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "error": {"type": exc.__class__.__name__},
        },
        headers=getattr(http_exc, "headers", None) or {},
    )


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    return {
        "success": True,
        "message": f"Welcome to {settings.api_title}",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health",
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
        log_level=settings.logging.level.lower(),
        access_log=settings.environment == "development",
    )
