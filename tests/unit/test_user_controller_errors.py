from httpx import AsyncClient
import pytest

from src.core.exceptions import AuthorizationError, ConflictError, NotFoundError, ValidationError


@pytest.mark.unit
async def test_list_users_validation_error_invalid_page(unit_client: AsyncClient, monkeypatch):
    # Mock user_service.list_users to raise ValidationError
    async def mock_list_users(*args, **kwargs):
        raise ValidationError("page must be >= 1")

    monkeypatch.setattr("src.services.user_service.list_users", mock_list_users)

    response = await unit_client.get("/api/v1/users?page=0&limit=10")

    assert response.status_code == 422  # ValidationError should map to 422


@pytest.mark.unit
async def test_list_users_validation_error_invalid_limit(unit_client: AsyncClient, monkeypatch):
    # Mock user_service.list_users to raise ValidationError
    async def mock_list_users(*args, **kwargs):
        raise ValidationError("limit must be >= 1")

    monkeypatch.setattr("src.services.user_service.list_users", mock_list_users)

    response = await unit_client.get("/api/v1/users?page=1&limit=0")

    assert response.status_code == 422  # ValidationError should map to 422


@pytest.mark.unit
async def test_get_user_not_found(unit_client: AsyncClient, monkeypatch):
    # Mock user_service.get_user_by_id to raise NotFoundError
    async def mock_get_user_by_id(*args, **kwargs):
        raise NotFoundError("User with id 1 not found")

    monkeypatch.setattr("src.services.user_service.get_user_by_id", mock_get_user_by_id)

    response = await unit_client.get("/api/v1/users/1")

    assert response.status_code == 404  # NotFoundError should map to 404


@pytest.mark.unit
async def test_create_user_validation_error(unit_client: AsyncClient, monkeypatch):
    # Mock user_service.create_user to raise ValidationError
    async def mock_create_user(*args, **kwargs):
        raise ValidationError("Invalid email address")

    monkeypatch.setattr("src.services.user_service.create_user", mock_create_user)

    payload = {
        "username": "testuser",
        "email": "invalid-email",  # invalid email should cause ValidationError
        "password": "Str0ng!Passw0rd",
    }

    response = await unit_client.post("/api/v1/users", json=payload)

    assert response.status_code == 422  # ValidationError should map to 422


@pytest.mark.unit
async def test_create_user_conflict_error(unit_client: AsyncClient, monkeypatch):
    # Mock user_service.create_user to raise ConflictError
    async def mock_create_user(*args, **kwargs):
        raise ConflictError("Username already registered")

    monkeypatch.setattr("src.services.user_service.create_user", mock_create_user)

    payload = {"username": "existinguser", "email": "existing@example.com", "password": "Str0ng!Passw0rd"}

    response = await unit_client.post("/api/v1/users", json=payload)

    assert response.status_code == 409  # ConflictError should map to 409


@pytest.mark.unit
async def test_update_user_patch_not_found(unit_client: AsyncClient, monkeypatch):
    # Mock user_service.update_user_patch to raise NotFoundError
    async def mock_update_user_patch(*args, **kwargs):
        raise NotFoundError("User with id 1 not found")

    monkeypatch.setattr("src.services.user_service.update_user_patch", mock_update_user_patch)

    payload = {"username": "newusername", "email": "new@example.com", "password": "NewStr0ng!Passw0rd"}

    response = await unit_client.patch("/api/v1/users/1", json=payload)

    assert response.status_code == 404  # NotFoundError should map to 404


@pytest.mark.unit
async def test_update_user_patch_conflict_error(unit_client: AsyncClient, monkeypatch):
    # Mock user_service.update_user_patch to raise ConflictError
    async def mock_update_user_patch(*args, **kwargs):
        raise ConflictError("Username already registered")

    monkeypatch.setattr("src.services.user_service.update_user_patch", mock_update_user_patch)

    payload = {"username": "existinguser", "email": "new@example.com", "password": "NewStr0ng!Passw0rd"}

    response = await unit_client.patch("/api/v1/users/1", json=payload)

    assert response.status_code == 409  # ConflictError should map to 409


@pytest.mark.unit
async def test_update_user_patch_authorization_error(unit_client: AsyncClient, monkeypatch):
    # Mock require_admin to raise AuthorizationError
    def mock_require_admin(*args, **kwargs):
        raise AuthorizationError("Admin privileges required")

    monkeypatch.setattr("src.core.deps.require_admin", mock_require_admin)

    payload = {"username": "newusername", "email": "new@example.com", "password": "NewStr0ng!Passw0rd"}

    response = await unit_client.patch("/api/v1/users/1", json=payload)

    assert response.status_code == 403  # AuthorizationError should map to 403


@pytest.mark.unit
async def test_replace_user_put_not_found(unit_client: AsyncClient, monkeypatch):
    # Mock user_service.replace_user_put to raise NotFoundError
    async def mock_replace_user_put(*args, **kwargs):
        raise NotFoundError("User with id 1 not found")

    monkeypatch.setattr("src.services.user_service.replace_user_put", mock_replace_user_put)

    payload = {"username": "newusername", "email": "new@example.com", "password": "NewStr0ng!Passw0rd"}

    response = await unit_client.put("/api/v1/users/1", json=payload)

    assert response.status_code == 404  # NotFoundError should map to 404


@pytest.mark.unit
async def test_replace_user_put_conflict_error(unit_client: AsyncClient, monkeypatch):
    # Mock user_service.replace_user_put to raise ConflictError
    async def mock_replace_user_put(*args, **kwargs):
        raise ConflictError("Username already registered")

    monkeypatch.setattr("src.services.user_service.replace_user_put", mock_replace_user_put)

    payload = {"username": "existinguser", "email": "new@example.com", "password": "NewStr0ng!Passw0rd"}

    response = await unit_client.put("/api/v1/users/1", json=payload)

    assert response.status_code == 409  # ConflictError should map to 409


@pytest.mark.unit
async def test_replace_user_put_authorization_error(unit_client: AsyncClient, monkeypatch):
    # Mock require_admin to raise AuthorizationError
    def mock_require_admin(*args, **kwargs):
        raise AuthorizationError("Admin privileges required")

    monkeypatch.setattr("src.core.deps.require_admin", mock_require_admin)

    payload = {"username": "newusername", "email": "new@example.com", "password": "NewStr0ng!Passw0rd"}

    response = await unit_client.put("/api/v1/users/1", json=payload)

    assert response.status_code == 403  # AuthorizationError should map to 403


@pytest.mark.unit
async def test_delete_user_not_found(unit_client: AsyncClient, monkeypatch):
    # Mock user_service.delete_user to raise NotFoundError
    async def mock_delete_user(*args, **kwargs):
        raise NotFoundError("User with id 1 not found")

    monkeypatch.setattr("src.services.user_service.delete_user", mock_delete_user)

    response = await unit_client.delete("/api/v1/users/1")

    assert response.status_code == 404  # NotFoundError should map to 404


@pytest.mark.unit
async def test_delete_user_authorization_error(unit_client: AsyncClient, monkeypatch):
    # Mock require_admin to raise AuthorizationError
    def mock_require_admin(*args, **kwargs):
        raise AuthorizationError("Admin privileges required")

    monkeypatch.setattr("src.core.deps.require_admin", mock_require_admin)

    response = await unit_client.delete("/api/v1/users/1")

    assert response.status_code == 403  # AuthorizationError should map to 403
