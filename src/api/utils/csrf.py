from __future__ import annotations

import hmac
import os
from secrets import token_urlsafe
from typing import Literal

from fastapi import Request, Response

CSRF_COOKIE_NAME = "__Host-csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "strict"
CSRF_COOKIE_SECURE = True  # __Host- cookies require secure
CSRF_COOKIE_PATH = "/"
CSRF_COOKIE_HTTPONLY = False  # must be readable by JS to send header explicitly if SPA


def _get_secret() -> bytes:
    # Derive a process secret from env or random fallback (non-persistent)
    # For production set CSRF_SECRET explicitly for stable validation across processes
    secret = os.getenv("CSRF_SECRET")
    if secret:
        return secret.encode("utf-8")
    return os.urandom(32)


def _sign(value: str) -> str:
    secret = _get_secret()
    mac = hmac.new(secret, msg=value.encode("utf-8"), digestmod="sha256").hexdigest()
    return mac


def generate_csrf_token() -> str:
    raw = token_urlsafe(32)
    sig = _sign(raw)
    return f"{raw}.{sig}"


def validate_csrf_token(token: str) -> bool:
    try:
        raw, sig = token.split(".", 1)
    except ValueError:
        return False
    expected = _sign(raw)
    return hmac.compare_digest(sig, expected)


def set_csrf_cookie(response: Response, token: str | None = None) -> str:
    value = token or generate_csrf_token()
    response.set_cookie(
        CSRF_COOKIE_NAME,
        value,
        samesite=CSRF_COOKIE_SAMESITE,
        secure=CSRF_COOKIE_SECURE,
        httponly=CSRF_COOKIE_HTTPONLY,
        path=CSRF_COOKIE_PATH,
    )
    return value


def clear_csrf_cookie(response: Response) -> None:
    response.delete_cookie(
        CSRF_COOKIE_NAME,
        path=CSRF_COOKIE_PATH,
    )


def extract_csrf(request: Request) -> tuple[str | None, str | None]:
    cookie_val = request.cookies.get(CSRF_COOKIE_NAME)
    header_val = request.headers.get(CSRF_HEADER_NAME)
    return cookie_val, header_val


def csrf_enabled() -> bool:
    return os.getenv("CSRF_ENABLE", "false").lower() in ("1", "true", "yes", "on")


def require_csrf(request: Request) -> bool:
    """Return True if CSRF validation should be enforced for this request."""
    if not csrf_enabled():
        return False
    # Allow only same-site origins by default, but keep it simple here
    return True
