from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AuthenticationError
from db.database import get_db
from schemas.auth import AuthLogin, AuthRegister, TokenPayload
from schemas.responses import SuccessResponse
from schemas.users import UserOut
from services import auth_service, jwt_service

from ...utils.cookies import clear_refresh_cookie, set_refresh_cookie
from ...utils.csrf import extract_csrf, require_csrf, set_csrf_cookie, validate_csrf_token
from ...utils.request_context import extract_client, get_refresh_cookie

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=SuccessResponse[UserOut],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    response_model_exclude_none=True,
)
async def register(
    payload: Annotated[AuthRegister, Body(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[UserOut]:
    return await auth_service.register(db=db, payload=payload)


@router.post(
    "/login",
    response_model=SuccessResponse[TokenPayload],
    summary="Login with username/email and password",
    response_model_exclude_none=True,
)
async def login(
    request: Request,
    response: Response,
    payload: Annotated[AuthLogin, Body(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[TokenPayload]:
    user_agent, ip = extract_client(request)
    data, refresh_jwt = await auth_service.login(db=db, payload=payload, user_agent=user_agent, ip=ip)
    # Set refresh cookie and CSRF cookie (for subsequent refresh/logout requests)
    set_refresh_cookie(response, refresh_jwt)
    set_csrf_cookie(response)
    return data


@router.post(
    "/refresh",
    response_model=SuccessResponse[TokenPayload],
    summary="Refresh access token using refresh cookie",
    response_model_exclude_none=True,
)
async def refresh(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[TokenPayload]:
    # CSRF check if enabled
    if require_csrf(request):
        cookie_val, header_val = extract_csrf(request)
        if not cookie_val or not header_val or not validate_csrf_token(cookie_val) or cookie_val != header_val:
            # Clear refresh cookie to be safe and reject
            clear_refresh_cookie(response)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")

    refresh_jwt = get_refresh_cookie(request)
    user_agent, ip = extract_client(request)
    try:
        data, new_refresh = await auth_service.refresh(db=db, refresh_jwt=refresh_jwt, user_agent=user_agent, ip=ip)
    except AuthenticationError:
        clear_refresh_cookie(response)
        raise
    set_refresh_cookie(response, new_refresh)
    # Refresh CSRF cookie as well (rotation optional but keeps symmetry)
    set_csrf_cookie(response)
    return data


@router.post(
    "/logout",
    response_model=SuccessResponse[str],
    summary="Logout from current session",
)
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[str]:
    # CSRF check if enabled
    if require_csrf(request):
        cookie_val, header_val = extract_csrf(request)
        if not cookie_val or not header_val or not validate_csrf_token(cookie_val) or cookie_val != header_val:
            clear_refresh_cookie(response)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")

    refresh_jwt = request.cookies.get("__Host-rt")
    if not refresh_jwt:
        clear_refresh_cookie(response)
        return SuccessResponse[str].ok("Logged out")
    try:
        data = await auth_service.logout(db=db, refresh_jwt=refresh_jwt)
    except AuthenticationError:
        clear_refresh_cookie(response)
        raise
    clear_refresh_cookie(response)
    # Clear CSRF cookie as session ends
    # Not strictly necessary, but reduces stale tokens exposure
    try:
        from ...utils.csrf import clear_csrf_cookie  # local import to avoid top-level import cycles

        clear_csrf_cookie(response)
    except Exception:
        pass
    return data


@router.post(
    "/logout-all",
    response_model=SuccessResponse[str],
    summary="Logout from all sessions",
)
async def logout_all(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[str]:
    refresh_jwt = get_refresh_cookie(request)
    try:
        user_id = jwt_service.validate_refresh_token_and_extract_user_id(refresh_jwt)
    except AuthenticationError:
        clear_refresh_cookie(response)
        raise
    data = await auth_service.logout_all(db=db, user_id=user_id)
    clear_refresh_cookie(response)
    try:
        from ...utils.csrf import clear_csrf_cookie

        clear_csrf_cookie(response)
    except Exception:
        pass
    return data
