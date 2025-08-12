import importlib

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AuthorizationError, ConflictError, NotFoundError
from db.models.user import User
import db.repositories.user_repository as user_repository


async def check_post_owner_or_admin(db: AsyncSession, post_id: int, current_user: User) -> None:
    """
    Checks if the user is the owner of the post or an admin.

    Args:
        db: Asynchronous database session
        post_id: ID of the post
        current_user: Current user

    Raises:
        NotFoundError: If the post is not found
        AuthorizationError: If the user is neither the owner nor an admin
    """
    repo = importlib.import_module("db.repositories.post_repository")
    post = await repo.get_post_by_id(db, post_id)
    if not post:
        raise NotFoundError("Post not found")

    is_admin = (current_user.role if hasattr(current_user, "role") else "user") == "admin"
    raw_owner_id = getattr(post, "author_id", None)
    if raw_owner_id is None:
        raise NotFoundError("Post has no author")

    owner_id = int(raw_owner_id)
    user_id = int(current_user.id)

    if not is_admin and owner_id != user_id:
        raise AuthorizationError("Forbidden")


async def check_create_post_permission(current_user: User, post_author_id: int) -> None:
    """
    Checks if the user can create a post on behalf of the specified author.

    Args:
        current_user: Current user
        post_author_id: ID of the post author

    Raises:
        AuthorizationError: If the user cannot create a post for the specified author
    """
    is_admin = (current_user.role if hasattr(current_user, "role") else "user") == "admin"
    user_id = int(current_user.id)

    if not is_admin and int(post_author_id) != user_id:
        raise AuthorizationError("Cannot create post for another user")


async def check_username_unique(db: AsyncSession, username: str, user_id: int | None = None) -> None:
    """
    Checks the uniqueness of the username.

    Args:
        db: Asynchronous database session
        username: Username to check
        user_id: User ID (if checking for an existing user)

    Raises:
        ConflictError: If the username is already taken
    """
    existing = await user_repository.get_user_by_username(db, username)
    if existing is not None and (user_id is None or int(getattr(existing, "id", 0)) != int(user_id)):
        raise ConflictError("Username already registered")


async def check_email_unique(db: AsyncSession, email: str, user_id: int | None = None) -> None:
    """
    Checks the uniqueness of the email.

    Args:
        db: Asynchronous database session
        email: Email to check
        user_id: User ID (if checking for an existing user)

    Raises:
        ConflictError: If the email is already taken
    """
    existing = await user_repository.get_user_by_email(db, email)
    if existing is not None and (user_id is None or int(getattr(existing, "id", 0)) != int(user_id)):
        raise ConflictError("Email already registered")
