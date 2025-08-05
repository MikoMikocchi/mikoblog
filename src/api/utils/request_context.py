from typing import Optional, Tuple
from fastapi import Request, HTTPException, status


def extract_client(request: Request) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract user-agent and client IP from request.
    Prefer X-Forwarded-For header when present (behind proxy), otherwise fallback to client.host.
    """
    user_agent = request.headers.get("user-agent")
    ip = request.headers.get("x-forwarded-for") or (
        request.client.host if request.client else None
    )
    return user_agent, ip


def get_refresh_cookie(request: Request, *, cookie_name: str = "__Host-rt") -> str:
    """
    Read refresh token cookie or raise 401 with proper WWW-Authenticate header.
    """
    refresh_jwt = request.cookies.get(cookie_name)
    if not refresh_jwt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh cookie",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return refresh_jwt
