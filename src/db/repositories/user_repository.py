import logging

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from db.models.user import User

logger = logging.getLogger(__name__)


def get_user_by_id(db: Session, user_id: int) -> User:
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User with id {user_id} not found")
            raise
        return user

    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching user {user_id}: {e}")
        raise

    except Exception as e:
        logger.error(f"Unexpected error while fetching user {user_id}: {e}")
        raise


def get_user_by_username(db: Session, username: str) -> User | None:
    try:
        return db.query(User).filter(User.username == username).first()

    except SQLAlchemyError as e:
        logger.error(
            f"Database error while fetching user by username '{username}': {e}"
        )
        raise

    except Exception as e:
        logger.error(
            f"Unexpected error while fetching user by username '{username}': {e}"
        )
        raise


def get_user_by_email(db: Session, email: str) -> User | None:
    try:
        return db.query(User).filter(User.email == email).first()

    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching user by email '{email}': {e}")
        raise

    except Exception as e:
        logger.error(f"Unexpected error while fetching user by email '{email}': {e}")
        raise


def create_user(db: Session, username: str, email: str, hashed_password: str) -> User:
    try:
        db_user = User(username=username, email=email, hashed_password=hashed_password)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"Created new user with id {db_user.id}, username='{username}'")
        return db_user

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error while creating user '{username}': {e}")
        raise

    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error while creating user '{username}': {e}")
        raise
