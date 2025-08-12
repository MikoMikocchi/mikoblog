import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AuthorizationError, NotFoundError, ValidationError
import db.repositories.post_repository as post_repository
from schemas.posts import PostContentUpdate, PostCreate, PostTitleUpdate
from services import post_service


@pytest.mark.unit
async def test_get_all_posts_validation_error_invalid_page(db_session: AsyncSession):
    with pytest.raises(ValidationError):
        await post_service.get_all_posts(db_session, page=0, limit=10)


@pytest.mark.unit
async def test_get_all_posts_validation_error_invalid_limit(db_session: AsyncSession):
    with pytest.raises(ValidationError):
        await post_service.get_all_posts(db_session, page=1, limit=0)


@pytest.mark.unit
async def test_get_post_by_id_not_found(db_session: AsyncSession, monkeypatch):
    # Mock get_post_by_id to return None
    async def mock_get_post_by_id(*args, **kwargs):
        return None

    monkeypatch.setattr(post_repository, "get_post_by_id", mock_get_post_by_id)

    with pytest.raises(NotFoundError):
        await post_service.get_post_by_id(db_session, 1)


@pytest.mark.unit
async def test_create_post_authorization_error_not_owner(db_session: AsyncSession, monkeypatch):
    # Mock user object
    class MockUser:
        id = 1
        role = "user"

    payload = PostCreate(title="Test Post", content="Test Content", author_id=2, is_published=True)  # different from user id

    with pytest.raises(AuthorizationError):
        await post_service.create_post(db_session, payload, current_user=MockUser())


@pytest.mark.unit
async def test_create_post_validation_error_failed_to_create(db_session: AsyncSession, monkeypatch):
    # Mock user object
    class MockUser:
        id = 1
        role = "user"

    payload = PostCreate(title="Test Post", content="Test Content", author_id=1, is_published=True)

    # Mock create_post to return None
    async def mock_create_post(*args, **kwargs):
        return None

    monkeypatch.setattr(post_repository, "create_post", mock_create_post)

    with pytest.raises(ValidationError):
        await post_service.create_post(db_session, payload, current_user=MockUser())


@pytest.mark.unit
async def test_update_title_post_not_found(db_session: AsyncSession, monkeypatch):
    # Mock get_post_by_id to return None
    async def mock_get_post_by_id(*args, **kwargs):
        return None

    monkeypatch.setattr(post_repository, "get_post_by_id", mock_get_post_by_id)

    payload = PostTitleUpdate(title="New Title")

    with pytest.raises(NotFoundError):
        await post_service.update_title(db_session, 1, payload.title, current_user=None)


@pytest.mark.unit
async def test_update_title_authorization_error_not_owner(db_session: AsyncSession, monkeypatch):
    # Mock post object
    class MockPost:
        author_id = 2

    # Mock get_post_by_id to return a post
    async def mock_get_post_by_id(*args, **kwargs):
        return MockPost()

    monkeypatch.setattr(post_repository, "get_post_by_id", mock_get_post_by_id)

    # Mock user object
    class MockUser:
        id = 1
        role = "user"

    payload = PostTitleUpdate(title="New Title")

    with pytest.raises(AuthorizationError):
        await post_service.update_title(db_session, 1, payload.title, current_user=MockUser())


@pytest.mark.unit
async def test_update_title_validation_error_failed_to_update(db_session: AsyncSession, monkeypatch):
    # Mock post object
    class MockPost:
        author_id = 1

    # Mock get_post_by_id to return a post
    async def mock_get_post_by_id(*args, **kwargs):
        return MockPost()

    monkeypatch.setattr(post_repository, "get_post_by_id", mock_get_post_by_id)

    # Mock user object
    class MockUser:
        id = 1
        role = "user"

    # Mock update_title_by_id to return False
    async def mock_update_title_by_id(*args, **kwargs):
        return False

    monkeypatch.setattr(post_repository, "update_title_by_id", mock_update_title_by_id)

    payload = PostTitleUpdate(title="New Title")

    with pytest.raises(ValidationError):
        await post_service.update_title(db_session, 1, payload.title, current_user=MockUser())


@pytest.mark.unit
async def test_update_title_post_not_found_after_update(db_session: AsyncSession, monkeypatch):
    # Mock post object
    class MockPost:
        author_id = 1

    # Mock get_post_by_id to return a post
    async def mock_get_post_by_id(*args, **kwargs):
        return MockPost()

    monkeypatch.setattr(post_repository, "get_post_by_id", mock_get_post_by_id)

    # Mock user object
    class MockUser:
        id = 1
        role = "user"

    # Mock update_title_by_id to return True
    async def mock_update_title_by_id(*args, **kwargs):
        return True

    monkeypatch.setattr(post_repository, "update_title_by_id", mock_update_title_by_id)

    # Mock get_post_by_id to return None after update
    async def mock_get_post_by_id_after(*args, **kwargs):
        return None

    monkeypatch.setattr(post_repository, "get_post_by_id", mock_get_post_by_id_after)

    payload = PostTitleUpdate(title="New Title")

    with pytest.raises(NotFoundError):
        await post_service.update_title(db_session, 1, payload.title, current_user=MockUser())


@pytest.mark.unit
async def test_update_content_post_not_found(db_session: AsyncSession, monkeypatch):
    # Mock get_post_by_id to return None
    async def mock_get_post_by_id(*args, **kwargs):
        return None

    monkeypatch.setattr(post_repository, "get_post_by_id", mock_get_post_by_id)

    payload = PostContentUpdate(content="New Content")

    with pytest.raises(NotFoundError):
        await post_service.update_content(db_session, 1, payload.content, current_user=None)


@pytest.mark.unit
async def test_update_content_authorization_error_not_owner(db_session: AsyncSession, monkeypatch):
    # Mock post object
    class MockPost:
        author_id = 2

    # Mock get_post_by_id to return a post
    async def mock_get_post_by_id(*args, **kwargs):
        return MockPost()

    monkeypatch.setattr(post_repository, "get_post_by_id", mock_get_post_by_id)

    # Mock user object
    class MockUser:
        id = 1
        role = "user"

    payload = PostContentUpdate(content="New Content")

    with pytest.raises(AuthorizationError):
        await post_service.update_content(db_session, 1, payload.content, current_user=MockUser())


@pytest.mark.unit
async def test_update_content_validation_error_failed_to_update(db_session: AsyncSession, monkeypatch):
    # Mock post object
    class MockPost:
        author_id = 1

    # Mock get_post_by_id to return a post
    async def mock_get_post_by_id(*args, **kwargs):
        return MockPost()

    monkeypatch.setattr(post_repository, "get_post_by_id", mock_get_post_by_id)

    # Mock user object
    class MockUser:
        id = 1
        role = "user"

    # Mock update_content_by_id to return False
    async def mock_update_content_by_id(*args, **kwargs):
        return False

    monkeypatch.setattr(post_repository, "update_content_by_id", mock_update_content_by_id)

    payload = PostContentUpdate(content="New Content")

    with pytest.raises(ValidationError):
        await post_service.update_content(db_session, 1, payload.content, current_user=MockUser())


@pytest.mark.unit
async def test_update_content_post_not_found_after_update(db_session: AsyncSession, monkeypatch):
    # Mock post object
    class MockPost:
        author_id = 1

    # Mock get_post_by_id to return a post
    async def mock_get_post_by_id(*args, **kwargs):
        return MockPost()

    monkeypatch.setattr(post_repository, "get_post_by_id", mock_get_post_by_id)

    # Mock user object
    class MockUser:
        id = 1
        role = "user"

    # Mock update_content_by_id to return True
    async def mock_update_content_by_id(*args, **kwargs):
        return True

    monkeypatch.setattr(post_repository, "update_content_by_id", mock_update_content_by_id)

    # Mock get_post_by_id to return None after update
    async def mock_get_post_by_id_after(*args, **kwargs):
        return None

    monkeypatch.setattr(post_repository, "get_post_by_id", mock_get_post_by_id_after)

    payload = PostContentUpdate(content="New Content")

    with pytest.raises(NotFoundError):
        await post_service.update_content(db_session, 1, payload.content, current_user=MockUser())


@pytest.mark.unit
async def test_delete_post_post_not_found(db_session: AsyncSession, monkeypatch):
    # Mock get_post_by_id to return None
    async def mock_get_post_by_id(*args, **kwargs):
        return None

    monkeypatch.setattr(post_repository, "get_post_by_id", mock_get_post_by_id)

    with pytest.raises(NotFoundError):
        await post_service.delete_post(db_session, 1, current_user=None)


@pytest.mark.unit
async def test_delete_post_authorization_error_not_owner(db_session: AsyncSession, monkeypatch):
    # Mock post object
    class MockPost:
        author_id = 2

    # Mock get_post_by_id to return a post
    async def mock_get_post_by_id(*args, **kwargs):
        return MockPost()

    monkeypatch.setattr(post_repository, "get_post_by_id", mock_get_post_by_id)

    # Mock user object
    class MockUser:
        id = 1
        role = "user"

    with pytest.raises(AuthorizationError):
        await post_service.delete_post(db_session, 1, current_user=MockUser())


@pytest.mark.unit
async def test_delete_post_not_found(db_session: AsyncSession, monkeypatch):
    # Mock post object
    class MockPost:
        author_id = 1

    # Mock get_post_by_id to return a post
    async def mock_get_post_by_id(*args, **kwargs):
        return MockPost()

    monkeypatch.setattr(post_repository, "get_post_by_id", mock_get_post_by_id)

    # Mock user object
    class MockUser:
        id = 1
        role = "user"

    # Mock delete_post_by_id to return False
    async def mock_delete_post_by_id(*args, **kwargs):
        return False

    monkeypatch.setattr(post_repository, "delete_post_by_id", mock_delete_post_by_id)

    with pytest.raises(NotFoundError):
        await post_service.delete_post(db_session, 1, current_user=MockUser())
