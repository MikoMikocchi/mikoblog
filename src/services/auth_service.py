from datetime import UTC, datetime
import os
import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AuthenticationError, ConflictError, ValidationError
from core.security import get_password_hash, verify_password
from db.models.user import User
from db.repositories import user_repository
from schemas.auth import AuthLogin, AuthRegister, TokenPayload
from schemas.responses import SuccessResponse
from schemas.users import UserOut
from services import jwt_service


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _compute_access_expires_in_seconds() -> int:
    minutes = int(os.getenv("JWT_ACCESS_MINUTES", "15"))
    return minutes * 60


async def register(db: AsyncSession, payload: AuthRegister) -> SuccessResponse[UserOut]:
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
    if await user_repository.get_user_by_username(db, username):
        raise ConflictError("Username already registered")
    if await user_repository.get_user_by_email(db, email_clean):
        raise ConflictError("Email already registered")

    hashed_password = get_password_hash(pwd)

    # Attempt create; handle unique races deterministically
    try:
        db_user = await user_repository.create_user(
            db=db,
            username=username,
            email=email_clean,
            hashed_password=hashed_password,
        )
        # Persist transaction explicitly
        try:
            await db.commit()
        except IntegrityError as ie:  # Unique constraint could still trip here in rare races
            await db.rollback()
            raise ConflictError("Username or email already registered") from ie
    except IntegrityError as ie:
        # Repo-level integrity violation (pre-commit)
        raise ConflictError("Username or email already registered") from ie
    except Exception as e:
        # Map transient locking errors deterministically to Conflict when duplicates appear
        msg = str(e).lower()
        if "lock timeout" in msg or "locknotavailable" in msg or "could not obtain lock" in msg:
            if (await user_repository.get_user_by_username(db, username)) or (await user_repository.get_user_by_email(db, email_clean)):
                raise ConflictError("Username or email already registered") from e
        # Ensure transaction is not left open on unexpected errors
        try:
            await db.rollback()
        except Exception:
            pass
        raise

    return SuccessResponse[UserOut].ok(UserOut.model_validate(db_user))


async def _resolve_user_by_login(db: AsyncSession, username_or_email: str) -> User | None:
    # Repository functions return ORM User or None.
    user = await user_repository.get_user_by_username(db, username_or_email)
    if not user:
        user = await user_repository.get_user_by_email(db, username_or_email)
    return user


async def login(
    db: AsyncSession,
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
    user = await _resolve_user_by_login(db, payload.username_or_email)
    if not user:
        raise AuthenticationError("Invalid credentials")
    # Help static analyzers: assert presence of id attr, then set local user_id
    if not hasattr(user, "id"):
        raise AuthenticationError("Invalid user object")
    user_id: int = int(user.id)

    if not verify_password(payload.password, getattr(user, "hashed_password", "")):
        raise AuthenticationError("Invalid credentials")

    # Create tokens using jwt_service
    payload_out, refresh = await jwt_service.create_tokens_for_user(
        db=db,
        user_id=user_id,
        user_agent=user_agent,
        ip=ip,
    )
    return SuccessResponse[TokenPayload].ok(payload_out), refresh


async def refresh(
    db: AsyncSession,
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
    # Rotate tokens using jwt_service
    payload_out, new_refresh = await jwt_service.rotate_tokens(
        db=db,
        refresh_jwt=refresh_jwt,
        user_agent=user_agent,
        ip=ip,
    )
    return SuccessResponse[TokenPayload].ok(payload_out), new_refresh


async def logout(db: AsyncSession, refresh_jwt: str) -> SuccessResponse[str]:
    """
    Revoke refresh token from provided JWT.
    """
    await jwt_service.revoke_refresh_token(db=db, refresh_jwt=refresh_jwt)
    return SuccessResponse[str].ok("Logged out")


async def logout_all(db: AsyncSession, user_id: int) -> SuccessResponse[str]:
    """
    Revoke all active refresh tokens for the specified user.
    """
    await jwt_service.revoke_all_user_tokens(db=db, user_id=user_id)
    return SuccessResponse[str].ok("Logged out from all sessions")
