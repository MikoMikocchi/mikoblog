from fastapi import APIRouter, Body, Depends, Request, Response, status, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from schemas.auth import AuthLogin, AuthRegister, TokenPayload
from schemas.responses import SuccessResponse
from schemas.users import UserOut
from services import auth_service

from .utils.cookies import set_refresh_cookie, clear_refresh_cookie
from .utils.request_context import extract_client, get_refresh_cookie
from core.jwt import decode_token, validate_typ

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


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
    user_agent, ip = extract_client(request)
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
    refresh_jwt = get_refresh_cookie(request)
    user_agent, ip = extract_client(request)

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
    refresh_jwt = request.cookies.get("__Host-rt")
    if not refresh_jwt:
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
    refresh_jwt = get_refresh_cookie(request)

    # Decode locally to get user id; service performs stricter checks
    decoded = decode_token(refresh_jwt)
    validate_typ(decoded, expected_typ="refresh")
    sub = decoded.get("sub")
    if sub is None:
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
