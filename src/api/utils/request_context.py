from fastapi import Request

from core.exceptions import AuthenticationError


def extract_client(request: Request) -> tuple[str | None, str | None]:
    """
    Extract user-agent and client IP from request.
    Priority:
      1) X-Forwarded-For (first IP)
      2) X-Real-IP
      3) CF-Connecting-IP
      4) request.client.host
    """
    user_agent = request.headers.get("user-agent")

    xff = request.headers.get("x-forwarded-for")
    ip: str | None = None
    if xff:
        # Take the first non-empty IP, trimming spaces
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            ip = parts[0]
    if not ip:
        ip = request.headers.get("x-real-ip") or request.headers.get("cf-connecting-ip")
    if not ip and request.client:
        ip = request.client.host
    return user_agent, ip


def get_refresh_cookie(request: Request, *, cookie_name: str = "__Host-rt") -> str:
    """
    Read refresh token cookie or raise AuthenticationError; global handler maps it to 401.
    """
    refresh_jwt = request.cookies.get(cookie_name)
    if not refresh_jwt:
        raise AuthenticationError("Missing refresh cookie")
    return refresh_jwt
