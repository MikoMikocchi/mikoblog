from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.security import verify_password, get_password_hash
from core.jwt import (
    encode_access_token,
    encode_refresh_token,
    make_jti,
    decode_token,
    validate_typ,
)
from db.repositories import user_repository
from db.repositories import refresh_token_repository as rt_repo
from schemas.auth import AuthLogin, AuthRegister, TokenPayload
from schemas.responses import SuccessResponse
from schemas.users import UserOut


ACCESS_EXPIRES_MINUTES = 15  # mirrored by env; used to compute expires_in in responses


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _compute_access_expires_in_seconds() -> int:
    return ACCESS_EXPIRES_MINUTES * 60


def register(db: Session, payload: AuthRegister) -> SuccessResponse[UserOut]:
    """
    Create a new user and return UserOut.
    Performs uniqueness checks and hashes password.
    """
    if user_repository.get_user_by_username(db, payload.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already registered"
        )
    if user_repository.get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    hashed_password = get_password_hash(payload.password)
    db_user = user_repository.create_user(
        db=db,
        username=payload.username,
        email=payload.email,
        hashed_password=hashed_password,
    )

    return SuccessResponse[UserOut].ok(UserOut.model_validate(db_user))


def _resolve_user_by_login(db: Session, username_or_email: str):
    user = user_repository.get_user_by_username(db, username_or_email)
    if not user:
        user = user_repository.get_user_by_email(db, username_or_email)
    return user


def login(
    db: Session,
    payload: AuthLogin,
    *,
    user_agent: Optional[str],
    ip: Optional[str],
) -> Tuple[SuccessResponse[TokenPayload], str]:
    """
    Validate credentials, create refresh record and return:
      - SuccessResponse[TokenPayload] (access token info)
      - refresh_jwt string (to be set in cookie by controller)
    """
    user = _resolve_user_by_login(db, payload.username_or_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    if not verify_password(payload.password, getattr(user, "hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    # Create refresh token record (DB) and JWT pair
    now = _utcnow()
    refresh_expires = now + timedelta(days=7)
    jti = make_jti()
    rt_repo.create(
        db=db,
        user_id=int(getattr(user, "id")),
        jti=jti,
        issued_at=now,
        expires_at=refresh_expires,
        user_agent=user_agent,
        ip=ip,
    )

    access = encode_access_token(int(getattr(user, "id")), jti=make_jti())
    refresh = encode_refresh_token(int(getattr(user, "id")), jti=jti)

    payload_out = TokenPayload(
        access_token=access,
        token_type="bearer",
        expires_in=_compute_access_expires_in_seconds(),
    )
    return SuccessResponse[TokenPayload].ok(payload_out), refresh


def refresh(
    db: Session,
    refresh_jwt: str,
    *,
    user_agent: Optional[str],
    ip: Optional[str],
) -> Tuple[SuccessResponse[TokenPayload], str]:
    """
    Validate refresh JWT, rotate record:
      - revoke old
      - create new rotated record
      - issue new access and refresh JWT
    Returns SuccessResponse[TokenPayload] and new refresh JWT.
    """
    decoded = decode_token(refresh_jwt)
    validate_typ(decoded, expected_typ="refresh")

    sub = decoded.get("sub")
    jti = decoded.get("jti")
    if not sub or not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token subject",
        )

    # Check record state
    if not rt_repo.is_active(db, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is not active",
        )

    # Rotate
    now = _utcnow()
    new_jti = make_jti()
    new_expires = now + timedelta(days=7)
    new_record = rt_repo.rotate(
        db=db,
        old_jti=jti,
        new_jti=new_jti,
        user_id=user_id,
        issued_at=now,
        expires_at=new_expires,
        user_agent=user_agent,
        ip=ip,
    )
    if not new_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found"
        )

    # Issue new pair
    access = encode_access_token(user_id, jti=make_jti())
    new_refresh = encode_refresh_token(user_id, jti=new_jti)

    payload_out = TokenPayload(
        access_token=access,
        token_type="bearer",
        expires_in=_compute_access_expires_in_seconds(),
    )
    return SuccessResponse[TokenPayload].ok(payload_out), new_refresh


def logout(db: Session, refresh_jwt: str) -> SuccessResponse[str]:
    """
    Revoke refresh token from provided JWT.
    """
    decoded = decode_token(refresh_jwt)
    validate_typ(decoded, expected_typ="refresh")
    jti = decoded.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    rt_repo.revoke_by_jti(db=db, jti=jti)
    return SuccessResponse[str].ok("Logged out")


def logout_all(db: Session, user_id: int) -> SuccessResponse[str]:
    """
    Revoke all active refresh tokens for the specified user.
    """
    rt_repo.revoke_all_for_user(db=db, user_id=user_id)
    return SuccessResponse[str].ok("Logged out from all sessions")
