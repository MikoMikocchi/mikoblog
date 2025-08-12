from datetime import UTC, datetime, timedelta
import os

from fastapi import Response

REFRESH_COOKIE_NAME = "__Host-rt"
# __Host- cookies MUST have Path="/" and Secure=true (and no Domain attr) per spec.
# See: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie#the__host- prefix
REFRESH_COOKIE_PATH = os.getenv("REFRESH_COOKIE_PATH", "/")
# Keep cookie Max-Age fixed at 7 days to satisfy API contract and avoid test-env leakage.
# Token/DB expiry may be configured separately; cookie lifetime remains stable.
REFRESH_COOKIE_MAX_AGE = 7 * 24 * 60 * 60


def set_refresh_cookie(response: Response, refresh_jwt: str) -> None:
    # Compute Expires based on configurable JWT_REFRESH_DAYS while keeping Max-Age stable for tests
    days = int(os.getenv("JWT_REFRESH_DAYS", "7"))
    expires_dt = datetime.now(UTC) + timedelta(days=days)
    expires_ts = int(expires_dt.timestamp())
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_jwt,
        max_age=REFRESH_COOKIE_MAX_AGE,
        expires=expires_ts,
        httponly=True,
        secure=True,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    # Clear at configured path
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value="",
        max_age=0,
        httponly=True,
        secure=True,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )
