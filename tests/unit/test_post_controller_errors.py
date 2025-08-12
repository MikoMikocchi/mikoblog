from httpx import AsyncClient
import pytest

from core.exceptions import AuthorizationError, NotFoundError, ValidationError


@pytest.mark.unit
async def test_get_all_posts_validation_error_invalid_page(unit_client: AsyncClient, monkeypatch):
    # Mock post_service.get_all_posts to raise ValidationError
    async def mock_get_all_posts(*args, **kwargs):
        raise ValidationError("page must be >= 1")

    monkeypatch.setattr("services.post_service.get_all_posts", mock_get_all_posts)

    response = await unit_client.get("/api/v1/posts?page=0&limit=10")

    assert response.status_code == 422  # ValidationError should map to 422


@pytest.mark.unit
async def test_get_all_posts_validation_error_invalid_limit(unit_client: AsyncClient, monkeypatch):
    # Mock post_service.get_all_posts to raise ValidationError
    async def mock_get_all_posts(*args, **kwargs):
        raise ValidationError("limit must be >= 1")

    monkeypatch.setattr("services.post_service.get_all_posts", mock_get_all_posts)

    response = await unit_client.get("/api/v1/posts?page=1&limit=0")

    assert response.status_code == 422  # ValidationError should map to 422


@pytest.mark.unit
async def test_get_post_not_found(unit_client: AsyncClient, monkeypatch):
    # Mock post_service.get_post_by_id to raise NotFoundError
    async def mock_get_post_by_id(*args, **kwargs):
        raise NotFoundError("Post with id 1 not found")

    monkeypatch.setattr("services.post_service.get_post_by_id", mock_get_post_by_id)

    response = await unit_client.get("/api/v1/posts/1")

    assert response.status_code == 404  # NotFoundError should map to 404


@pytest.mark.unit
async def test_create_post_validation_error(unit_client: AsyncClient, monkeypatch):
    # Mock post_service.create_post to raise ValidationError
    async def mock_create_post(*args, **kwargs):
        raise ValidationError("Invalid title")

    monkeypatch.setattr("services.post_service.create_post", mock_create_post)

    payload = {"title": "", "content": "Test Content", "author_id": 1, "is_published": True}  # empty title should cause ValidationError

    response = await unit_client.post("/api/v1/posts", json=payload)

    assert response.status_code == 422  # ValidationError should map to 422


@pytest.mark.unit
async def test_create_post_authorization_error(unit_client: AsyncClient, monkeypatch):
    # Mock post_service.create_post to raise AuthorizationError
    async def mock_create_post(*args, **kwargs):
        raise AuthorizationError("Cannot create post for another user")

    monkeypatch.setattr("services.post_service.create_post", mock_create_post)

    payload = {
        "title": "A Proper Valid Title",
        "content": "This is valid content with enough words to satisfy all validators and avoid 422.",
        "author_id": 2,  # different from current user
        "is_published": True,
    }

    response = await unit_client.post("/api/v1/posts", json=payload)
    assert response.status_code == 403  # AuthorizationError should map to 403


@pytest.mark.unit
async def test_update_title_post_not_found(unit_client: AsyncClient, monkeypatch):
    # Mock post_service.update_title to raise NotFoundError
    async def mock_update_title(*args, **kwargs):
        raise NotFoundError("Post with id 1 not found")

    monkeypatch.setattr("services.post_service.update_title", mock_update_title)

    payload = {"title": "New Title"}

    response = await unit_client.patch("/api/v1/posts/1/title", json=payload)

    assert response.status_code == 404  # NotFoundError should map to 404


@pytest.mark.unit
async def test_update_title_authorization_error(unit_client: AsyncClient, monkeypatch):
    # Mock post_service.update_title to raise AuthorizationError
    async def mock_update_title(*args, **kwargs):
        raise AuthorizationError("Forbidden")

    monkeypatch.setattr("services.post_service.update_title", mock_update_title)

    payload = {"title": "New Title"}

    response = await unit_client.patch("/api/v1/posts/1/title", json=payload)

    assert response.status_code == 403  # AuthorizationError should map to 403


@pytest.mark.unit
async def test_update_content_post_not_found(unit_client: AsyncClient, monkeypatch):
    # Mock post_service.update_content to raise NotFoundError
    async def mock_update_content(*args, **kwargs):
        raise NotFoundError("Post with id 1 not found")

    monkeypatch.setattr("services.post_service.update_content", mock_update_content)

    payload = {"content": "New Content"}

    response = await unit_client.patch("/api/v1/posts/1/content", json=payload)

    assert response.status_code == 404  # NotFoundError should map to 404


@pytest.mark.unit
async def test_update_content_authorization_error(unit_client: AsyncClient, monkeypatch):
    # Mock post_service.update_content to raise AuthorizationError
    async def mock_update_content(*args, **kwargs):
        raise AuthorizationError("Forbidden")

    monkeypatch.setattr("services.post_service.update_content", mock_update_content)

    payload = {"content": "New Content"}

    response = await unit_client.patch("/api/v1/posts/1/content", json=payload)

    assert response.status_code == 403  # AuthorizationError should map to 403


@pytest.mark.unit
async def test_delete_post_not_found(unit_client: AsyncClient, monkeypatch):
    # Mock post_service.delete_post to raise NotFoundError
    async def mock_delete_post(*args, **kwargs):
        raise NotFoundError("Post with id 1 not found")

    monkeypatch.setattr("services.post_service.delete_post", mock_delete_post)

    response = await unit_client.delete("/api/v1/posts/1")

    assert response.status_code == 404  # NotFoundError should map to 404


@pytest.mark.unit
async def test_delete_post_authorization_error(unit_client: AsyncClient, monkeypatch):
    # Mock post_service.delete_post to raise AuthorizationError
    async def mock_delete_post(*args, **kwargs):
        raise AuthorizationError("Forbidden")

    monkeypatch.setattr("services.post_service.delete_post", mock_delete_post)

    response = await unit_client.delete("/api/v1/posts/1")

    assert response.status_code == 403  # AuthorizationError should map to 403
