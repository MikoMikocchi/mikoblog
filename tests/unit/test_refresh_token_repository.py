from datetime import datetime

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError
from db.repositories import refresh_token_repository as rt_repo


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
    # Mock get_by_jti to return a mock token
    from datetime import datetime, timedelta

    from db.models.refresh_token import RefreshToken

    mock_token = RefreshToken(
        id=1, user_id=1, jti="test_jti", issued_at=datetime.utcnow(), expires_at=datetime.utcnow() + timedelta(days=1)
    )

    async def mock_get_by_jti(*args, **kwargs):
        return mock_token

    monkeypatch.setattr(rt_repo, "get_by_jti", mock_get_by_jti)

    # Mock SQLAlchemyError to simulate database failure
    async def mock_flush(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "flush", mock_flush)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await rt_repo.revoke_by_jti(db_session, "test_jti")


@pytest.mark.unit
async def test_revoke_all_for_user_database_error(db_session: AsyncSession, monkeypatch):
    # Mock db.execute to return a list of tokens
    from datetime import datetime, timedelta
    from unittest.mock import AsyncMock, MagicMock

    from db.models.refresh_token import RefreshToken

    # Create mock tokens
    mock_token1 = RefreshToken(
        id=1, user_id=1, jti="test_jti_1", issued_at=datetime.utcnow(), expires_at=datetime.utcnow() + timedelta(days=1)
    )

    mock_token2 = RefreshToken(
        id=2, user_id=1, jti="test_jti_2", issued_at=datetime.utcnow(), expires_at=datetime.utcnow() + timedelta(days=1)
    )

    # Create mock result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_token1, mock_token2]

    # Create mock execute
    mock_execute = AsyncMock(return_value=mock_result)
    monkeypatch.setattr(db_session, "execute", mock_execute)

    # Mock SQLAlchemyError to simulate database failure
    async def mock_flush(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(db_session, "flush", mock_flush)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await rt_repo.revoke_all_for_user(db_session, 1)


@pytest.mark.unit
async def test_rotate_database_error(db_session: AsyncSession, monkeypatch):
    # Mock get_by_jti to return a mock token
    from datetime import datetime, timedelta

    from db.models.refresh_token import RefreshToken

    mock_token = RefreshToken(id=1, user_id=1, jti="old_jti", issued_at=datetime.utcnow(), expires_at=datetime.utcnow() + timedelta(days=1))

    async def mock_get_by_jti(*args, **kwargs):
        return mock_token

    monkeypatch.setattr(rt_repo, "get_by_jti", mock_get_by_jti)

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
    # Mock get_by_jti to raise SQLAlchemyError
    async def mock_get_by_jti(*args, **kwargs):
        raise SQLAlchemyError("Database connection failed")

    monkeypatch.setattr(rt_repo, "get_by_jti", mock_get_by_jti)

    # Should raise DatabaseError when SQLAlchemyError occurs
    with pytest.raises(DatabaseError):
        await rt_repo.is_active(db_session, "test_jti")
