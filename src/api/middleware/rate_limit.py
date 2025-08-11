from __future__ import annotations

from collections import deque
from collections.abc import Awaitable, Callable
from datetime import datetime
from time import time
from typing import TYPE_CHECKING

from fastapi import Request
from fastapi.responses import JSONResponse, Response

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import FastAPI


# Simple in-memory per-IP rate limiter for auth endpoints
_LOGIN_RPM_DEFAULT = 10
_REFRESH_RPM_DEFAULT = 30
_WINDOW_SECONDS = 60.0


def register_auth_rate_limit_middleware(app: FastAPI) -> None:
    import os

    login_rpm = int(os.getenv("LOGIN_RATE_LIMIT_PER_MINUTE", str(_LOGIN_RPM_DEFAULT)))
    refresh_rpm = int(os.getenv("REFRESH_RATE_LIMIT_PER_MINUTE", str(_REFRESH_RPM_DEFAULT)))
    buckets: dict[tuple[str, str], deque[float]] = {}

    def _rate_limit_key(ip: str | None, route: str) -> tuple[str, str]:
        return (ip or "unknown", route)

    def _allow(rate_per_minute: int, key: tuple[str, str]) -> bool:
        if rate_per_minute <= 0:
            return True
        now = time()
        cutoff = now - _WINDOW_SECONDS
        q = buckets.setdefault(key, deque())
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= rate_per_minute:
            return False
        q.append(now)
        return True

    @app.middleware("http")
    async def rate_limit_auth(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:  # noqa: D401
        path = request.url.path
        is_login = path.endswith("/auth/login")
        is_refresh = path.endswith("/auth/refresh")
        if not (is_login or is_refresh):
            return await call_next(request)

        ip = request.headers.get("x-forwarded-for")
        if ip:
            parts = [p.strip() for p in ip.split(",") if p.strip()]
            ip = parts[0] if parts else None
        if not ip:
            ip = request.headers.get("x-real-ip") or request.headers.get("cf-connecting-ip")
        if not ip and request.client:
            ip = request.client.host

        limit = login_rpm if is_login else refresh_rpm
        key = _rate_limit_key(ip, "login" if is_login else "refresh")
        if not _allow(limit, key):
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "Too many requests, please try again later.",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        return await call_next(request)
