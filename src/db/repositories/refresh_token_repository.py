from collections.abc import Iterable
from datetime import datetime
import logging

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.refresh_token import RefreshToken
from db.repositories.decorators import handle_db_errors, with_retry

logger = logging.getLogger(__name__)


@with_retry(log_prefix="fetching refresh token by jti")
async def get_by_jti(db: AsyncSession, jti: str) -> RefreshToken | None:
    """Fetch refresh token by its unique jti."""
    stmt = select(RefreshToken).where(RefreshToken.jti == jti)
    res = await db.execute(stmt)
    return res.scalars().first()


@with_retry(log_prefix="listing active refresh tokens for user")
async def get_active_for_user(db: AsyncSession, user_id: int) -> Iterable[RefreshToken]:
    """List active (not revoked and not expired) refresh tokens for a user."""
    now = datetime.utcnow()
    stmt = (
        select(RefreshToken)
        .where(
            and_(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
        )
        .order_by(RefreshToken.issued_at.desc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


@with_retry(log_prefix="creating refresh token for user")
async def create(
    db: AsyncSession,
    *,
    user_id: int,
    jti: str,
    issued_at: datetime,
    expires_at: datetime,
    rotated_from_jti: str | None = None,
    user_agent: str | None = None,
    ip: str | None = None,
) -> RefreshToken:
    """Create a new refresh token record."""
    token = RefreshToken(
        user_id=user_id,
        jti=jti,
        issued_at=issued_at,
        expires_at=expires_at,
        rotated_from_jti=rotated_from_jti,
        user_agent=user_agent,
        ip=ip,
    )
    db.add(token)
    await db.flush()
    await db.refresh(token)
    logger.info("Created refresh token jti=%s for user_id=%s", jti, user_id)
    return token


@with_retry(log_prefix="revoking refresh token")
async def revoke_by_jti(db: AsyncSession, jti: str, *, revoked_at: datetime | None = None) -> bool:
    """Revoke a refresh token by jti. Returns True if updated."""
    revoked_at = revoked_at or datetime.utcnow()
    token = await get_by_jti(db, jti)
    if token is None:
        logger.info("Skip revoke: refresh token jti=%s not found", jti)
        return False
    if getattr(token, "revoked_at", None) is not None:
        logger.debug("Refresh token jti=%s already revoked at %s", jti, getattr(token, "revoked_at", None))
        return True
    object.__setattr__(token, "revoked_at", revoked_at)
    await db.flush()
    await db.refresh(token)
    logger.info("Revoked refresh token jti=%s", jti)
    return True


@with_retry(log_prefix="revoking all refresh tokens for user")
async def revoke_all_for_user(db: AsyncSession, user_id: int, *, revoked_at: datetime | None = None) -> int:
    """Revoke all active refresh tokens for a user. Returns count affected."""
    revoked_at = revoked_at or datetime.utcnow()
    stmt = select(RefreshToken).where(and_(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)))
    res = await db.execute(stmt)
    tokens = list(res.scalars().all())
    count = 0
    for t in tokens:
        object.__setattr__(t, "revoked_at", revoked_at)
        count += 1
    if count:
        await db.flush()
    logger.info("Revoked %s refresh tokens for user_id=%s", count, user_id)
    return count


@with_retry(log_prefix="rotating refresh token")
async def rotate(
    db: AsyncSession,
    *,
    old_jti: str,
    new_jti: str,
    user_id: int,
    issued_at: datetime,
    expires_at: datetime,
    user_agent: str | None = None,
    ip: str | None = None,
) -> RefreshToken | None:
    """
    Rotate a refresh token:
      - revoke old token (revoked_at = now)
      - create new token with rotated_from_jti = old_jti
    Returns the new token or None if old not found.
    """
    now = datetime.utcnow()
    old = await get_by_jti(db, old_jti)
    if not old:
        logger.info("Skip rotate: old refresh token jti=%s not found", old_jti)
        return None

    if getattr(old, "revoked_at", None) is None:
        object.__setattr__(old, "revoked_at", now)

    new_token = RefreshToken(
        user_id=user_id,
        jti=new_jti,
        issued_at=issued_at,
        expires_at=expires_at,
        rotated_from_jti=old_jti,
        user_agent=user_agent,
        ip=ip,
    )
    db.add(new_token)
    await db.flush()
    await db.refresh(new_token)
    logger.info("Rotated refresh token old_jti=%s -> new_jti=%s", old_jti, new_jti)
    return new_token


@handle_db_errors()
async def is_active(db: AsyncSession, jti: str, *, at: datetime | None = None) -> bool:
    """Check if refresh token with jti is active (not revoked, not expired)."""
    at = at or datetime.utcnow()
    t = await get_by_jti(db, jti)
    if t is None:
        return False
    revoked_at_value = getattr(t, "revoked_at", None)
    if revoked_at_value is not None:
        return False
    expires_at_value = getattr(t, "expires_at", None)
    if expires_at_value is None or expires_at_value <= at:
        return False
    return True
