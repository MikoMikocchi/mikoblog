import logging
from typing import Any, cast

from sqlalchemy import and_, text as _sql_text
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from db.models.user import User
from db.utils import transactional

logger = logging.getLogger(__name__)


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Return a user by primary key.

    Args:
        db: SQLAlchemy session.
        user_id: User id.

    Returns:
        Optional[User]: User instance if found, else None.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.info("User with id %s not found", user_id)
        return user
    except SQLAlchemyError as e:
        logger.error("Database error while fetching user %s: %s", user_id, e)
        raise
    except Exception as e:
        logger.error("Unexpected error while fetching user %s: %s", user_id, e)
        raise


def get_user_by_username(db: Session, username: str) -> User | None:
    """Return a user by exact username."""
    try:
        return db.query(User).filter(User.username == username).first()
    except SQLAlchemyError as e:
        logger.error("Database error while fetching user by username '%s': %s", username, e)
        raise
    except Exception as e:
        logger.error("Unexpected error while fetching user by username '%s': %s", username, e)
        raise


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return a user by exact email."""
    try:
        return db.query(User).filter(User.email == email).first()
    except SQLAlchemyError as e:
        logger.error("Database error while fetching user by email '%s': %s", email, e)
        raise
    except Exception as e:
        logger.error("Unexpected error while fetching user by email '%s': %s", email, e)
        raise


def count_users(db: Session, username: str | None = None, email: str | None = None) -> int:
    """Count users with optional exact filters.

    Args:
        db: Session.
        username: Exact username filter.
        email: Exact email filter.

    Returns:
        int: Total count.
    """
    try:
        query = db.query(User)
        conditions = []
        if username is not None:
            conditions.append(User.username == username)
        if email is not None:
            conditions.append(User.email == email)
        if conditions:
            query = query.filter(and_(*conditions))
        return query.count()
    except SQLAlchemyError as e:
        logger.error("Database error while counting users: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error while counting users: %s", e)
        raise


def get_users_paginated(
    db: Session,
    offset: int,
    limit: int,
    username: str | None = None,
    email: str | None = None,
) -> list[User]:
    """Return users page with optional exact filters, ordered by id ASC.

    Args:
        db: Session.
        offset: Offset >= 0.
        limit: Limit > 0.
        username: Exact username filter.
        email: Exact email filter.

    Returns:
        list[User]: Users slice.
    """
    try:
        query = db.query(User)
        conditions = []
        if username is not None:
            conditions.append(User.username == username)
        if email is not None:
            conditions.append(User.email == email)
        if conditions:
            query = query.filter(and_(*conditions))
        users = query.order_by(User.id.asc()).offset(offset).limit(limit).all()
        return users
    except SQLAlchemyError as e:
        logger.error("Database error while listing users: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error while listing users: %s", e)
        raise


@transactional
def create_user(db: Session, username: str, email: str, hashed_password: str) -> User:
    """Create new user under transactional boundary using ON CONFLICT to avoid index lock waits."""

    # One short retry for rare lock/deadlock on CI

    while True:
        try:
            # Reasonable local timeouts
            try:
                db.execute(_sql_text("SET LOCAL lock_timeout = '1500ms'"))
                db.execute(_sql_text("SET LOCAL statement_timeout = '2500ms'"))
            except Exception:
                pass

            # Preflight with NOWAIT to avoid waiting on locked rows
            preflight_sql = _sql_text(
                """
                SELECT 1
                FROM users
                WHERE username = :username OR email = :email
                FOR KEY SHARE NOWAIT
                LIMIT 1
                """
            )
            pre = db.execute(preflight_sql, {"username": username, "email": email}).first()
            if pre is not None:
                raise IntegrityError(
                    "duplicate username/email",
                    params={},
                    orig=Exception("unique conflict"),
                )  # type: ignore[arg-type]

            # Single insert that ignores any unique conflict; if not inserted -> conflict
            insert_sql = _sql_text(
                """
                INSERT INTO users (username, email, hashed_password, created_at, updated_at, role)
                VALUES (:username, :email, :hashed_password, NOW(), NOW(), 'user')
                ON CONFLICT DO NOTHING
                RETURNING id
                """
            )
            row = db.execute(
                insert_sql,
                {
                    "username": username,
                    "email": email,
                    "hashed_password": hashed_password,
                },
            ).fetchone()
            if row is None:
                # Deterministic 409 on any unique conflict (username or email)
                raise IntegrityError(
                    "duplicate username/email",
                    params={},
                    orig=Exception("unique conflict"),
                )  # type: ignore[arg-type]

            pk = int(row[0])
            created = db.get(User, pk)
            if created is None:
                raise SQLAlchemyError("inserted row not found after RETURNING")
            logger.info(
                "Created new user with id %s, username='%s'",
                pk,
                username,
            )
            return created

        except IntegrityError as e:
            try:
                db.rollback()
            except Exception:
                pass
            logger.warning(
                "IntegrityError on creating user (username=%s, email=%s): %s",
                username,
                email,
                e,
            )
            raise

        except OperationalError as e:
            try:
                db.rollback()
            except Exception:
                pass
            # Re-raise with explicit cause to satisfy Ruff B904
            raise IntegrityError("duplicate username/email", params={}, orig=e) from e  # type: ignore[arg-type]

        except SQLAlchemyError as e:
            logger.error("Database error while creating user '%s': %s", username, e)
            raise
        except Exception as e:
            logger.error("Unexpected error while creating user '%s': %s", username, e)
            raise


@transactional
def update_user_partial(
    db: Session,
    user_id: int,
    *,
    username: str | None = None,
    email: str | None = None,
    hashed_password: str | None = None,
) -> User | None:
    """Apply partial update (PATCH) to user.

    Returns:
        Optional[User]: Updated user or None if not found.
    """
    try:
        user = get_user_by_id(db, user_id)
        if not user:
            logger.info("Skip patch: user %s not found", user_id)
            return None

        # Use a narrow cast to Any to avoid static type confusion with Column descriptors in type checkers
        u = cast(Any, user)
        if username is not None:
            u.username = username
        if email is not None:
            u.email = email
        if hashed_password is not None:
            u.hashed_password = hashed_password

        db.flush()
        db.refresh(user)
        logger.info("Patched user %s", user_id)
        return user
    except SQLAlchemyError as e:
        logger.error("Database error while patching user %s: %s", user_id, e)
        raise
    except Exception as e:
        logger.error("Unexpected error while patching user %s: %s", user_id, e)
        raise


@transactional
def replace_user(
    db: Session,
    user_id: int,
    *,
    username: str,
    email: str,
    hashed_password: str,
) -> User | None:
    """Replace user state (PUT). Returns None if user not found."""
    try:
        user = get_user_by_id(db, user_id)
        if not user:
            logger.info("Skip replace: user %s not found", user_id)
            return None

        # Use a narrow cast to Any to avoid static type confusion with Column descriptors in type checkers
        u = cast(Any, user)
        u.username = username
        u.email = email
        u.hashed_password = hashed_password

        db.flush()
        db.refresh(user)
        logger.info("Replaced user %s", user_id)
        return user
    except SQLAlchemyError as e:
        logger.error("Database error while replacing user %s: %s", user_id, e)
        raise
    except Exception as e:
        logger.error("Unexpected error while replacing user %s: %s", user_id, e)
        raise


@transactional
def delete_user(db: Session, user_id: int) -> bool:
    """Delete user by id.

    Returns:
        bool: True if deleted, False if not found.
    """
    try:
        user = get_user_by_id(db, user_id)
        if not user:
            logger.info("Skip delete: user %s not found", user_id)
            return False
        db.delete(user)
        logger.info("Deleted user with id %s", user_id)
        return True
    except SQLAlchemyError as e:
        logger.error("Database error while deleting user %s: %s", user_id, e)
        raise
    except Exception as e:
        logger.error("Unexpected error while deleting user %s: %s", user_id, e)
        raise
