from typing import Any, cast

from sqlalchemy.orm import Session

from core.exceptions import AuthorizationError, NotFoundError, ValidationError
import db.repositories.post_repository as post_repository
import schemas.posts
from schemas.responses import PaginatedResponse, PaginationMeta, SuccessResponse


def get_all_posts(db: Session, page: int = 1, limit: int = 10) -> PaginatedResponse[schemas.posts.PostOut]:
    if page < 1:
        raise ValidationError("page must be >= 1")
    if limit < 1:
        raise ValidationError("limit must be >= 1")

    offset = (page - 1) * limit
    posts = post_repository.get_posts_paginated(db=db, offset=offset, limit=limit)
    total = post_repository.count_posts(db)

    items = [schemas.posts.PostOut.model_validate(p) for p in posts]
    total_pages = max(1, (total + limit - 1) // limit)
    pagination = PaginationMeta(
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )
    return PaginatedResponse[schemas.posts.PostOut].ok(items=items, pagination=pagination)


def get_post_by_id(db: Session, post_id: int) -> SuccessResponse[schemas.posts.PostOut]:
    post = post_repository.get_post_by_id(db, post_id)
    if not post:
        raise NotFoundError(f"Post with id {post_id} not found")
    return SuccessResponse[schemas.posts.PostOut].ok(schemas.posts.PostOut.model_validate(post))


def create_post(
    db: Session,
    post_data: schemas.posts.PostCreate,
    *,
    current_user: Any | None = None,
) -> SuccessResponse[schemas.posts.PostOut]:
    if current_user is not None:
        is_admin = (current_user.role if hasattr(current_user, "role") else "user") == "admin"
        user_id = int(current_user.id)
        if not is_admin and int(post_data.author_id) != user_id:
            raise AuthorizationError("Cannot create post for another user")

    post = post_repository.create_post(
        db=db,
        title=post_data.title,
        content=post_data.content,
        is_published=post_data.is_published,
        author_id=post_data.author_id,
    )
    if not post:
        raise ValidationError("Failed to create post")
    return SuccessResponse[schemas.posts.PostOut].ok(schemas.posts.PostOut.model_validate(post))


def _ensure_owner_or_admin(db: Session, post_id: int, current_user: Any) -> None:
    post = post_repository.get_post_by_id(db, post_id)
    if not post:
        raise NotFoundError("Post not found")
    is_admin = (current_user.role if hasattr(current_user, "role") else "user") == "admin"
    raw_owner_id = getattr(post, "author_id", None)
    if raw_owner_id is None:
        raise NotFoundError("Post has no author")
    owner_id = cast(int, raw_owner_id) if isinstance(raw_owner_id, int) else int(raw_owner_id)
    user_id = int(current_user.id)
    if not is_admin and owner_id != user_id:
        raise AuthorizationError("Forbidden")


def update_title(db: Session, post_id: int, title: str, *, current_user: Any | None = None) -> SuccessResponse[schemas.posts.PostOut]:
    if current_user is not None:
        _ensure_owner_or_admin(db, post_id, current_user)
    result = post_repository.update_title_by_id(db=db, post_id=post_id, title=title)
    if not result:
        raise ValidationError("Failed to update title")

    updated_post = post_repository.get_post_by_id(db, post_id)
    if not updated_post:
        raise NotFoundError("Post not found after update")

    return SuccessResponse[schemas.posts.PostOut].ok(schemas.posts.PostOut.model_validate(updated_post))


def update_content(db: Session, post_id: int, content: str, *, current_user: Any | None = None) -> SuccessResponse[schemas.posts.PostOut]:
    if current_user is not None:
        _ensure_owner_or_admin(db, post_id, current_user)
    result = post_repository.update_content_by_id(db=db, post_id=post_id, content=content)
    if not result:
        raise ValidationError("Failed to update content")

    updated_post = post_repository.get_post_by_id(db, post_id)
    if not updated_post:
        raise NotFoundError("Post not found after update")

    return SuccessResponse[schemas.posts.PostOut].ok(schemas.posts.PostOut.model_validate(updated_post))


def delete_post(db: Session, post_id: int, *, current_user: Any | None = None) -> SuccessResponse[str]:
    if current_user is not None:
        _ensure_owner_or_admin(db, post_id, current_user)
    result = post_repository.delete_post_by_id(db=db, post_id=post_id)
    if not result:
        raise NotFoundError("Post not found")
    return SuccessResponse[str].ok("Post deleted")
