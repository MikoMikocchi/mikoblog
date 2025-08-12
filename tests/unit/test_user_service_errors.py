import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError, NotFoundError, ValidationError
from schemas.users import UserCreate, UserReplace, UserUpdate
from services import user_service


@pytest.mark.unit
async def test_get_user_by_id_not_found(db_session: AsyncSession, monkeypatch):
    # Mock get_user_by_id to return None
    async def mock_get_user_by_id(*args, **kwargs):
        return None

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_id", mock_get_user_by_id)

    with pytest.raises(NotFoundError):
        await user_service.get_user_by_id(db_session, 1)


@pytest.mark.unit
async def test_list_users_validation_error_invalid_page(db_session: AsyncSession):
    with pytest.raises(ValidationError):
        await user_service.list_users(db_session, page=0, limit=10)


@pytest.mark.unit
async def test_list_users_validation_error_invalid_limit(db_session: AsyncSession):
    with pytest.raises(ValidationError):
        await user_service.list_users(db_session, page=1, limit=0)


@pytest.mark.unit
async def test_create_user_conflict_error_username_exists(db_session: AsyncSession, monkeypatch):
    # Mock get_user_by_username to return a user
    async def mock_get_user_by_username(*args, **kwargs):
        return object()  # any non-None object

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_username", mock_get_user_by_username)

    payload = UserCreate(username="testuser", email="test@example.com", password="Str0ng!Passw0rd")

    with pytest.raises(ConflictError):
        await user_service.create_user(db_session, payload)


@pytest.mark.unit
async def test_create_user_conflict_error_email_exists(db_session: AsyncSession, monkeypatch):
    # Mock get_user_by_username to return None
    async def mock_get_user_by_username(*args, **kwargs):
        return None

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_username", mock_get_user_by_username)

    # Mock get_user_by_email to return a user
    async def mock_get_user_by_email(*args, **kwargs):
        return object()  # any non-None object

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_email", mock_get_user_by_email)

    payload = UserCreate(username="testuser", email="test@example.com", password="Str0ng!Passw0rd")

    with pytest.raises(ConflictError):
        await user_service.create_user(db_session, payload)


@pytest.mark.unit
async def test_create_user_database_error_on_create(db_session: AsyncSession, monkeypatch):
    # Mock get_user_by_username and get_user_by_email to return None
    async def mock_get_user_by_username(*args, **kwargs):
        return None

    async def mock_get_user_by_email(*args, **kwargs):
        return None

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_username", mock_get_user_by_username)
    monkeypatch.setattr("db.repositories.user_repository.get_user_by_email", mock_get_user_by_email)

    # Mock create_user to raise IntegrityError
    async def mock_create_user(*args, **kwargs):
        raise IntegrityError("statement", "params", Exception("orig"))

    monkeypatch.setattr("db.repositories.user_repository.create_user", mock_create_user)

    payload = UserCreate(username="testuser", email="test@example.com", password="Str0ng!Passw0rd")

    with pytest.raises(ConflictError):
        await user_service.create_user(db_session, payload)


@pytest.mark.unit
async def test_create_user_unexpected_database_error(db_session: AsyncSession, monkeypatch):
    # Mock get_user_by_username and get_user_by_email to return None
    async def mock_get_user_by_username(*args, **kwargs):
        return None

    async def mock_get_user_by_email(*args, **kwargs):
        return None

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_username", mock_get_user_by_username)
    monkeypatch.setattr("db.repositories.user_repository.get_user_by_email", mock_get_user_by_email)

    # Mock create_user to raise unexpected SQLAlchemyError
    async def mock_create_user(*args, **kwargs):
        raise SQLAlchemyError("Unexpected database error")

    monkeypatch.setattr("db.repositories.user_repository.create_user", mock_create_user)

    payload = UserCreate(username="testuser", email="test@example.com", password="Str0ng!Passw0rd")

    with pytest.raises(ValidationError):
        await user_service.create_user(db_session, payload)


@pytest.mark.unit
async def test_update_user_patch_user_not_found(db_session: AsyncSession, monkeypatch):
    # Mock get_user_by_id to return None
    async def mock_get_user_by_id(*args, **kwargs):
        return None

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_id", mock_get_user_by_id)

    patch = UserUpdate(username="newusername", email="new@example.com", password="NewStr0ng!Passw0rd")

    with pytest.raises(NotFoundError):
        await user_service.update_user_patch(db_session, 1, patch)


@pytest.mark.unit
async def test_update_user_patch_conflict_error_username_exists(db_session: AsyncSession, monkeypatch):
    # Mock user object
    class MockUser:
        id = 1

    # Mock get_user_by_id to return a user
    async def mock_get_user_by_id(*args, **kwargs):
        return MockUser()

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_id", mock_get_user_by_id)

    # Mock get_user_by_username to return a different user
    async def mock_get_user_by_username(*args, **kwargs):
        class OtherUser:
            id = 2

        return OtherUser()

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_username", mock_get_user_by_username)

    patch = UserUpdate(username="existinguser", email="new@example.com", password="NewStr0ng!Passw0rd")

    with pytest.raises(ConflictError):
        await user_service.update_user_patch(db_session, 1, patch)


@pytest.mark.unit
async def test_update_user_patch_conflict_error_email_exists(db_session: AsyncSession, monkeypatch):
    # Mock user object
    class MockUser:
        id = 1

    # Mock get_user_by_id to return a user
    async def mock_get_user_by_id(*args, **kwargs):
        return MockUser()

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_id", mock_get_user_by_id)

    # Mock get_user_by_username to return None
    async def mock_get_user_by_username(*args, **kwargs):
        return None

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_username", mock_get_user_by_username)

    # Mock get_user_by_email to return a different user
    async def mock_get_user_by_email(*args, **kwargs):
        class OtherUser:
            id = 2

        return OtherUser()

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_email", mock_get_user_by_email)

    patch = UserUpdate(username="newusername", email="existing@example.com", password="NewStr0ng!Passw0rd")

    with pytest.raises(ConflictError):
        await user_service.update_user_patch(db_session, 1, patch)


@pytest.mark.unit
async def test_update_user_patch_user_not_found_after_update(db_session: AsyncSession, monkeypatch):
    # Mock user object
    class MockUser:
        id = 1

    # Mock get_user_by_id to return a user
    async def mock_get_user_by_id(*args, **kwargs):
        return MockUser()

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_id", mock_get_user_by_id)

    # Mock get_user_by_username and get_user_by_email to return None
    async def mock_get_user_by_username(*args, **kwargs):
        return None

    async def mock_get_user_by_email(*args, **kwargs):
        return None

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_username", mock_get_user_by_username)
    monkeypatch.setattr("db.repositories.user_repository.get_user_by_email", mock_get_user_by_email)

    # Mock update_user_partial to return None
    async def mock_update_user_partial(*args, **kwargs):
        return None

    monkeypatch.setattr("db.repositories.user_repository.update_user_partial", mock_update_user_partial)

    patch = UserUpdate(username="newusername", email="new@example.com", password="NewStr0ng!Passw0rd")

    with pytest.raises(NotFoundError):
        await user_service.update_user_patch(db_session, 1, patch)


@pytest.mark.unit
async def test_replace_user_put_user_not_found(db_session: AsyncSession, monkeypatch):
    # Mock get_user_by_id to return None
    async def mock_get_user_by_id(*args, **kwargs):
        return None

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_id", mock_get_user_by_id)

    payload = UserReplace(username="newusername", email="new@example.com", password="NewStr0ng!Passw0rd")

    with pytest.raises(NotFoundError):
        await user_service.replace_user_put(db_session, 1, payload)


@pytest.mark.unit
async def test_replace_user_put_conflict_error_username_exists(db_session: AsyncSession, monkeypatch):
    # Mock user object
    class MockUser:
        id = 1

    # Mock get_user_by_id to return a user
    async def mock_get_user_by_id(*args, **kwargs):
        return MockUser()

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_id", mock_get_user_by_id)

    # Mock get_user_by_username to return a different user
    async def mock_get_user_by_username(*args, **kwargs):
        class OtherUser:
            id = 2

        return OtherUser()

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_username", mock_get_user_by_username)

    payload = UserReplace(username="existinguser", email="new@example.com", password="NewStr0ng!Passw0rd")

    with pytest.raises(ConflictError):
        await user_service.replace_user_put(db_session, 1, payload)


@pytest.mark.unit
async def test_replace_user_put_conflict_error_email_exists(db_session: AsyncSession, monkeypatch):
    # Mock user object
    class MockUser:
        id = 1

    # Mock get_user_by_id to return a user
    async def mock_get_user_by_id(*args, **kwargs):
        return MockUser()

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_id", mock_get_user_by_id)

    # Mock get_user_by_username to return None
    async def mock_get_user_by_username(*args, **kwargs):
        return None

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_username", mock_get_user_by_username)

    # Mock get_user_by_email to return a different user
    async def mock_get_user_by_email(*args, **kwargs):
        class OtherUser:
            id = 2

        return OtherUser()

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_email", mock_get_user_by_email)

    payload = UserReplace(username="newusername", email="existing@example.com", password="NewStr0ng!Passw0rd")

    with pytest.raises(ConflictError):
        await user_service.replace_user_put(db_session, 1, payload)


@pytest.mark.unit
async def test_replace_user_put_user_not_found_after_replace(db_session: AsyncSession, monkeypatch):
    # Mock user object
    class MockUser:
        id = 1

    # Mock get_user_by_id to return a user
    async def mock_get_user_by_id(*args, **kwargs):
        return MockUser()

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_id", mock_get_user_by_id)

    # Mock get_user_by_username and get_user_by_email to return None
    async def mock_get_user_by_username(*args, **kwargs):
        return None

    async def mock_get_user_by_email(*args, **kwargs):
        return None

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_username", mock_get_user_by_username)
    monkeypatch.setattr("db.repositories.user_repository.get_user_by_email", mock_get_user_by_email)

    # Mock replace_user to return None
    async def mock_replace_user(*args, **kwargs):
        return None

    monkeypatch.setattr("db.repositories.user_repository.replace_user", mock_replace_user)

    payload = UserReplace(username="newusername", email="new@example.com", password="NewStr0ng!Passw0rd")

    with pytest.raises(NotFoundError):
        await user_service.replace_user_put(db_session, 1, payload)


@pytest.mark.unit
async def test_delete_user_user_not_found(db_session: AsyncSession, monkeypatch):
    # Mock get_user_by_id to return None
    async def mock_get_user_by_id(*args, **kwargs):
        return None

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_id", mock_get_user_by_id)

    with pytest.raises(NotFoundError):
        await user_service.delete_user(db_session, 1)


@pytest.mark.unit
async def test_delete_user_user_not_found_after_delete(db_session: AsyncSession, monkeypatch):
    # Mock user object
    class MockUser:
        id = 1

    # Mock get_user_by_id to return a user
    async def mock_get_user_by_id(*args, **kwargs):
        return MockUser()

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_id", mock_get_user_by_id)

    # Mock delete_user to return False
    async def mock_delete_user(*args, **kwargs):
        return False

    monkeypatch.setattr("db.repositories.user_repository.delete_user", mock_delete_user)

    with pytest.raises(NotFoundError):
        await user_service.delete_user(db_session, 1)
