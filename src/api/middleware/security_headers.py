from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from fastapi import Request
from fastapi.responses import Response

from core.config import settings

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import FastAPI


def register_security_headers_middleware(app: FastAPI) -> None:
    """Attach middleware that sets a hardened set of security headers."""

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:  # noqa: D401
        response = await call_next(request)
        # Only set HSTS in non-development environments
        if settings.environment != "development":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
        return response
