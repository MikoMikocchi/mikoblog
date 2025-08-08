from datetime import datetime

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import DatabaseError
from src.db.repositories import refresh_token_repository as rt_repo


@pytest.mark.unit
async def test_get_by_jti_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_execute(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "execute", mock_execute)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await rt_repo.get_by_jti(db_session, "test_jti")


@pytest.mark.unit
async def test_get_active_for_user_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_execute(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "execute", mock_execute)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await rt_repo.get_active_for_user(db_session, 1)


@pytest.mark.unit
async def test_create_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_flush(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "flush", mock_flush)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await rt_repo.create(db_session, user_id=1, jti="test_jti", issued_at=datetime(2023, 1, 1), expires_at=datetime(2023, 1, 2))


@pytest.mark.unit
async def test_revoke_by_jti_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_flush(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "flush", mock_flush)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await rt_repo.revoke_by_jti(db_session, "test_jti")


@pytest.mark.unit
async def test_revoke_all_for_user_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_flush(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "flush", mock_flush)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await rt_repo.revoke_all_for_user(db_session, 1)


@pytest.mark.unit
async def test_rotate_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_flush(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "flush", mock_flush)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await rt_repo.rotate(
            db_session, old_jti="old_jti", new_jti="new_jti", user_id=1, issued_at=datetime(2023, 1, 1), expires_at=datetime(2023, 1, 2)
        )


@pytest.mark.unit
async def test_is_active_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_execute(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "execute", mock_execute)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await rt_repo.is_active(db_session, "test_jti")
