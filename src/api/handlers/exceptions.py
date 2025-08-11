from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse

from core.exceptions import AuthenticationError, BlogException, map_exception_to_http

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import FastAPI, Request


def register_exception_handlers(app: FastAPI) -> None:
    """Register application-wide exception handlers."""

    @app.exception_handler(BlogException)
    async def blog_exception_handler(request: Request, exc: BlogException) -> JSONResponse:  # noqa: D401
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

    @app.exception_handler(AuthenticationError)
    async def auth_exception_handler(request: Request, exc: AuthenticationError) -> JSONResponse:  # noqa: D401
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
