import logging

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from db.models.user import User
from db.utils import transactional

logger = logging.getLogger(__name__)


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """
    Fetch a user by id.

    Returns:
        User | None: User instance if found, else None.
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


def get_user_by_email(db: Session, email: str) -> User | None:
    try:
        return db.query(User).filter(User.email == email).first()
    except SQLAlchemyError as e:
        logger.error("Database error while fetching user by email '%s': %s", email, e)
        raise
    except Exception as e:
        logger.error("Unexpected error while fetching user by email '%s': %s", email, e)
        raise


@transactional
def create_user(db: Session, username: str, email: str, hashed_password: str) -> User:
    """
    Create a new user.

    Transaction boundaries are handled by @transactional:
    - commit on success (if session active)
    - rollback on SQLAlchemyError
    """
    try:
        db_user = User(username=username, email=email, hashed_password=hashed_password)
        db.add(db_user)
        # commit via decorator; ensure persistence boundaries with flush/refresh
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
