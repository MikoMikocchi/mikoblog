import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AuthenticationError, ConflictError, NotFoundError, ValidationError
from src.schemas.auth import AuthLogin, AuthRegister
from src.services import auth_service


@pytest.mark.unit
async def test_register_validation_error_email_whitespace(db_session: AsyncSession):
    payload = AuthRegister(
        username="testuser",
        email=" test@example.com ",
        password="Str0ng!Passw0rd",  # whitespace should cause ValidationError
    )

    with pytest.raises(ValidationError):
        await auth_service.register(db_session, payload)


@pytest.mark.unit
async def test_register_validation_error_reserved_username(db_session: AsyncSession):
    payload = AuthRegister(
        username="admin",
        email="test@example.com",
        password="Str0ng!Passw0rd",  # reserved username should cause ValidationError
    )

    with pytest.raises(ValidationError):
        await auth_service.register(db_session, payload)


@pytest.mark.unit
async def test_register_validation_error_invalid_username_format(db_session: AsyncSession):
    payload = AuthRegister(username="user name", email="test@example.com", password="Str0ng!Passw0rd")  # space should cause ValidationError

    with pytest.raises(ValidationError):
        await auth_service.register(db_session, payload)


@pytest.mark.unit
async def test_register_validation_error_weak_password(db_session: AsyncSession):
    payload = AuthRegister(username="testuser", email="test@example.com", password="weak")  # weak password should cause ValidationError

    with pytest.raises(ValidationError):
        await auth_service.register(db_session, payload)


@pytest.mark.unit
async def test_register_conflict_error_username_exists(db_session: AsyncSession, monkeypatch):
    # Mock get_user_by_username to return a user
    async def mock_get_user_by_username(*args, **kwargs):
        return object()  # any non-None object

    monkeypatch.setattr("src.db.repositories.user_repository.get_user_by_username", mock_get_user_by_username)

    payload = AuthRegister(username="testuser", email="test@example.com", password="Str0ng!Passw0rd")

    with pytest.raises(ConflictError):
        await auth_service.register(db_session, payload)


@pytest.mark.unit
async def test_register_conflict_error_email_exists(db_session: AsyncSession, monkeypatch):
    # Mock get_user_by_email to return a user
    async def mock_get_user_by_email(*args, **kwargs):
        return object()  # any non-None object

    monkeypatch.setattr("src.db.repositories.user_repository.get_user_by_email", mock_get_user_by_email)

    payload = AuthRegister(username="testuser", email="test@example.com", password="Str0ng!Passw0rd")

    with pytest.raises(ConflictError):
        await auth_service.register(db_session, payload)


@pytest.mark.unit
async def test_register_database_error_on_create(db_session: AsyncSession, monkeypatch):
    # Mock get_user_by_username and get_user_by_email to return None
    async def mock_get_user_by_username(*args, **kwargs):
        return None

    async def mock_get_user_by_email(*args, **kwargs):
        return None

    monkeypatch.setattr("src.db.repositories.user_repository.get_user_by_username", mock_get_user_by_username)
    monkeypatch.setattr("src.db.repositories.user_repository.get_user_by_email", mock_get_user_by_email)

    # Mock create_user to raise IntegrityError
    async def mock_create_user(*args, **kwargs):
        raise IntegrityError("statement", "params", Exception("orig"))

    monkeypatch.setattr("src.db.repositories.user_repository.create_user", mock_create_user)

    payload = AuthRegister(username="testuser", email="test@example.com", password="Str0ng!Passw0rd")

    with pytest.raises(ConflictError):
        await auth_service.register(db_session, payload)


@pytest.mark.unit
async def test_register_unexpected_database_error(db_session: AsyncSession, monkeypatch):
    # Mock get_user_by_username and get_user_by_email to return None
    async def mock_get_user_by_username(*args, **kwargs):
        return None

    async def mock_get_user_by_email(*args, **kwargs):
        return None

    monkeypatch.setattr("src.db.repositories.user_repository.get_user_by_username", mock_get_user_by_username)
    monkeypatch.setattr("src.db.repositories.user_repository.get_user_by_email", mock_get_user_by_email)

    # Mock create_user to raise unexpected SQLAlchemyError
    async def mock_create_user(*args, **kwargs):
        raise SQLAlchemyError("Unexpected database error")

    monkeypatch.setattr("src.db.repositories.user_repository.create_user", mock_create_user)

    payload = AuthRegister(username="testuser", email="test@example.com", password="Str0ng!Passw0rd")

    with pytest.raises(ValidationError):
        await auth_service.register(db_session, payload)


@pytest.mark.unit
async def test_login_user_not_found(db_session: AsyncSession, monkeypatch):
    # Mock _resolve_user_by_login to return None
    async def mock_resolve_user_by_login(*args, **kwargs):
        return None

    monkeypatch.setattr(auth_service, "_resolve_user_by_login", mock_resolve_user_by_login)

    payload = AuthLogin(username_or_email="testuser", password="Str0ng!Passw0rd")

    with pytest.raises(AuthenticationError):
        await auth_service.login(db_session, payload, user_agent=None, ip=None)


@pytest.mark.unit
async def test_login_invalid_password(db_session: AsyncSession, monkeypatch):
    # Mock user object
    class MockUser:
        id = 1
        hashed_password = "hashed_password"

    # Mock _resolve_user_by_login to return a user
    async def mock_resolve_user_by_login(*args, **kwargs):
        return MockUser()

    monkeypatch.setattr(auth_service, "_resolve_user_by_login", mock_resolve_user_by_login)

    # Mock verify_password to return False
    def mock_verify_password(*args, **kwargs):
        return False

    monkeypatch.setattr("src.core.security.verify_password", mock_verify_password)

    payload = AuthLogin(username_or_email="testuser", password="Str0ng!Passw0rd")

    with pytest.raises(AuthenticationError):
        await auth_service.login(db_session, payload, user_agent=None, ip=None)


@pytest.mark.unit
async def test_login_invalid_user_object(db_session: AsyncSession, monkeypatch):
    # Mock user object without id attribute
    class MockUser:
        pass

    # Mock _resolve_user_by_login to return a user
    async def mock_resolve_user_by_login(*args, **kwargs):
        return MockUser()

    monkeypatch.setattr(auth_service, "_resolve_user_by_login", mock_resolve_user_by_login)

    payload = AuthLogin(username_or_email="testuser", password="Str0ng!Passw0rd")

    with pytest.raises(AuthenticationError):
        await auth_service.login(db_session, payload, user_agent=None, ip=None)


@pytest.mark.unit
async def test_refresh_invalid_token(db_session: AsyncSession):
    refresh_jwt = "invalid_token"

    with pytest.raises(AuthenticationError):
        await auth_service.refresh(db_session, refresh_jwt, user_agent=None, ip=None)


@pytest.mark.unit
async def test_refresh_invalid_sub_claim(db_session: AsyncSession, monkeypatch):
    # Mock decode_token to return a token with invalid sub
    def mock_decode_token(*args, **kwargs):
        return {"sub": "invalid", "jti": "test_jti", "typ": "refresh"}

    monkeypatch.setattr("src.core.jwt.decode_token", mock_decode_token)

    refresh_jwt = "valid_token"

    with pytest.raises(AuthenticationError):
        await auth_service.refresh(db_session, refresh_jwt, user_agent=None, ip=None)


@pytest.mark.unit
async def test_refresh_inactive_token(db_session: AsyncSession, monkeypatch):
    # Mock decode_token to return a valid token
    def mock_decode_token(*args, **kwargs):
        return {"sub": "1", "jti": "test_jti", "typ": "refresh"}

    monkeypatch.setattr("src.core.jwt.decode_token", mock_decode_token)

    # Mock validate_typ to do nothing
    def mock_validate_typ(*args, **kwargs):
        pass

    monkeypatch.setattr("src.core.jwt.validate_typ", mock_validate_typ)

    # Mock is_active to return False
    async def mock_is_active(*args, **kwargs):
        return False

    monkeypatch.setattr("src.db.repositories.refresh_token_repository.is_active", mock_is_active)

    refresh_jwt = "valid_token"

    with pytest.raises(AuthenticationError):
        await auth_service.refresh(db_session, refresh_jwt, user_agent=None, ip=None)


@pytest.mark.unit
async def test_refresh_token_not_found(db_session: AsyncSession, monkeypatch):
    # Mock decode_token to return a valid token
    def mock_decode_token(*args, **kwargs):
        return {"sub": "1", "jti": "test_jti", "typ": "refresh"}

    monkeypatch.setattr("src.core.jwt.decode_token", mock_decode_token)

    # Mock validate_typ to do nothing
    def mock_validate_typ(*args, **kwargs):
        pass

    monkeypatch.setattr("src.core.jwt.validate_typ", mock_validate_typ)

    # Mock is_active to return True
    async def mock_is_active(*args, **kwargs):
        return True

    monkeypatch.setattr("src.db.repositories.refresh_token_repository.is_active", mock_is_active)

    # Mock rotate to return None
    async def mock_rotate(*args, **kwargs):
        return None

    monkeypatch.setattr("src.db.repositories.refresh_token_repository.rotate", mock_rotate)

    refresh_jwt = "valid_token"

    with pytest.raises(NotFoundError):
        await auth_service.refresh(db_session, refresh_jwt, user_agent=None, ip=None)


@pytest.mark.unit
async def test_logout_invalid_token(db_session: AsyncSession):
    refresh_jwt = "invalid_token"

    with pytest.raises(AuthenticationError):
        await auth_service.logout(db_session, refresh_jwt)


@pytest.mark.unit
async def test_logout_missing_jti(db_session: AsyncSession, monkeypatch):
    # Mock decode_token to return a token without jti
    def mock_decode_token(*args, **kwargs):
        return {"sub": "1", "typ": "refresh"}

    monkeypatch.setattr("src.core.jwt.decode_token", mock_decode_token)

    # Mock validate_typ to do nothing
    def mock_validate_typ(*args, **kwargs):
        pass

    monkeypatch.setattr("src.core.jwt.validate_typ", mock_validate_typ)

    refresh_jwt = "valid_token"

    with pytest.raises(AuthenticationError):
        await auth_service.logout(db_session, refresh_jwt)
