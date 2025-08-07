from logging.config import fileConfig
import os
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import application's metadata and settings (after sys.path setup)
from core.config import settings  # noqa: E402
from db.database import Base  # noqa: E402
import db.models  # noqa: E402,F401  ensure models are imported so tables are registered

# Configure sys.path early so 'core' and 'db' are importable
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Configure Alembic and logging
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Use application's metadata for autogenerate
target_metadata = Base.metadata


def _get_database_url() -> str:
    return settings.database.url  # type: ignore[attr-defined]


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    ini_section = config.get_section(config.config_ini_section, {}) or {}
    ini_section["sqlalchemy.url"] = _get_database_url()

    connectable = engine_from_config(
        ini_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
