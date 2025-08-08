import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import DatabaseError
from src.db.repositories import post_repository


@pytest.mark.unit
async def test_create_post_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_flush(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "flush", mock_flush)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await post_repository.create_post(db_session, "Test Title", "Test Content", 1)


@pytest.mark.unit
async def test_get_all_posts_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_execute(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "execute", mock_execute)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await post_repository.get_all_posts(db_session)


@pytest.mark.unit
async def test_count_posts_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_execute(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "execute", mock_execute)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await post_repository.count_posts(db_session)


@pytest.mark.unit
async def test_get_post_by_id_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_execute(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "execute", mock_execute)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await post_repository.get_post_by_id(db_session, 1)


@pytest.mark.unit
async def test_get_posts_paginated_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_execute(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "execute", mock_execute)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await post_repository.get_posts_paginated(db_session, 0, 10)


@pytest.mark.unit
async def test_delete_post_by_id_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_delete(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "delete", mock_delete)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await post_repository.delete_post_by_id(db_session, 1)


@pytest.mark.unit
async def test_update_post_field_database_error(db_session: AsyncSession, monkeypatch):
    # Mock SQLAlchemyError to simulate database failure
    async def mock_flush(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "flush", mock_flush)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await post_repository.update_post_field(db_session, 1, "title", "New Title")
