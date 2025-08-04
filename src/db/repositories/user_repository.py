import logging
from typing import Iterable, Optional

from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db.models.user import User
from db.utils import transactional

logger = logging.getLogger(__name__)


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
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


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Return a user by exact username."""
    try:
        return db.query(User).filter(User.username == username).first()
    except SQLAlchemyError as e:
        logger.error(
            "Database error while fetching user by username '%s': %s", username, e
        )
        raise
    except Exception as e:
        logger.error(
            "Unexpected error while fetching user by username '%s': %s", username, e
        )
        raise


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Return a user by exact email."""
    try:
        return db.query(User).filter(User.email == email).first()
    except SQLAlchemyError as e:
        logger.error("Database error while fetching user by email '%s': %s", email, e)
        raise
    except Exception as e:
        logger.error("Unexpected error while fetching user by email '%s': %s", email, e)
        raise


def count_users(
    db: Session, username: Optional[str] = None, email: Optional[str] = None
) -> int:
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
    username: Optional[str] = None,
    email: Optional[str] = None,
) -> Iterable[User]:
    """Return users page with optional exact filters, ordered by id ASC.

    Args:
        db: Session.
        offset: Offset >= 0.
        limit: Limit > 0.
        username: Exact username filter.
        email: Exact email filter.

    Returns:
        Iterable[User]: Users slice.
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
    """Create a new user under transactional boundary."""
    try:
        db_user = User(username=username, email=email, hashed_password=hashed_password)
        db.add(db_user)
        db.flush()
        db.refresh(db_user)
        logger.info("Created new user with id %s, username='%s'", db_user.id, username)
        return db_user
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
    username: Optional[str] = None,
    email: Optional[str] = None,
    hashed_password: Optional[str] = None,
) -> Optional[User]:
    """Apply partial update (PATCH) to user.

    Returns:
        Optional[User]: Updated user or None if not found.
    """
    try:
        user = get_user_by_id(db, user_id)
        if not user:
            logger.info("Skip patch: user %s not found", user_id)
            return None

        # Use SQLAlchemy's setattr to avoid static type confusion with Column descriptors
        if username is not None:
            setattr(user, "username", username)
        if email is not None:
            setattr(user, "email", email)
        if hashed_password is not None:
            setattr(user, "hashed_password", hashed_password)

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
) -> Optional[User]:
    """Replace user state (PUT). Returns None if user not found."""
    try:
        user = get_user_by_id(db, user_id)
        if not user:
            logger.info("Skip replace: user %s not found", user_id)
            return None

        setattr(user, "username", username)
        setattr(user, "email", email)
        setattr(user, "hashed_password", hashed_password)

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
