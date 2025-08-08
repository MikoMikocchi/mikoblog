from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError, ValidationError
import db.repositories.post_repository as post_repository
import schemas.posts
from schemas.responses import PaginatedResponse, PaginationMeta, SuccessResponse
from services.auth_utils import check_create_post_permission, check_post_owner_or_admin


async def get_all_posts(db: AsyncSession, page: int = 1, limit: int = 10) -> PaginatedResponse[schemas.posts.PostOut]:
    if page < 1:
        raise ValidationError("page must be >= 1")
    if limit < 1:
        raise ValidationError("limit must be >= 1")

    offset = (page - 1) * limit
    posts = await post_repository.get_posts_paginated(db=db, offset=offset, limit=limit)
    total = await post_repository.count_posts(db)

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
    post = await post_repository.get_post_by_id(db, post_id)
    if not post:
        raise NotFoundError(f"Post with id {post_id} not found")
    return SuccessResponse[schemas.posts.PostOut].ok(schemas.posts.PostOut.model_validate(post))


async def create_post(
    db: AsyncSession,
    post_data: schemas.posts.PostCreate,
    *,
    current_user: Any | None = None,
) -> SuccessResponse[schemas.posts.PostOut]:
    if current_user is not None:
        await check_create_post_permission(current_user, post_data.author_id)

    post = await post_repository.create_post(
        db=db,
        title=post_data.title,
        content=post_data.content,
        is_published=post_data.is_published,
        author_id=post_data.author_id,
    )
    if not post:
        raise ValidationError("Failed to create post")

    await db.commit()
    return SuccessResponse[schemas.posts.PostOut].ok(schemas.posts.PostOut.model_validate(post))


async def update_title(
    db: AsyncSession, post_id: int, title: str, *, current_user: Any | None = None
) -> SuccessResponse[schemas.posts.PostOut]:
    if current_user is not None:
        await check_post_owner_or_admin(db, post_id, current_user)
    result = await post_repository.update_title_by_id(db=db, post_id=post_id, title=title)
    if not result:
        raise ValidationError("Failed to update title")

    updated_post = await post_repository.get_post_by_id(db, post_id)
    if not updated_post:
        raise NotFoundError("Post not found after update")

    await db.commit()
    return SuccessResponse[schemas.posts.PostOut].ok(schemas.posts.PostOut.model_validate(updated_post))


async def update_content(
    db: AsyncSession, post_id: int, content: str, *, current_user: Any | None = None
) -> SuccessResponse[schemas.posts.PostOut]:
    if current_user is not None:
        await check_post_owner_or_admin(db, post_id, current_user)
    result = await post_repository.update_content_by_id(db=db, post_id=post_id, content=content)
    if not result:
        raise ValidationError("Failed to update content")

    updated_post = await post_repository.get_post_by_id(db, post_id)
    if not updated_post:
        raise NotFoundError("Post not found after update")

    await db.commit()
    return SuccessResponse[schemas.posts.PostOut].ok(schemas.posts.PostOut.model_validate(updated_post))


async def delete_post(db: AsyncSession, post_id: int, *, current_user: Any | None = None) -> SuccessResponse[str]:
    if current_user is not None:
        await check_post_owner_or_admin(db, post_id, current_user)
    result = await post_repository.delete_post_by_id(db=db, post_id=post_id)
    if not result:
        raise NotFoundError("Post not found")
    await db.commit()
    return SuccessResponse[str].ok("Post deleted")
