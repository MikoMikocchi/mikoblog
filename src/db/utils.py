from collections.abc import Callable
import logging
from typing import ParamSpec, TypeVar

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar("T")
P = ParamSpec("P")


def transactional[**P, T](func: Callable[P, T]) -> Callable[P, T]:
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
            candidate0 = args[0]
            if isinstance(candidate0, Session):
                db = candidate0
        if db is None:
            candidate_kw = kwargs.get("db")
            if isinstance(candidate_kw, Session):
                db = candidate_kw

        try:
            result = func(*args, **kwargs)
            # Best-effort commit if the function hasn't committed yet and session is active
            if db is not None and db.is_active:
                try:
                    db.commit()
                except SQLAlchemyError:
                    # Ignore if an inner commit already finalized the transaction boundary
                    pass
            return result
        except SQLAlchemyError as e:
            if db is not None:
                db.rollback()
            logger.error("Transactional error in %s: %s", getattr(func, "__name__", str(func)), e)
            raise

    return wrapper
