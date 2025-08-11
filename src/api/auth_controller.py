from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AuthenticationError
from db.database import get_db
from schemas.auth import AuthLogin, AuthRegister, TokenPayload
from schemas.responses import SuccessResponse
from schemas.users import UserOut
from services import auth_service, jwt_service

from .utils.cookies import clear_refresh_cookie, set_refresh_cookie
from .utils.request_context import extract_client, get_refresh_cookie

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post(
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


@auth_router.post(
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
    set_refresh_cookie(response, refresh_jwt)
    return data


@auth_router.post(
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
    refresh_jwt = get_refresh_cookie(request)
    user_agent, ip = extract_client(request)

    try:
        data, new_refresh = await auth_service.refresh(db=db, refresh_jwt=refresh_jwt, user_agent=user_agent, ip=ip)
    except AuthenticationError:
        # Clear potentially corrupted/expired refresh-cookie and re-raise the error.
        clear_refresh_cookie(response)
        raise

    set_refresh_cookie(response, new_refresh)
    return data


@auth_router.post(
    "/logout",
    response_model=SuccessResponse[str],
    summary="Logout from current session",
)
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[str]:
    refresh_jwt = request.cookies.get("__Host-rt")
    if not refresh_jwt:
        clear_refresh_cookie(response)
        return SuccessResponse[str].ok("Logged out")

    try:
        data = await auth_service.logout(db=db, refresh_jwt=refresh_jwt)
    except AuthenticationError:
        # Clear cookie even with invalid token, then return 401 via global handler.
        clear_refresh_cookie(response)
        raise

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
    return data
