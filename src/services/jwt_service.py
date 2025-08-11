from datetime import UTC, datetime, timedelta
import os

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AuthenticationError
from core.jwt import decode_token, encode_access_token, encode_refresh_token, make_jti, validate_typ
from db.repositories import refresh_token_repository as rt_repo
from schemas.auth import TokenPayload


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _compute_access_expires_in_seconds() -> int:
    minutes = int(os.getenv("JWT_ACCESS_MINUTES", "15"))
    return minutes * 60


async def create_tokens_for_user(db: AsyncSession, user_id: int, *, user_agent: str | None, ip: str | None) -> tuple[TokenPayload, str]:
    """
    Create access and refresh tokens for a user.
    Returns tuple of (TokenPayload, refresh_token_string).
    """
    # Create refresh token record (DB) and JWT pair
    now = _utcnow()
    refresh_days = int(os.getenv("JWT_REFRESH_DAYS", "7"))
    refresh_expires = now + timedelta(days=refresh_days)
    jti = make_jti()

    await rt_repo.create(
        db=db,
        user_id=user_id,
        jti=jti,
        issued_at=now,
        expires_at=refresh_expires,
        user_agent=user_agent,
        ip=ip,
    )
    # Ensure refresh record persisted
    try:
        await db.commit()
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise

    access = encode_access_token(user_id, jti=make_jti())
    refresh = encode_refresh_token(user_id, jti=jti)

    payload = TokenPayload(
        access_token=access,
        token_type="bearer",
        expires_in=_compute_access_expires_in_seconds(),
    )
    return payload, refresh


async def rotate_tokens(db: AsyncSession, refresh_jwt: str, *, user_agent: str | None, ip: str | None) -> tuple[TokenPayload, str]:
    """
    Validate refresh JWT, rotate record:
      - revoke old
      - create new rotated record
      - issue new access and refresh JWT
    Returns tuple of (TokenPayload, new_refresh_token_string).
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
    if not await rt_repo.is_active(db, jti):
        raise AuthenticationError("Refresh token is not active")

    # Rotate
    now = _utcnow()
    new_jti = make_jti()
    refresh_days = int(os.getenv("JWT_REFRESH_DAYS", "7"))
    new_expires = now + timedelta(days=refresh_days)
    new_record = await rt_repo.rotate(
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
        raise AuthenticationError("Refresh token not found")
    # Persist rotation before issuing tokens
    try:
        await db.commit()
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise

    # Issue new pair
    access = encode_access_token(user_id, jti=make_jti())
    new_refresh = encode_refresh_token(user_id, jti=new_jti)

    payload = TokenPayload(
        access_token=access,
        token_type="bearer",
        expires_in=_compute_access_expires_in_seconds(),
    )
    return payload, new_refresh


async def revoke_refresh_token(db: AsyncSession, refresh_jwt: str) -> None:
    """
    Revoke refresh token from provided JWT.
    """
    decoded = decode_token(refresh_jwt)
    validate_typ(decoded, expected_typ="refresh")
    jti = decoded.get("jti")
    if not jti:
        raise AuthenticationError("Invalid refresh token")

    await rt_repo.revoke_by_jti(db=db, jti=jti)
    try:
        await db.commit()
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise


async def revoke_all_user_tokens(db: AsyncSession, user_id: int) -> None:
    """
    Revoke all active refresh tokens for the specified user.
    """
    await rt_repo.revoke_all_for_user(db=db, user_id=user_id)
    try:
        await db.commit()
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise


def validate_refresh_token_and_extract_user_id(refresh_jwt: str) -> int:
    """
    Validate refresh JWT and extract user ID.
    """
    decoded = decode_token(refresh_jwt)
    validate_typ(decoded, expected_typ="refresh")
    sub = decoded.get("sub")
    if sub is None:
        raise AuthenticationError("Invalid refresh token")
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise AuthenticationError("Invalid refresh token subject") from None
    return user_id
