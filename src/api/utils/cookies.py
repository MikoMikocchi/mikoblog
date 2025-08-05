from fastapi import Response

REFRESH_COOKIE_NAME = "__Host-rt"
REFRESH_COOKIE_PATH = "/auth"
REFRESH_COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds


def set_refresh_cookie(response: Response, refresh_jwt: str) -> None:
    """
    Set HTTP-only, Secure, SameSite=strict refresh cookie.
    Domain is not set (host-only). Path is /auth.
    """
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
    """Clear refresh cookie by setting Max-Age=0 on the same path."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value="",
        max_age=0,
        httponly=True,
        secure=True,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )
