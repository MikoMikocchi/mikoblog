from collections.abc import Callable
import logging
from typing import ParamSpec, TypeVar

from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

T = TypeVar("T")
P = ParamSpec("P")


def transactional[**P, T](func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator for write-operations using a SQLAlchemy-like Session.
    - Commits the session when the wrapped function completes successfully (if still active).
    - Rolls back the session on any exception and re-raises it.

    Assumptions:
    - First positional argument of the wrapped function is a SQLAlchemy Session instance
      (or passed as keyword 'db').
    """

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        db: object | None = None
        if args:
            candidate0 = args[0]
            # Duck-typed session: has commit/rollback methods
            if hasattr(candidate0, "commit") and hasattr(candidate0, "rollback"):
                db = candidate0
        if db is None:
            candidate_kw = kwargs.get("db")
            if hasattr(candidate_kw, "commit") and hasattr(candidate_kw, "rollback"):
                db = candidate_kw

        try:
            result = func(*args, **kwargs)
            # Best-effort commit if the function hasn't committed yet and session is active
            is_active = True
            if db is not None and hasattr(db, "is_active"):
                try:
                    is_active = bool(db.is_active)  # type: ignore[attr-defined]
                except Exception:
                    is_active = True
            if db is not None and is_active and hasattr(db, "commit"):
                try:
                    db.commit()  # type: ignore[attr-defined]
                except SQLAlchemyError:
                    # Ignore if an inner commit already finalized the transaction boundary
                    pass
            return result
        except Exception as e:
            if db is not None and hasattr(db, "rollback"):
                try:
                    db.rollback()  # type: ignore[attr-defined]
                except Exception:
                    pass
            logger.error("Transactional error in %s: %s", getattr(func, "__name__", str(func)), e)
            raise

    return wrapper
