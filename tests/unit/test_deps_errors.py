from httpx import AsyncClient
import pytest

from core.exceptions import AuthenticationError


@pytest.mark.unit
async def test_get_current_user_missing_authorization_header(client: AsyncClient, monkeypatch):
    # Mock bearer_scheme to return None
    class MockCredentials:
        scheme = None
        credentials = None

    async def mock_bearer_scheme(*args, **kwargs):
        return None

    monkeypatch.setattr("core.deps.bearer_scheme", mock_bearer_scheme)

    response = await client.get("/api/v1/users/1")

    assert response.status_code == 401  # AuthenticationError should map to 401


@pytest.mark.unit
async def test_get_current_user_invalid_authorization_scheme(client: AsyncClient, monkeypatch):
    # Mock bearer_scheme to return invalid scheme
    class MockCredentials:
        scheme = "Basic"
        credentials = "credentials"

    async def mock_bearer_scheme(*args, **kwargs):
        return MockCredentials()

    monkeypatch.setattr("core.deps.bearer_scheme", mock_bearer_scheme)

    response = await client.get("/api/v1/users/1")

    assert response.status_code == 401  # AuthenticationError should map to 401


@pytest.mark.unit
async def test_get_current_user_missing_bearer_token(client: AsyncClient, monkeypatch):
    # Mock bearer_scheme to return missing credentials
    class MockCredentials:
        scheme = "Bearer"
        credentials = None

    async def mock_bearer_scheme(*args, **kwargs):
        return MockCredentials()

    monkeypatch.setattr("core.deps.bearer_scheme", mock_bearer_scheme)

    response = await client.get("/api/v1/users/1")

    assert response.status_code == 401  # AuthenticationError should map to 401


@pytest.mark.unit
async def test_get_current_user_invalid_token(client: AsyncClient, monkeypatch):
    # Mock decode_token to raise AuthenticationError
    def mock_decode_token(*args, **kwargs):
        raise AuthenticationError("Invalid token")

    monkeypatch.setattr("core.jwt.decode_token", mock_decode_token)

    response = await client.get("/api/v1/users/1")

    assert response.status_code == 401  # AuthenticationError should map to 401


@pytest.mark.unit
async def test_get_current_user_invalid_typ_claim(client: AsyncClient, monkeypatch):
    # Mock decode_token to return a token with invalid typ
    def mock_decode_token(*args, **kwargs):
        return {"sub": "1", "typ": "refresh"}

    monkeypatch.setattr("core.jwt.decode_token", mock_decode_token)

    # Mock validate_typ to raise AuthenticationError
    def mock_validate_typ(*args, **kwargs):
        raise AuthenticationError("Invalid token type: expected access")

    monkeypatch.setattr("core.jwt.validate_typ", mock_validate_typ)

    response = await client.get("/api/v1/users/1")

    assert response.status_code == 401  # AuthenticationError should map to 401


@pytest.mark.unit
async def test_get_current_user_invalid_sub_claim(client: AsyncClient, monkeypatch):
    # Mock decode_token to return a token with invalid sub
    def mock_decode_token(*args, **kwargs):
        return {"sub": "invalid", "typ": "access"}

    monkeypatch.setattr("core.jwt.decode_token", mock_decode_token)

    # Mock validate_typ to do nothing
    def mock_validate_typ(*args, **kwargs):
        pass

    monkeypatch.setattr("core.jwt.validate_typ", mock_validate_typ)

    response = await client.get("/api/v1/users/1")

    assert response.status_code == 401  # AuthenticationError should map to 401


@pytest.mark.unit
async def test_get_current_user_user_not_found(client: AsyncClient, monkeypatch):
    # Mock decode_token to return a valid token
    def mock_decode_token(*args, **kwargs):
        return {"sub": "1", "typ": "access"}

    monkeypatch.setattr("core.jwt.decode_token", mock_decode_token)

    # Mock validate_typ to do nothing
    def mock_validate_typ(*args, **kwargs):
        pass

    monkeypatch.setattr("core.jwt.validate_typ", mock_validate_typ)

    # Mock get_user_by_id to return None
    async def mock_get_user_by_id(*args, **kwargs):
        return None

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_id", mock_get_user_by_id)

    response = await client.get("/api/v1/users/1")

    assert response.status_code == 401  # AuthenticationError should map to 401


@pytest.mark.unit
async def test_require_admin_authorization_error(client: AsyncClient, monkeypatch):
    # Mock get_current_user to return a user with user role
    class MockUser:
        role = "user"

    async def mock_get_current_user(*args, **kwargs):
        return MockUser()

    monkeypatch.setattr("core.deps.get_current_user", mock_get_current_user)

    response = await client.patch("/api/v1/users/1", json={"username": "newusername"})

    assert response.status_code == 403  # AuthorizationError should map to 403
