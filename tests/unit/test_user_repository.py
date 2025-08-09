import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError
from src.db.repositories import user_repository


@pytest.mark.unit
async def test_get_user_by_id_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_get(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "get", mock_get)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await user_repository.get_user_by_id(db_session, 1)


@pytest.mark.unit
async def test_get_user_by_username_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_execute(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "execute", mock_execute)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await user_repository.get_user_by_username(db_session, "testuser")


@pytest.mark.unit
async def test_get_user_by_email_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_execute(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "execute", mock_execute)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await user_repository.get_user_by_email(db_session, "test@example.com")


@pytest.mark.unit
async def test_count_users_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_execute(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "execute", mock_execute)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await user_repository.count_users(db_session)


@pytest.mark.unit
async def test_get_users_paginated_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_execute(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "execute", mock_execute)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await user_repository.get_users_paginated(db_session, 0, 10)


@pytest.mark.unit
async def test_create_user_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_execute(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "execute", mock_execute)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await user_repository.create_user(db_session, "testuser", "test@example.com", "hashed_password")


@pytest.mark.unit
async def test_update_user_partial_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_flush(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "flush", mock_flush)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await user_repository.update_user_partial(db_session, 1, username="newusername")


@pytest.mark.unit
async def test_replace_user_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_flush(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "flush", mock_flush)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await user_repository.replace_user(
            db_session, 1, username="newusername", email="new@example.com", hashed_password="new_hashed_password"
        )


@pytest.mark.unit
async def test_delete_user_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_delete(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "delete", mock_delete)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await user_repository.delete_user(db_session, 1)
