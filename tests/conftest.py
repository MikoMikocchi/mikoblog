import asyncio
from collections.abc import AsyncGenerator
import os
from typing import Annotated, Protocol, runtime_checkable

from asgi_lifespan import LifespanManager
from fastapi import Depends
from httpx import AsyncClient
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.core.deps import get_current_user
from src.db import database as dbm
from src.db.database import Base, get_db
from src.main import app

# --- Environment bootstrap for tests ---
# Use .env.test values when running tests
os.environ.setdefault("DB_CHECK_ON_START", "false")
os.environ.setdefault("JWT_ACCESS_MINUTES", "1")
os.environ.setdefault("JWT_REFRESH_DAYS", "1")
# RS256 is enforced in code; ensure key paths are set for tests
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "tests/keys/jwt_private.pem")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "tests/keys/jwt_public.pem")

# Tell app that we are in tests (may relax cookie flags, etc.)
os.environ.setdefault("TESTING", "true")

# DATABASE_URL should be provided by docker-compose/.env.test when running inside compose.
# Default to in-network DSN; do NOT force localhost inside containers.
DEFAULT_TEST_DSN = "postgresql+psycopg2://postgres:postgres@pg_test:5432/mikoblog_test"
TEST_DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL") or DEFAULT_TEST_DSN
# Reflect normalized DSN for any late readers
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# Create a dedicated test engine and SessionLocal bound to it
test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    # Single event loop for session-scoped async fixtures
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def _override_db_settings():
    """
    Force the application to use the normalized test DSN and rebind its engine/session
    in case they were created during import time.
    """
    # Update settings
    if settings.database:
        settings.database.url = TEST_DATABASE_URL
    # Reinitialize app-level SQLAlchemy engine/session to the test DSN
    try:
        dbm.engine.dispose()
    except Exception:
        pass
    dbm.engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    dbm.SessionLocal.configure(bind=dbm.engine)
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    yield


@pytest.fixture(scope="session", autouse=True)
def _prepare_database():
    # Create schema once per test session
    Base.metadata.create_all(bind=test_engine)
    yield
    # Cleanup data safely respecting FK dependencies. Reset identities.
    with test_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE refresh_tokens, posts, users RESTART IDENTITY CASCADE;"))


@pytest.fixture(scope="function")
def db_session():
    """
    Provide a fresh SQLAlchemy session in a transaction for each test.
    Rolls back at the end to isolate tests.
    """
    from sqlalchemy import text as _sql_text

    connection = test_engine.connect()
    # Set fast-fail waits (Postgres only). Ignore on other DBs.
    try:
        connection.execute(_sql_text("SET lock_timeout = '2s'"))
    except Exception:
        pass
    try:
        connection.execute(_sql_text("SET statement_timeout = '3000ms'"))
    except Exception:
        pass

    session = TestSessionLocal(bind=connection)
    # Start ORM-managed transaction scope
    orm_tx = session.begin()

    try:
        yield session
    finally:
        # Close in safe order
        try:
            if orm_tx.is_active:
                orm_tx.rollback()
        except Exception:
            pass
        try:
            session.close()
        finally:
            connection.close()


@pytest.fixture(scope="function")
def override_get_db(db_session):
    """
    Override FastAPI dependency get_db to use our function-scoped session.
    """

    def _get_db_test():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db_test
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="function")
async def client(override_get_db) -> AsyncGenerator[AsyncClient]:
    """
    Async HTTP client with app lifespan management.
    """

    @runtime_checkable
    class _HasUserFields(Protocol):
        id: int
        role: str

    @app.get("/e2e/protected")
    async def _e2e_protected(
        user: Annotated[_HasUserFields, Depends(get_current_user)],
    ):
        return {
            "ok": True,
            "user_id": int(user.id),
            "role": user.role,
        }

    async with LifespanManager(app):
        # Use ASGI transport so requests go directly to the app (no real TCP/DNS).
        try:
            from httpx import ASGITransport  # type: ignore

            transport = ASGITransport(app=app)
        except Exception:
            from httpx import _transports

            transport = _transports.asgi.ASGITransport(app=app)

        # Use HTTPS scheme to allow httpx cookie jar to accept Secure cookies in tests
        async with AsyncClient(
            transport=transport,
            base_url="https://testserver.local",
            follow_redirects=True,
        ) as ac:
            yield ac
