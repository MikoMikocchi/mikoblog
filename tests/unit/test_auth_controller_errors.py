from httpx import AsyncClient
import pytest

from core.exceptions import AuthenticationError

pytestmark = pytest.mark.anyio


@pytest.mark.unit
async def test_register_validation_error(unit_client: AsyncClient, monkeypatch):
    # Mock auth_service.register to raise ValidationError
    async def mock_register(*args, **kwargs):
        from core.exceptions import ValidationError

        raise ValidationError("Invalid email address")

    monkeypatch.setattr("services.auth_service.register", mock_register)

    payload = {
        "username": "testuser",
        "email": "invalid-email",  # invalid email should cause ValidationError
        "password": "Str0ng!Passw0rd",
    }

    response = await unit_client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422  # ValidationError should map to 422


@pytest.mark.unit
async def test_login_authentication_error(unit_client: AsyncClient, monkeypatch):
    # Mock user_repository.get_user_by_username to return None (user not found)
    async def mock_get_user_by_username(*args, **kwargs):
        return None

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_username", mock_get_user_by_username)

    # Mock user_repository.get_user_by_email to return None (user not found)
    async def mock_get_user_by_email(*args, **kwargs):
        return None

    monkeypatch.setattr("db.repositories.user_repository.get_user_by_email", mock_get_user_by_email)

    payload = {"username_or_email": "testuser", "password": "wrongpassword"}

    response = await unit_client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 401
    assert not response.json()["success"]
    assert response.json()["message"] == "Invalid credentials"


@pytest.mark.unit
async def test_refresh_authentication_error(unit_client: AsyncClient, monkeypatch):
    # Mock auth_service.refresh to raise AuthenticationError
    async def mock_refresh(*args, **kwargs):
        raise AuthenticationError("Invalid refresh token")

    monkeypatch.setattr("services.auth_service.refresh", mock_refresh)

    response = await unit_client.post("/api/v1/auth/refresh")

    assert response.status_code == 401  # AuthenticationError should map to 401


@pytest.mark.unit
async def test_logout_authentication_error(unit_client: AsyncClient, monkeypatch):
    # Mock auth_service.logout to raise AuthenticationError
    async def mock_logout(*args, **kwargs):
        raise AuthenticationError("Invalid refresh token")

    monkeypatch.setattr("services.auth_service.logout", mock_logout)
    # Ensure route actually calls auth_service by sending a refresh cookie
    unit_client.cookies.set("__Host-rt", "dummy", path="/")

    response = await unit_client.post("/api/v1/auth/logout")

    assert response.status_code == 401  # AuthenticationError should map to 401


@pytest.mark.unit
async def test_logout_all_authentication_error(unit_client: AsyncClient, monkeypatch):
    # Mock get_refresh_cookie to raise AuthenticationError
    def mock_get_refresh_cookie(*args, **kwargs):
        raise AuthenticationError("Missing refresh cookie")

    monkeypatch.setattr("api.utils.request_context.get_refresh_cookie", mock_get_refresh_cookie)

    response = await unit_client.post("/api/v1/auth/logout-all")

    assert response.status_code == 401  # AuthenticationError should map to 401


@pytest.mark.unit
async def test_logout_all_invalid_token(unit_client: AsyncClient, monkeypatch):
    # Mock get_refresh_cookie to return a valid cookie
    def mock_get_refresh_cookie(*args, **kwargs):
        return "valid_cookie"

    monkeypatch.setattr("api.utils.request_context.get_refresh_cookie", mock_get_refresh_cookie)

    # Mock decode_token to raise AuthenticationError
    def mock_decode_token(*args, **kwargs):
        raise AuthenticationError("Invalid token")

    monkeypatch.setattr("core.jwt.decode_token", mock_decode_token)

    response = await unit_client.post("/api/v1/auth/logout-all")

    assert response.status_code == 401  # AuthenticationError should map to 401


@pytest.mark.unit
async def test_logout_all_invalid_sub_claim(unit_client: AsyncClient, monkeypatch):
    # Mock get_refresh_cookie to return a valid cookie
    def mock_get_refresh_cookie(*args, **kwargs):
        return "valid_cookie"

    monkeypatch.setattr("api.utils.request_context.get_refresh_cookie", mock_get_refresh_cookie)

    # Mock decode_token to return a token with invalid sub
    def mock_decode_token(*args, **kwargs):
        return {"sub": "invalid", "typ": "refresh"}

    monkeypatch.setattr("core.jwt.decode_token", mock_decode_token)

    # Mock validate_typ to do nothing
    def mock_validate_typ(*args, **kwargs):
        pass

    monkeypatch.setattr("core.jwt.validate_typ", mock_validate_typ)

    response = await unit_client.post("/api/v1/auth/logout-all")

    assert response.status_code == 401  # AuthenticationError should map to 401
