import os

from fastapi import Response

REFRESH_COOKIE_NAME = "__Host-rt"
# __Host- cookies MUST have Path="/" and Secure=true (and no Domain attr) per spec.
# See: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie#the__host- prefix
REFRESH_COOKIE_PATH = os.getenv("REFRESH_COOKIE_PATH", "/")
REFRESH_COOKIE_MAX_AGE = int(os.getenv("JWT_REFRESH_DAYS", "7")) * 24 * 60 * 60


def set_refresh_cookie(response: Response, refresh_jwt: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_jwt,
        max_age=REFRESH_COOKIE_MAX_AGE,
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
