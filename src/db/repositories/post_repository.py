import logging
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exceptions import ValidationError
from db.models.post import Post
from db.repositories.decorators import handle_db_errors, with_retry

logger = logging.getLogger(__name__)

DEFAULT_MAX_LIMIT: int = 100

AllowedField = Literal["title", "content", "is_published"]
ALLOWED_UPDATE_FIELDS: frozenset[AllowedField] = frozenset({"title", "content", "is_published"})


@handle_db_errors()
async def create_post(
    db: AsyncSession,
    title: str,
    content: str,
    author_id: int,
    is_published: bool = True,
) -> Post:
    new_post = Post(
        title=title,
        content=content,
        is_published=is_published,
        author_id=author_id,
    )
    db.add(new_post)
    await db.flush()
    await db.refresh(new_post)
    logger.info("Created new post with id %s", new_post.id)
    return new_post


@with_retry(log_prefix="fetching all posts")
async def get_all_posts(db: AsyncSession) -> list[Post]:
    stmt = select(Post).options(selectinload(Post.author)).order_by(Post.id)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@with_retry(log_prefix="counting posts")
async def count_posts(db: AsyncSession) -> int:
    from sqlalchemy import func

    stmt = select(func.count(Post.id))
    res = await db.execute(stmt)
    return int(res.scalar_one())


@with_retry(log_prefix="fetching post")
async def get_post_by_id(db: AsyncSession, post_id: int) -> Post | None:
    if post_id <= 0:
        logger.warning("Invalid post_id: %s (must be > 0)", post_id)
        return None

    stmt = select(Post).options(selectinload(Post.author)).where(Post.id == post_id)
    res = await db.execute(stmt)
    post = res.scalars().first()
    if not post:
        logger.info("Post with id %s not found", post_id)
    return post


@with_retry(log_prefix="fetching paginated posts")
async def get_posts_paginated(db: AsyncSession, offset: int, limit: int) -> list[Post]:
    if offset < 0:
        raise ValidationError("offset must be an integer >= 0")
    if limit <= 0 or limit > DEFAULT_MAX_LIMIT:
        raise ValidationError(f"limit must be in 1..{DEFAULT_MAX_LIMIT}")

    stmt = select(Post).options(selectinload(Post.author)).order_by(Post.id).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@handle_db_errors()
async def delete_post_by_id(db: AsyncSession, post_id: int) -> bool:
    post = await get_post_by_id(db, post_id)
    if not post:
        logger.info("Skip delete: post %s not found", post_id)
        return False

    await db.delete(post)
    logger.info("Deleted post with id %s", post_id)
    return True


@handle_db_errors()
async def update_post_field(db: AsyncSession, post_id: int, field: AllowedField, value: object) -> bool:
    post = await get_post_by_id(db, post_id)
    if not post:
        logger.info("Skip update: post %s not found", post_id)
        return False

    if field not in ALLOWED_UPDATE_FIELDS:
        logger.warning("Attempt to update disallowed field '%s' for post %s", field, post_id)
        return False

    if field in ("title", "content"):
        if not isinstance(value, str):
            logger.warning(
                "Invalid value type for '%s': expected str, got %s",
                field,
                type(value).__name__,
            )
            return False
        object.__setattr__(post, field, value)

    elif field == "is_published":
        if not isinstance(value, bool):
            logger.warning(
                "Invalid value type for '%s': expected bool, got %s",
                field,
                type(value).__name__,
            )
            return False
        object.__setattr__(post, field, value)

    await db.flush()
    await db.refresh(post)
    logger.info("Updated %s for post %s", field, post_id)
    return True


@handle_db_errors()
async def update_title_by_id(db: AsyncSession, post_id: int, title: str) -> bool:
    return await update_post_field(db, post_id, "title", title)


@handle_db_errors()
async def update_content_by_id(db: AsyncSession, post_id: int, content: str) -> bool:
    return await update_post_field(db, post_id, "content", content)


@handle_db_errors()
async def change_is_published_by_id(db: AsyncSession, post_id: int, is_published: bool) -> bool:
    return await update_post_field(db, post_id, "is_published", is_published)
