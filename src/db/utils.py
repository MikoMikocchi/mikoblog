import logging
from typing import Callable, TypeVar
from typing_extensions import (
    ParamSpec,
)  # compatible ParamSpec for various Python versions

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

T = TypeVar("T")
P = ParamSpec("P")


def transactional(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator for write-operations using SQLAlchemy Session.
    - Commits the session when the wrapped function completes successfully (if still active).
    - Rolls back the session on SQLAlchemyError and re-raises the exception.

    Assumptions:
    - First positional argument of the wrapped function is a SQLAlchemy Session instance
      (or passed as keyword 'db').
    """

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        db: Session | None = None
        if args:
            candidate = args[0]
            if isinstance(candidate, Session):
                db = candidate
        if db is None:
            candidate = kwargs.get("db")
            if isinstance(candidate, Session):
                db = candidate  # type: ignore[assignment]

        try:
            result = func(*args, **kwargs)
            # Best-effort commit if the function hasn't committed yet and session is active
            if isinstance(db, Session) and db.is_active:
                try:
                    db.commit()
                except SQLAlchemyError:
                    # Ignore if an inner commit already finalized the transaction boundary
                    pass
            return result
        except SQLAlchemyError as e:
            if isinstance(db, Session):
                db.rollback()
            logger.error("Transactional error in %s: %s", func.__name__, e)
            raise

    return wrapper
