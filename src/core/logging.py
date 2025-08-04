import logging
from logging import Logger

from .config import settings


def setup_logging() -> None:
    """
    Configure root logging based on settings.logging.

    - Sets root level according to settings.logging.level
    - Applies a consistent format from settings.logging.format
    - Avoids reconfiguration if handlers already exist (idempotent)
    """
    level_name = (settings.logging.level or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    # If already configured, just ensure level is set and return
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return

    logging.basicConfig(
        level=level,
        format=settings.logging.format,
    )

    # Reduce noisy third-party loggers if needed (optional tuning)
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.INFO)


__all__ = ["setup_logging", "Logger"]
