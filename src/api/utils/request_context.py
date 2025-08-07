from fastapi import Request

from core.exceptions import AuthenticationError


def extract_client(request: Request) -> tuple[str | None, str | None]:
    """
    Extract user-agent and client IP from request.
    Prefer X-Forwarded-For header when present (behind proxy), otherwise fallback to client.host.
    """
    user_agent = request.headers.get("user-agent")
    ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else None)
    return user_agent, ip


def get_refresh_cookie(request: Request, *, cookie_name: str = "__Host-rt") -> str:
    """
    Read refresh token cookie or raise AuthenticationError; global handler maps it to 401.
    """
    refresh_jwt = request.cookies.get(cookie_name)
    if not refresh_jwt:
        raise AuthenticationError("Missing refresh cookie")
    return refresh_jwt
