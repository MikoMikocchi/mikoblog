import logging
from datetime import datetime
from typing import Optional, Iterable

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from db.models.refresh_token import RefreshToken
from db.utils import transactional

logger = logging.getLogger(__name__)


def get_by_jti(db: Session, jti: str) -> Optional[RefreshToken]:
    """Fetch refresh token by its unique jti."""
    try:
        return db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    except SQLAlchemyError as e:
        logger.error("DB error while fetching refresh token by jti=%s: %s", jti, e)
        raise


def get_active_for_user(db: Session, user_id: int) -> Iterable[RefreshToken]:
    """List active (not revoked and not expired) refresh tokens for a user."""
    now = datetime.utcnow()
    try:
        return (
            db.query(RefreshToken)
            .filter(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .order_by(RefreshToken.issued_at.desc())
            .all()
        )
    except SQLAlchemyError as e:
        logger.error(
            "DB error while listing active refresh tokens for user %s: %s", user_id, e
        )
        raise


@transactional
def create(
    db: Session,
    *,
    user_id: int,
    jti: str,
    issued_at: datetime,
    expires_at: datetime,
    rotated_from_jti: Optional[str] = None,
    user_agent: Optional[str] = None,
    ip: Optional[str] = None,
) -> RefreshToken:
    """Create a new refresh token record."""
    try:
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
        db.flush()
        db.refresh(token)
        logger.info("Created refresh token jti=%s for user_id=%s", jti, user_id)
        return token
    except SQLAlchemyError as e:
        logger.error(
            "DB error while creating refresh token for user %s: %s", user_id, e
        )
        raise


@transactional
def revoke_by_jti(
    db: Session, jti: str, *, revoked_at: Optional[datetime] = None
) -> bool:
    """Revoke a refresh token by jti. Returns True if updated."""
    revoked_at = revoked_at or datetime.utcnow()
    try:
        token = get_by_jti(db, jti)
        if token is None:
            logger.info("Skip revoke: refresh token jti=%s not found", jti)
            return False
        # Проверяем именно значение поля, а не ColumnElement
        if getattr(token, "revoked_at", None) is not None:
            logger.debug(
                "Refresh token jti=%s already revoked at %s",
                jti,
                getattr(token, "revoked_at", None),
            )
            return True
        setattr(token, "revoked_at", revoked_at)
        db.flush()
        db.refresh(token)
        logger.info("Revoked refresh token jti=%s", jti)
        return True
    except SQLAlchemyError as e:
        logger.error("DB error while revoking refresh token jti=%s: %s", jti, e)
        raise


@transactional
def revoke_all_for_user(
    db: Session, user_id: int, *, revoked_at: Optional[datetime] = None
) -> int:
    """Revoke all active refresh tokens for a user. Returns count affected."""
    revoked_at = revoked_at or datetime.utcnow()
    try:
        tokens = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .all()
        )
        count = 0
        for t in tokens:
            # безопасно присваиваем значение через setattr для обхода статического анализа
            setattr(t, "revoked_at", revoked_at)
            count += 1
        if count:
            db.flush()
        logger.info("Revoked %s refresh tokens for user_id=%s", count, user_id)
        return count
    except SQLAlchemyError as e:
        logger.error(
            "DB error while revoking all refresh tokens for user %s: %s", user_id, e
        )
        raise


@transactional
def rotate(
    db: Session,
    *,
    old_jti: str,
    new_jti: str,
    user_id: int,
    issued_at: datetime,
    expires_at: datetime,
    user_agent: Optional[str] = None,
    ip: Optional[str] = None,
) -> Optional[RefreshToken]:
    """
    Rotate a refresh token:
      - revoke old token (revoked_at = now)
      - create new token with rotated_from_jti = old_jti
    Returns the new token or None if old not found.
    """
    now = datetime.utcnow()
    try:
        old = get_by_jti(db, old_jti)
        if not old:
            logger.info("Skip rotate: old refresh token jti=%s not found", old_jti)
            return None

        # Mark old as revoked if not already
        if getattr(old, "revoked_at", None) is None:
            setattr(old, "revoked_at", now)

        # Create new rotated token
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
        db.flush()
        db.refresh(new_token)
        logger.info("Rotated refresh token old_jti=%s -> new_jti=%s", old_jti, new_jti)
        return new_token
    except SQLAlchemyError as e:
        logger.error(
            "DB error while rotating refresh token old_jti=%s -> new_jti=%s: %s",
            old_jti,
            new_jti,
            e,
        )
        raise


def is_active(db: Session, jti: str, *, at: Optional[datetime] = None) -> bool:
    """Check if refresh token with jti is active (not revoked, not expired)."""
    at = at or datetime.utcnow()
    try:
        t = get_by_jti(db, jti)
        if t is None:
            return False
        # Явно получаем значения полей экземпляра
        revoked_at_value = getattr(t, "revoked_at", None)
        if revoked_at_value is not None:
            return False
        expires_at_value = getattr(t, "expires_at", None)
        if expires_at_value is None or expires_at_value <= at:
            return False
        return True
    except SQLAlchemyError as e:
        logger.error("DB error while checking active state for jti=%s: %s", jti, e)
        raise
