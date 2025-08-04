from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Response, status, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from schemas.auth import AuthLogin, AuthRegister, TokenPayload
from schemas.responses import SuccessResponse
from schemas.users import UserOut
from services import auth_service

auth_router = APIRouter(prefix="/auth", tags=["Auth"])

# Cookie settings for refresh token
REFRESH_COOKIE_NAME = "__Host-rt"
REFRESH_COOKIE_PATH = "/auth"
REFRESH_COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds


def set_refresh_cookie(response: Response, refresh_jwt: str) -> None:
    """
    Set HTTP-only, Secure, SameSite=strict refresh cookie as agreed.
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


@auth_router.post(
    "/register",
    response_model=SuccessResponse[UserOut],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    response_model_exclude_none=True,
)
async def register(payload: AuthRegister = Body(...), db: Session = Depends(get_db)):
    return auth_service.register(db=db, payload=payload)


@auth_router.post(
    "/login",
    response_model=SuccessResponse[TokenPayload],
    summary="Login with username/email and password",
    response_model_exclude_none=True,
)
async def login(
    request: Request,
    response: Response,
    payload: AuthLogin = Body(...),
    db: Session = Depends(get_db),
):
    user_agent = request.headers.get("user-agent")
    # Prefer X-Forwarded-For if present (behind proxy), fallback to client.host
    ip = (
        request.headers.get("x-forwarded-for") or request.client.host
        if request.client
        else None
    )

    data, refresh_jwt = auth_service.login(
        db=db, payload=payload, user_agent=user_agent, ip=ip
    )
    set_refresh_cookie(response, refresh_jwt)
    return data


@auth_router.post(
    "/refresh",
    response_model=SuccessResponse[TokenPayload],
    summary="Refresh access token using refresh cookie",
    response_model_exclude_none=True,
)
async def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_jwt = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_jwt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh cookie",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_agent = request.headers.get("user-agent")
    ip = (
        request.headers.get("x-forwarded-for") or request.client.host
        if request.client
        else None
    )

    data, new_refresh = auth_service.refresh(
        db=db, refresh_jwt=refresh_jwt, user_agent=user_agent, ip=ip
    )
    set_refresh_cookie(response, new_refresh)
    return data


@auth_router.post(
    "/logout",
    response_model=SuccessResponse[str],
    summary="Logout from current session",
)
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_jwt = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_jwt:
        # Idempotent logout: still clear cookie to ensure client state is clean
        clear_refresh_cookie(response)
        return SuccessResponse[str].ok("Logged out")

    data = auth_service.logout(db=db, refresh_jwt=refresh_jwt)
    clear_refresh_cookie(response)
    return data


@auth_router.post(
    "/logout-all",
    response_model=SuccessResponse[str],
    summary="Logout from all sessions",
)
async def logout_all(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    # For security, require refresh cookie to verify the user identity context.
    refresh_jwt = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_jwt:
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh cookie",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode refresh locally just to obtain user id; auth_service.refresh already does stricter checks,
    # but here we only need to identify the user for logout-all. We reuse the service by first refreshing decode.
    # To avoid duplication, perform a lightweight decode inline via auth_service.refresh dependencies:
    # Use core.jwt.decode_token to read sub without rotation.
    from core.jwt import decode_token, validate_typ  # local import to avoid circulars

    decoded = decode_token(refresh_jwt)
    validate_typ(decoded, expected_typ="refresh")
    sub = decoded.get("sub")
    if not sub:
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    data = auth_service.logout_all(db=db, user_id=user_id)
    clear_refresh_cookie(response)
    return data
