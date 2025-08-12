# ruff: noqa: E402
# IMPORTANT:
# 1) Set environment variables (DATABASE_URL etc.) first, then import src.*
# 2) All imports at the top of the file to satisfy Ruff/Pylance.
# 3) anyio_backend must be session-scoped to avoid ScopeMismatch.

from collections.abc import AsyncGenerator
import os
import socket

from asgi_lifespan import LifespanManager
from httpx import AsyncClient
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# src.* imports MUST be executed ONLY after DATABASE_URL is set
# NOTE: src.* imports are intentionally moved below after env init


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
    # Use a stable default superuser for local Postgres
    os.environ.setdefault("TEST_PG_USER", "postgres")
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


# --- Now safely import the application and dependencies ---
# These imports must come ONLY after DATABASE_URL is set
# isort: off
from app import create_app
from db.database import Base, get_db

# isort: on

# --- PyJWT compatibility shim for tests ---
# Allow jwt.encode(payload, key=None, algorithm=None) used in negative tests.
# PyJWT>=2 expects a str/bytes key even for NoneAlgorithm; make it accept None.
try:  # noqa: SIM105
    import jwt  # type: ignore
    from jwt.algorithms import NoneAlgorithm  # type: ignore
    import jwt.api_jws as _api_jws  # type: ignore
    from jwt.api_jws import PyJWS  # type: ignore
    from jwt.api_jwt import api_jws  # type: ignore

    _orig_prepare_key = NoneAlgorithm.prepare_key  # type: ignore[attr-defined]

    def _prepare_key_allow_none(self, key):  # type: ignore[override]
        if key is None:
            return b""
        return _orig_prepare_key(self, key)

    NoneAlgorithm.prepare_key = _prepare_key_allow_none  # type: ignore[assignment]
    # Also set default algorithm to 'none' so calls with algorithm=None don't fallback to HS256.
    try:
        PyJWS.algorithm = "none"  # type: ignore[attr-defined]
        # Ensure the pre-created singleton also uses 'none' if already instantiated.
        try:
            api_jws.algorithm = "none"  # type: ignore[attr-defined]
        except Exception:
            pass
        # Some PyJWT versions use a module-level DEFAULT_ALGORITHM when None is passed.
        try:
            _api_jws.DEFAULT_ALGORITHM = "none"  # type: ignore[attr-defined]
        except Exception:

            pass
        # Final fallback: override jwt.encode to support algorithm=None with no signature.
        import base64 as _base64  # type: ignore
        import json as _json  # type: ignore

        _orig_encode = jwt.encode  # type: ignore[attr-defined]

        def _b64url(data: bytes) -> str:
            return _base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

        def _encode_compat(payload, key=None, algorithm=None, headers=None, json_encoder=None):  # type: ignore[override]
            if algorithm is None and key is None:
                hdr = {"alg": "none", "typ": "JWT"}
                if headers:
                    hdr.update(headers)
                header_b64 = _b64url(_json.dumps(hdr, separators=(",", ":")).encode("utf-8"))
                payload_b64 = _b64url(
                    _json.dumps(payload, cls=json_encoder, separators=(",", ":")).encode("utf-8")
                    if json_encoder
                    else _json.dumps(payload, separators=(",", ":")).encode("utf-8")
                )
                return f"{header_b64}.{payload_b64}."
            return _orig_encode(payload, key=key, algorithm=algorithm, headers=headers, json_encoder=json_encoder)

        jwt.encode = _encode_compat  # type: ignore[assignment]
    except Exception:
        pass
except Exception:
    # If PyJWT is unavailable or API changed, don't block tests.
    pass


# Create AsyncEngine and session factory for tests
test_async_engine = create_async_engine(
    TEST_DATABASE_URL_ASYNC,
    future=True,
    pool_pre_ping=False,
    poolclass=NullPool,  # avoid reusing connections across different event loops
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
    autoflush=True,  # Enable autoflush so pending INSERTs become visible before SELECTs
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
def app():
    """FastAPI application instance for tests, created by factory.

    Additionally registers a test protected endpoint /e2e/protected
    only for e2e tests (does not appear in prod code and OpenAPI schema).
    """
    _app = create_app()

    # Local imports to avoid breaking env initialization order in this file
    from typing import Annotated

    from fastapi import Depends

    from core.deps import get_current_user
    from db.models.user import User

    @_app.get("/e2e/protected", include_in_schema=False)
    async def _e2e_protected(current_user: Annotated[User, Depends(get_current_user)]):
        return {"ok": True, "user_id": int(current_user.id)}

    return _app


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Align anyio_backend scope with anyio plugin expectations."""
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def _prepare_database():
    """Create schema once per test session and cleanup after."""
    # Import models to register tables with Base before create_all
    # These imports are intentionally local to avoid side effects during module import
    from db.models import post as _post_model, refresh_token as _rt_model, user as _user_model  # noqa: F401

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
    # Create a dedicated engine tied to the current test's event loop
    engine = create_async_engine(
        TEST_DATABASE_URL_ASYNC,
        future=True,
        pool_pre_ping=False,
        poolclass=NullPool,
        connect_args=(
            {"ssl": False}
            if TEST_DATABASE_URL_ASYNC.startswith("postgresql+asyncpg://")
            and "@" in TEST_DATABASE_URL_ASYNC
            and TEST_DATABASE_URL_ASYNC.split("@")[0].endswith("://" + os.environ["TEST_PG_USER"])
            and os.environ["TEST_PG_PASSWORD"] == ""
            else {}
        ),
    )

    SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=engine,
        autoflush=True,
        expire_on_commit=False,
    )

    session = SessionLocal()

    try:
        # Start transaction for test isolation
        await session.begin()
        yield session
    finally:
        # Cleanup: try to close session; suppress any rollback-on-close errors
        try:
            try:
                await session.close()
            except Exception:
                # Suppress teardown-time loop/rollback errors; we'll hard-clean below
                pass
        finally:
            # Per-test hard cleanup to ensure isolation without relying on session transaction state
            async with engine.begin() as conn:
                await conn.execute(text("TRUNCATE TABLE refresh_tokens, posts, users RESTART IDENTITY CASCADE;"))
            # Dispose the per-test engine to ensure no connections leak across loops
            await engine.dispose()


@pytest.fixture(scope="function")
async def override_get_db(app):
    """
    Override FastAPI dependency to provide a fresh AsyncSession per request.
    Using TestAsyncSessionLocal ensures each request gets its own session that
    is properly closed by the context manager, preventing unchecked-in connections.
    """

    async def _get_db_test() -> AsyncGenerator[AsyncSession]:
        async with TestAsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db_test
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="function")
async def client(app, override_get_db: None) -> AsyncGenerator[AsyncClient]:
    """
    Async HTTP client with app lifespan management for integration tests.
    """

    async with LifespanManager(app):
        transport = _create_asgi_transport(app)
        # Fixed base_url: removed extra spaces
        async with AsyncClient(
            transport=transport,
            base_url="https://testserver.local",
            follow_redirects=True,
        ) as ac:
            yield ac


@pytest.fixture(scope="function")
async def unit_client(app, override_get_db: None) -> AsyncGenerator[AsyncClient]:
    """
    Lightweight HTTP client for unit tests without lifespan management.
    Uses the same ASGI transport and DB override as integration client.
    """
    # Local import to avoid breaking environment initialization order
    from fastapi import Depends

    from core import deps as deps_module
    from core.deps import _resolve_current_user, get_current_user

    # Dummy user for unit tests of controllers (bypass authentication)
    async def _dummy_user():  # type: ignore[unused-argument]
        class _U:
            id = 0
            role = "admin"

        return _U()

    app.dependency_overrides[get_current_user] = _dummy_user
    app.dependency_overrides[_resolve_current_user] = _dummy_user

    # Proxy override for original require_admin to allow test monkeypatching of deps_module.require_admin
    orig_require_admin = deps_module.require_admin

    from typing import Annotated

    from db.models.user import User

    async def _proxy_require_admin(
        _auth: Annotated[User, Depends(_resolve_current_user)],  # type: ignore[name-defined]
    ):
        return deps_module.require_admin(_auth)

    app.dependency_overrides[orig_require_admin] = _proxy_require_admin
    try:
        transport = _create_asgi_transport(app)
        async with AsyncClient(
            transport=transport,
            base_url="https://testserver.local",
            follow_redirects=True,
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(_resolve_current_user, None)
        app.dependency_overrides.pop(orig_require_admin, None)
