from datetime import UTC, datetime, timedelta
import os
import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.exceptions import AuthenticationError, ConflictError, NotFoundError, ValidationError
from core.jwt import decode_token, encode_access_token, encode_refresh_token, make_jti, validate_typ
from core.security import get_password_hash, verify_password
from db.repositories import refresh_token_repository as rt_repo, user_repository
from schemas.auth import AuthLogin, AuthRegister, TokenPayload
from schemas.responses import SuccessResponse
from schemas.users import UserOut


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _compute_access_expires_in_seconds() -> int:
    minutes = int(os.getenv("JWT_ACCESS_MINUTES", "15"))
    return minutes * 60


def register(db: Session, payload: AuthRegister) -> SuccessResponse[UserOut]:
    """
    Create a new user and return UserOut.
    Performs optimistic uniqueness checks and hashes the password.
    Maps domain validation/conflict errors via global handler.
    """
    username = payload.username
    email_clean = payload.email.strip()
    if payload.email != email_clean:
        raise ValidationError("Invalid email address")

    # Enforce username business rules at domain layer
    if username.lower() in {"admin", "root", "system", "api", "test"}:
        raise ValidationError("Username not allowed")

    if not re.fullmatch(r"^[a-zA-Z0-9_-]+$", username):
        raise ValidationError("Invalid username format")

    # Password strength (mirror schemas guard for defense in depth)
    pwd = payload.password
    if not (
        len(pwd) >= 12
        and any(c.isupper() for c in pwd)
        and any(c.islower() for c in pwd)
        and any(c.isdigit() for c in pwd)
        and any(c in '!@#$%^&*(),.?":{}|<>' for c in pwd)
    ):
        raise ValidationError("Password does not meet complexity requirements")

    # Optimistic checks before attempting INSERT
    if user_repository.get_user_by_username(db, username):
        raise ConflictError("Username already registered")
    if user_repository.get_user_by_email(db, email_clean):
        raise ConflictError("Email already registered")

    hashed_password = get_password_hash(pwd)

    # Attempt create; handle unique races deterministically
    try:
        db_user = user_repository.create_user(
            db=db,
            username=username,
            email=email_clean,
            hashed_password=hashed_password,
        )
    except IntegrityError as ie:
        raise ConflictError("Username or email already registered") from ie
    except Exception as e:
        msg = str(e).lower()
        if "lock timeout" in msg or "locknotavailable" in msg or "could not obtain lock" in msg:
            if user_repository.get_user_by_username(db, username) or user_repository.get_user_by_email(db, email_clean):
                raise ConflictError("Username or email already registered") from e
        raise

    return SuccessResponse[UserOut].ok(UserOut.model_validate(db_user))


def _resolve_user_by_login(db: Session, username_or_email: str):
    # Repository functions return ORM User or None.
    user = user_repository.get_user_by_username(db, username_or_email)
    if not user:
        user = user_repository.get_user_by_email(db, username_or_email)
    return user


def login(
    db: Session,
    payload: AuthLogin,
    *,
    user_agent: str | None,
    ip: str | None,
) -> tuple[SuccessResponse[TokenPayload], str]:
    """
    Validate credentials, create refresh record and return:
      - SuccessResponse[TokenPayload] (access token info)
      - refresh_jwt string (to be set in cookie by controller)
    """
    user = _resolve_user_by_login(db, payload.username_or_email)
    if not user:
        raise AuthenticationError("Invalid credentials")
    # Help static analyzers: assert presence of id attr, then set local user_id
    if not hasattr(user, "id"):
        raise AuthenticationError("Invalid user object")
    user_id: int = int(user.id)  # type: ignore[attr-defined]

    if not verify_password(payload.password, getattr(user, "hashed_password", "")):
        raise AuthenticationError("Invalid credentials")

    # Create refresh token record (DB) and JWT pair
    now = _utcnow()
    refresh_expires = now + timedelta(days=7)
    jti = make_jti()

    rt_repo.create(
        db=db,
        user_id=user_id,
        jti=jti,
        issued_at=now,
        expires_at=refresh_expires,
        user_agent=user_agent,
        ip=ip,
    )

    access = encode_access_token(user_id, jti=make_jti())
    refresh = encode_refresh_token(user_id, jti=jti)

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
    user_agent: str | None,
    ip: str | None,
) -> tuple[SuccessResponse[TokenPayload], str]:
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
        raise AuthenticationError("Invalid refresh token")

    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise AuthenticationError("Invalid refresh token subject") from None

    # Check record state
    if not rt_repo.is_active(db, jti):
        raise AuthenticationError("Refresh token is not active")

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
        raise NotFoundError("Refresh token not found")

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
        raise AuthenticationError("Invalid refresh token")

    rt_repo.revoke_by_jti(db=db, jti=jti)
    return SuccessResponse[str].ok("Logged out")


def logout_all(db: Session, user_id: int) -> SuccessResponse[str]:
    """
    Revoke all active refresh tokens for the specified user.
    """
    rt_repo.revoke_all_for_user(db=db, user_id=user_id)
    return SuccessResponse[str].ok("Logged out from all sessions")
