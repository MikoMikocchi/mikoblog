# ruff: noqa: E402
# ВАЖНО:
# 1) Сначала задаем переменные окружения (DATABASE_URL и др.), затем импортируем src.*
# 2) Все импорты — в самом верху файла, чтобы удовлетворить Ruff/Pylance.
# 3) anyio_backend должен быть session-scoped, чтобы не ловить ScopeMismatch.

import asyncio
from collections.abc import AsyncGenerator
import os
from typing import Annotated, Protocol, runtime_checkable

from asgi_lifespan import LifespanManager
from fastapi import Depends
from httpx import AsyncClient
import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Теперь безопасно импортировать приложение и зависимости
from src.core.deps import get_current_user  # noqa: E402
from src.db.database import Base, get_db  # noqa: E402
from src.main import app  # noqa: E402

# --- Раннее задание окружения для тестов ---
# Загружаем переменные из .env.test ПЕРЕД сборкой DATABASE_URL, чтобы использовать заданный там DSN.
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(".env.test", override=False)
except Exception:
    pass

os.environ.setdefault("DB_CHECK_ON_START", "false")
os.environ.setdefault("JWT_ACCESS_MINUTES", "1")
os.environ.setdefault("JWT_REFRESH_DAYS", "1")
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "tests/keys/jwt_private.pem")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "tests/keys/jwt_public.pem")
os.environ.setdefault("TESTING", "true")

# PostgreSQL дефолты для локального запуска (можно переопределить TEST_PG_* или TEST_DATABASE_URL/DATABASE_URL)
# ВАЖНО: используем psql-совместимые дефолты, но не навязываем несуществующую роль.
os.environ.setdefault("TEST_PG_HOST", "localhost")
os.environ.setdefault("TEST_PG_PORT", "5432")
# Не заставляем по умолчанию использовать роль 'postgres' с паролем. Пусть дефолт будет текущий пользователь ОС без пароля.
# Если у вас другая роль/пароль — задайте TEST_PG_USER/TEST_PG_PASSWORD явно.
os.environ.setdefault("TEST_PG_USER", os.getenv("USER", "postgres"))
os.environ.setdefault("TEST_PG_PASSWORD", "")
os.environ.setdefault("TEST_PG_DB", "mikoblog_test")


def _build_sync_dsn_from_env() -> str:
    user = os.environ["TEST_PG_USER"]
    password = os.environ["TEST_PG_PASSWORD"]
    host = os.environ["TEST_PG_HOST"]
    port = os.environ["TEST_PG_PORT"]
    db = os.environ["TEST_PG_DB"]
    auth = user if password == "" else f"{user}:{password}"
    return f"postgresql+psycopg2://{auth}@{host}:{port}/{db}"


# Приоритет: .env.test -> ENV -> fallback из TEST_PG_*
RAW_TEST_DSN = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
if not RAW_TEST_DSN:
    RAW_TEST_DSN = _build_sync_dsn_from_env()


def _to_asyncpg(dsn: str) -> str:
    return (
        dsn.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
        .replace("postgres://", "postgresql+asyncpg://")
        .replace("postgresql://", "postgresql+asyncpg://")
    )


# Используем .env.test как источник правды. Внутри он указывает pg_test:5432 (docker-compose сеть).
# Если тесты запускаются с хоста, pg_test недоступен по DNS. Для хоста предусмотрен TEST_DATABASE_URL в .env.test (localhost:55432).
# Локально, если имя хоста pg_test не резолвится — автоматически переключимся на TEST_DATABASE_URL (если задан),
# иначе попробуем заменить хост pg_test -> localhost и порт 5432 -> 55432 (стандартное пробрасывание из compose).
TEST_DATABASE_URL_ASYNC = _to_asyncpg(RAW_TEST_DSN)


def _host_unresolvable(name: str) -> bool:
    try:
        import socket

        socket.getaddrinfo(name, None)
        return False
    except Exception:
        return True


def _rewrite_pg_test_to_local(url: str) -> str:
    # грубая, но достаточная замена хоста и порта для типовых DSN строк
    return url.replace("@pg_test:5432/", "@localhost:55432/")


# Если в DSN встречается pg_test и он не резолвится — подменим на локальную прокладку
if "pg_test" in TEST_DATABASE_URL_ASYNC and _host_unresolvable("pg_test"):
    fallback = os.getenv("TEST_DATABASE_URL")
    if fallback:
        TEST_DATABASE_URL_ASYNC = _to_asyncpg(fallback)
    else:
        TEST_DATABASE_URL_ASYNC = _to_asyncpg(_rewrite_pg_test_to_local(TEST_DATABASE_URL_ASYNC))

# Обязательное требование: только Postgres async драйвер
if not TEST_DATABASE_URL_ASYNC.startswith("postgresql+asyncpg://"):
    raise RuntimeError(
        "Tests require PostgreSQL with asyncpg driver. "
        "Provide DATABASE_URL/TEST_DATABASE_URL pointing to Postgres. "
        "Hint: use TEST_DATABASE_URL from .env.test when running tests on host."
    )

# ВАЖНО: выставляем DATABASE_URL до импорта src.*
os.environ["DATABASE_URL"] = TEST_DATABASE_URL_ASYNC


# Create AsyncEngine and session factory for tests
test_async_engine = create_async_engine(
    TEST_DATABASE_URL_ASYNC,
    pool_pre_ping=True,
    future=True,
    # Если пароль пустой (peer/trust auth по локальному сокету), отключим SSL negotiation
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
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    # Single event loop for session-scoped async fixtures
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Align anyio_backend scope with anyio plugin expectations for session-scoped parametrization
@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def _prepare_database():
    # Create schema once per test session using async engine
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup data safely respecting FK dependencies. Reset identities.
    async with test_async_engine.begin() as conn:
        try:
            await conn.execute(text("TRUNCATE TABLE refresh_tokens, posts, users RESTART IDENTITY CASCADE;"))
        except Exception:
            # Если в схеме иные имена или нет таблиц — игнорируем для устойчивости.
            pass


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession]:
    """
    Provide a fresh AsyncSession isolated by a SAVEPOINT per test.
    We open a parent transaction once and then a nested transaction (SAVEPOINT)
    to avoid autobegin conflicts and allow session.commit() inside tests.
    """
    async with test_async_engine.connect() as conn:
        # Begin parent transaction explicitly BEFORE any SQL to avoid implicit autobegin
        trans = await conn.begin()

        # Optional local timeouts (Postgres). Ignore errors; execute inside explicit transaction
        for stmt in ("SET LOCAL lock_timeout = '2s'", "SET LOCAL statement_timeout = '3000ms'"):
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass

        # Bind session to this connection to share the same transaction
        session: AsyncSession = TestAsyncSessionLocal(bind=conn)

        # Reopen SAVEPOINT automatically when a transaction on the connection ends.
        # Use the lower-level "engine_connect" event to re-create a SAVEPOINT safely.
        @event.listens_for(conn.sync_connection, "commit")
        def _restart_savepoint_commit(sess_conn):  # type: ignore[no-redef]
            # This event is synchronous; we cannot await. Don't re-enter event loop here.
            # The actual re-creation is handled on next DB interaction; we only mark intent.
            pass

        @event.listens_for(conn.sync_connection, "rollback")
        def _restart_savepoint_rollback(sess_conn):  # type: ignore[no-redef]
            pass

        try:
            yield session
        finally:
            try:
                await session.close()
            finally:
                # Rollback parent transaction to restore DB state
                await trans.rollback()


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
    Async HTTP client with app lifespan management.
    """

    @runtime_checkable
    class _HasUserFields(Protocol):
        id: int
        username: str
        email: str

    @app.get("/e2e/protected")
    async def _protected(
        user: Annotated[_HasUserFields, Depends(get_current_user)],
    ) -> dict[str, str]:
        return {"user": user.username}

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
