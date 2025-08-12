import importlib

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError, ValidationError
from db.models.user import User
import schemas.posts
from schemas.responses import PaginatedResponse, PaginationMeta, SuccessResponse
from services.auth_utils import check_create_post_permission, check_post_owner_or_admin


async def get_all_posts(db: AsyncSession, page: int = 1, limit: int = 10) -> PaginatedResponse[schemas.posts.PostOut]:
    if page < 1:
        raise ValidationError("page must be >= 1")
    if limit < 1:
        raise ValidationError("limit must be >= 1")

    offset = (page - 1) * limit
    repo = importlib.import_module("db.repositories.post_repository")
    posts = await repo.get_posts_paginated(db=db, offset=offset, limit=limit)
    total = await repo.count_posts(db)

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


async def get_post_by_id(db: AsyncSession, post_id: int) -> SuccessResponse[schemas.posts.PostOut]:
    repo = importlib.import_module("db.repositories.post_repository")
    post = await repo.get_post_by_id(db, post_id)
    if not post:
        raise NotFoundError(f"Post with id {post_id} not found")
    return SuccessResponse[schemas.posts.PostOut].ok(schemas.posts.PostOut.model_validate(post))


async def create_post(
    db: AsyncSession,
    post_data: schemas.posts.PostCreate,
    *,
    current_user: User | None = None,
) -> SuccessResponse[schemas.posts.PostOut]:
    if current_user is not None:
        await check_create_post_permission(current_user, post_data.author_id)

    repo = importlib.import_module("db.repositories.post_repository")
    try:
        post = await repo.create_post(
            db=db,
            title=post_data.title,
            content=post_data.content,
            is_published=post_data.is_published,
            author_id=post_data.author_id,
        )
    except IntegrityError as e:
        # Map FK or other integrity issues to service-level validation error for consistent API
        raise ValidationError("Failed to create post") from e
    if not post:
        raise ValidationError("Failed to create post")

    await db.commit()
    return SuccessResponse[schemas.posts.PostOut].ok(schemas.posts.PostOut.model_validate(post))


async def update_title(
    db: AsyncSession, post_id: int, title: str, *, current_user: User | None = None
) -> SuccessResponse[schemas.posts.PostOut]:
    if current_user is not None:
        await check_post_owner_or_admin(db, post_id, current_user)
    repo = importlib.import_module("db.repositories.post_repository")
    result = await repo.update_title_by_id(db=db, post_id=post_id, title=title)
    if not result:
        # Distinguish not found from failed update
        exists = await repo.get_post_by_id(db, post_id)
        if not exists:
            raise NotFoundError("Post not found")
        raise ValidationError("Failed to update title")

    updated_post = await importlib.import_module("db.repositories.post_repository").get_post_by_id(db, post_id)
    if not updated_post:
        raise NotFoundError("Post not found after update")

    await db.commit()
    return SuccessResponse[schemas.posts.PostOut].ok(schemas.posts.PostOut.model_validate(updated_post))


async def update_content(
    db: AsyncSession, post_id: int, content: str, *, current_user: User | None = None
) -> SuccessResponse[schemas.posts.PostOut]:
    if current_user is not None:
        await check_post_owner_or_admin(db, post_id, current_user)
    repo = importlib.import_module("db.repositories.post_repository")
    result = await repo.update_content_by_id(db=db, post_id=post_id, content=content)
    if not result:
        # Distinguish not found from failed update
        exists = await repo.get_post_by_id(db, post_id)
        if not exists:
            raise NotFoundError("Post not found")
        raise ValidationError("Failed to update content")

    updated_post = await repo.get_post_by_id(db, post_id)
    if not updated_post:
        raise NotFoundError("Post not found after update")

    await db.commit()
    return SuccessResponse[schemas.posts.PostOut].ok(schemas.posts.PostOut.model_validate(updated_post))


async def delete_post(db: AsyncSession, post_id: int, *, current_user: User | None = None) -> SuccessResponse[str]:
    if current_user is not None:
        await check_post_owner_or_admin(db, post_id, current_user)
    repo = importlib.import_module("db.repositories.post_repository")
    result = await repo.delete_post_by_id(db=db, post_id=post_id)
    if not result:
        raise NotFoundError("Post not found")
    await db.commit()
    return SuccessResponse[str].ok("Post deleted")
