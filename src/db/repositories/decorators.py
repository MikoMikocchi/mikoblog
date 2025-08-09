import asyncio
from collections.abc import Callable
import functools
import logging
from typing import Any, TypeVar, cast

from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

T = TypeVar('T')
AsyncFunc = Callable[..., Any]
AsyncFuncT = Callable[..., T]


def with_retry(max_retries: int = 3, log_prefix: str = ""):
    """Decorator for retrying function execution on OperationalError.

    Args:
        max_retries: Maximum number of attempts
        log_prefix: Prefix for log messages
    """

    def decorator(func: AsyncFuncT) -> AsyncFuncT:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = getattr(func, "__name__", str(func))

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except OperationalError as e:
                    # Extract logging information from function arguments
                    entity_info = _extract_entity_info(func_name, args, kwargs)

                    if attempt < max_retries - 1:
                        logger.warning(f"OperationalError while {log_prefix or func_name} {entity_info} " f"(attempt {attempt + 1}): {e}")
                        # Use current event loop for delay
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    else:
                        logger.error(f"Database error while {log_prefix or func_name} {entity_info}: {e}")
                        raise DatabaseError(message="Database failure") from e
                except SQLAlchemyError as e:
                    entity_info = _extract_entity_info(func_name, args, kwargs)
                    logger.error(f"Database error while {log_prefix or func_name} {entity_info}: {e}")
                    raise DatabaseError(message="Database failure") from e
                except Exception as e:
                    entity_info = _extract_entity_info(func_name, args, kwargs)
                    logger.error(f"Unexpected error while {log_prefix or func_name} {entity_info}: {e}")
                    raise

            # This code should not be reached due to exception handling above
            raise DatabaseError(message="Database failure")

        return cast(AsyncFuncT, wrapper)

    return decorator


def handle_db_errors(entity_name: str = ""):
    """Decorator for handling database errors without retries.

    Used for operations that do not require retries,
    for example, write operations.

    Args:
        entity_name: Entity name for logging
    """

    def decorator(func: AsyncFunc) -> AsyncFunc:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = getattr(func, "__name__", str(func))

            try:
                return await func(*args, **kwargs)
            except IntegrityError:
                # Do not wrap: calling functions rely on IntegrityError
                # for mapping to 409 in the service layer
                raise
            except SQLAlchemyError as e:
                entity_info = _extract_entity_info(func_name, args, kwargs)
                log_prefix = f"{entity_name} " if entity_name else ""
                logger.error(f"Database error while {log_prefix}{func_name} {entity_info}: {e}")
                raise DatabaseError(message="Database failure") from e
            except Exception as e:
                entity_info = _extract_entity_info(func_name, args, kwargs)
                log_prefix = f"{entity_name} " if entity_name else ""
                logger.error(f"Unexpected error while {log_prefix}{func_name} {entity_info}: {e}")
                raise

        return wrapper

    return decorator


def _extract_entity_info(func_name: str, args: tuple, kwargs: dict) -> str:
    """Extracts entity information from function arguments for logging.

    Tries to find an entity ID or other information in the arguments
    to create more informative log messages.
    """
    # Skip the first argument (usually db: AsyncSession)
    if len(args) > 1 and isinstance(args[1], int | str):
        return str(args[1])

    # Check for typical identifiers in kwargs
    for key in ['id', 'user_id', 'post_id', 'username', 'email']:
        if key in kwargs:
            return f"{key}={kwargs[key]}"

    # If no specific info is found, return empty string
    return ""
