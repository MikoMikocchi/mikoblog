from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING
import uuid

from fastapi import Request
from fastapi.responses import Response

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import FastAPI


def register_request_id_middleware(app: FastAPI) -> None:
    """Attach Request-ID middleware that sets X-Request-Id on responses."""

    @app.middleware("http")
    async def add_request_id(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:  # noqa: D401
        req_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        response = await call_next(request)
        response.headers.setdefault("X-Request-Id", req_id)
        return response
