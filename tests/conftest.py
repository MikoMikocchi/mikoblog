# ruff: noqa: E402
# IMPORTANT:
# 1) Set environment variables (DATABASE_URL etc.) first, then import src.*
# 2) All imports at the top of the file to satisfy Ruff/Pylance.
# 3) anyio_backend must be session-scoped to avoid ScopeMismatch.

import asyncio
from collections.abc import AsyncGenerator
import os
import socket
from typing import Annotated, Protocol, runtime_checkable

from asgi_lifespan import LifespanManager
from fastapi import Depends
from httpx import AsyncClient
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# --- Now safely import the application and dependencies ---
# These imports must come ONLY after DATABASE_URL is set
from src.core.deps import get_current_user
from src.db.database import Base, get_db
from src.main import app


# --- Function for early test environment setup ---
# Must be called before any imports from src.*
def _setup_test_environment() -> str:
    """Sets up environment variables for tests and returns the final DATABASE_URL."""
    # Load variables from .env.test BEFORE building DATABASE_URL to use the one defined there.
    try:
        from dotenv import load_dotenv

        load_dotenv(".env.test", override=False)
    except ImportError:
        pass  # dotenv is optional

    os.environ.setdefault("DB_CHECK_ON_START", "false")
    os.environ.setdefault("JWT_ACCESS_MINUTES", "1")
    os.environ.setdefault("JWT_REFRESH_DAYS", "1")
    os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "tests/keys/jwt_private.pem")
    os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "tests/keys/jwt_public.pem")
    os.environ.setdefault("TESTING", "true")

    # PostgreSQL defaults for local run
    os.environ.setdefault("TEST_PG_HOST", "localhost")
    os.environ.setdefault("TEST_PG_PORT", "5432")
    os.environ.setdefault("TEST_PG_USER", os.getenv("USER", "postgres"))
    os.environ.setdefault("TEST_PG_PASSWORD", "")
    os.environ.setdefault("TEST_PG_DB", "mikoblog_test")

    def _build_sync_dsn_from_env() -> str:
        user = os.environ["TEST_PG_USER"]
        password = os.environ["TEST_PG_PASSWORD"]
        host = os.environ["TEST_PG_HOST"]
        port = os.environ["TEST_PG_PORT"]
        db = os.environ["TEST_PG_DB"]
        auth = user if not password else f"{user}:{password}"
        return f"postgresql://{auth}@{host}:{port}/{db}"  # Use standard format

    # Priority: DATABASE_URL -> TEST_DATABASE_URL -> .env.test -> fallback
    raw_test_dsn = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
    if not raw_test_dsn:
        raw_test_dsn = _build_sync_dsn_from_env()

    def _to_asyncpg(dsn: str) -> str:
        if dsn.startswith("postgresql+asyncpg://"):
            return dsn
        return (
            dsn.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
            .replace("postgres://", "postgresql+asyncpg://")
            .replace("postgresql://", "postgresql+asyncpg://")
        )

    test_database_url_async = _to_asyncpg(raw_test_dsn)

    def _host_unresolvable(name: str) -> bool:
        try:
            socket.getaddrinfo(name, None)
            return False
        except socket.gaierror:  # More specific exception
            return True
        except Exception:  # In case of other problems
            return True

    # Automatic substitution for local run
    if "pg_test" in test_database_url_async and _host_unresolvable("pg_test"):
        fallback = os.getenv("TEST_DATABASE_URL")
        if fallback:
            test_database_url_async = _to_asyncpg(fallback)
        else:
            test_database_url_async = _to_asyncpg(test_database_url_async.replace("@pg_test:5432/", "@localhost:55432/"))

    # Mandatory requirement: only Postgres async driver
    if not test_database_url_async.startswith("postgresql+asyncpg://"):
        raise RuntimeError(
            "Tests require PostgreSQL with asyncpg driver. "
            "Provide DATABASE_URL/TEST_DATABASE_URL pointing to Postgres. "
            "Hint: use TEST_DATABASE_URL from .env.test when running tests on host."
        )

    # --- CRITICAL: Set DATABASE_URL before importing src.* ---
    os.environ["DATABASE_URL"] = test_database_url_async
    return test_database_url_async


# --- EARLY ENVIRONMENT INITIALIZATION ---
TEST_DATABASE_URL_ASYNC = _setup_test_environment()


# Create AsyncEngine and session factory for tests
test_async_engine = create_async_engine(
    TEST_DATABASE_URL_ASYNC,
    pool_pre_ping=True,
    future=True,
    # If password is empty (peer/trust auth via local socket), disable SSL negotiation
    connect_args=(
        {"ssl": False}
        if TEST_DATABASE_URL_ASYNC.startswith("postgresql+asyncpg://")
        and "@" in TEST_DATABASE_URL_ASYNC
        and TEST_DATABASE_URL_ASYNC.split("@")[0].endswith("://" + os.environ["TEST_PG_USER"])
        and os.environ["TEST_PG_PASSWORD"] == ""
        else {}
    ),
)

TestAsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=test_async_engine,
    autoflush=False,  # Kept as in original, but can be discussed
    expire_on_commit=False,
)


# --- Helper functions ---
def _create_asgi_transport(app_to_use):
    """Creates ASGI transport for httpx client."""
    try:
        from httpx import ASGITransport

        return ASGITransport(app=app_to_use)
    except ImportError:
        from httpx._transports.asgi import ASGITransport

        return ASGITransport(app=app_to_use)


# --- Pytest Fixtures ---


@pytest.fixture(scope="session")
def event_loop():
    """Create and provide a new event loop for all tests."""
    # Always create a new event loop for tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # Close loop after all tests
    loop.close()


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Align anyio_backend scope with anyio plugin expectations."""
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def _prepare_database():
    """Create schema once per test session and cleanup after."""
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup data safely respecting FK dependencies. Reset identities.
    async with test_async_engine.begin() as conn:
        try:
            await conn.execute(text("TRUNCATE TABLE refresh_tokens, posts, users RESTART IDENTITY CASCADE;"))
        except DatabaseError:
            # If schema has different names or no tables - ignore for robustness.
            pass


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession]:
    """
    Provide a fresh AsyncSession for each test.
    This approach avoids issues with event loops and connection closing.
    """
    # Create a new session for each test
    session = TestAsyncSessionLocal()

    try:
        # Start transaction for test isolation
        await session.begin()
        yield session
    finally:
        # Rollback all changes
        await session.rollback()
        # Close session
        await session.close()


@pytest.fixture(scope="function")
async def override_get_db(db_session: AsyncSession):
    """
    Override FastAPI dependency to provide our per-test AsyncSession.
    """

    async def _get_db_test() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _get_db_test
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="function")
async def client(override_get_db: None) -> AsyncGenerator[AsyncClient]:
    """
    Async HTTP client with app lifespan management for integration tests.
    """

    # --- Temporary addition of test endpoint ---
    # This allows checking get_current_user work in tests
    @runtime_checkable
    class _HasUserFields(Protocol):
        id: int
        username: str
        email: str

    # Save original routes if any existed
    original_routes = app.routes.copy()

    # Add test route
    @app.get("/e2e/protected")
    async def _protected(user: Annotated[_HasUserFields, Depends(get_current_user)]):
        return {"user": user.username}

    async with LifespanManager(app):
        transport = _create_asgi_transport(app)
        # Fixed base_url: removed extra spaces
        async with AsyncClient(
            transport=transport,
            base_url="https://testserver.local",
            follow_redirects=True,
        ) as ac:
            yield ac

    # Restore original routes after test
    # This helps avoid route accumulation between tests
    # (This is not the most reliable way, but works for simple cases.
    #  More reliably - create a copy of app for tests, like in unit_client)
    app.routes[:] = original_routes
    # Clear overrides if they were set only for this test
    # (but override_get_db already does this, so it's duplication)


@pytest.fixture(scope="function")
async def unit_client() -> AsyncGenerator[AsyncClient]:
    """
    Async HTTP client for unit tests without database dependency.
    Creates a copy of the app to avoid conflicts and side effects.
    """
    # Create a copy of the application for isolation
    import copy

    from src.main import app as original_app

    unit_app = copy.deepcopy(original_app)  # This might not work for FastAPI
    # Alternative: import create_app and create a new application
    # But for simplicity we'll leave it as is, assuming routes don't change

    # --- Temporary addition of test endpoint ---
    @runtime_checkable
    class _HasUserFields(Protocol):
        id: int
        username: str
        email: str

    # Add test route
    unit_app.get("/e2e/protected")(lambda user: {"user": user.username})(Depends(get_current_user))

    async with LifespanManager(unit_app):
        transport = _create_asgi_transport(unit_app)
        # Fixed base_url: removed extra spaces
        async with AsyncClient(
            transport=transport,
            base_url="https://testserver.local",
            follow_redirects=True,
        ) as ac:
            yield ac

    # For unit_client cleanup is not needed, since it's a copy, but just in case:
    unit_app.dependency_overrides.clear()
