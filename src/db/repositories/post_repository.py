import logging
from typing import Literal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from core.exceptions import NotFoundError, ValidationError
from db.models.post import Post
from db.utils import transactional

logger = logging.getLogger(__name__)

DEFAULT_MAX_LIMIT: int = 100

AllowedField = Literal["title", "content", "is_published"]
ALLOWED_UPDATE_FIELDS: frozenset[AllowedField] = frozenset({"title", "content", "is_published"})


@transactional
def create_post(
    db: Session,
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
    db.flush()
    db.refresh(new_post)
    logger.info("Created new post with id %s", new_post.id)
    return new_post


def get_all_posts(db: Session) -> list[Post]:
    try:
        posts = db.query(Post).options(joinedload(Post.author)).order_by(Post.id).all()
        return posts
    except SQLAlchemyError as e:
        logger.error("Database error while fetching all posts: %s", e)
        raise ValidationError("Failed to fetch all posts") from e


def count_posts(db: Session) -> int:
    return db.query(Post).count()


def get_post_by_id(db: Session, post_id: int) -> Post | None:
    if post_id <= 0:
        logger.warning("Invalid post_id: %s (must be > 0)", post_id)
        return None
    try:
        post = db.query(Post).options(joinedload(Post.author)).filter(Post.id == post_id).first()
        if not post:
            logger.info("Post with id %s not found", post_id)
        return post
    except SQLAlchemyError as e:
        logger.error("Database error while fetching post %s: %s", post_id, e)
        raise ValidationError("Failed to fetch post") from e


def get_posts_paginated(db: Session, offset: int, limit: int) -> list[Post]:
    if offset < 0:
        raise ValidationError("offset must be an integer >= 0")
    if limit <= 0 or limit > DEFAULT_MAX_LIMIT:
        raise ValidationError(f"limit must be in 1..{DEFAULT_MAX_LIMIT}")

    try:
        posts = db.query(Post).options(joinedload(Post.author)).order_by(Post.id).offset(offset).limit(limit).all()
        return posts
    except SQLAlchemyError as e:
        logger.error("Database error while fetching paginated posts: %s", e)
        raise ValidationError("Failed to fetch paginated posts") from e


@transactional
def delete_post_by_id(db: Session, post_id: int) -> bool:
    post = get_post_by_id(db, post_id)
    if not post:
        logger.info("Skip delete: post %s not found", post_id)
        raise NotFoundError("Post not found")

    try:
        db.delete(post)
        logger.info("Deleted post with id %s", post_id)
        return True
    except SQLAlchemyError as e:
        logger.error("Database error while deleting post %s: %s", post_id, e)
        raise ValidationError("Failed to delete post") from e


@transactional
def update_post_field(db: Session, post_id: int, field: AllowedField, value: object) -> bool:
    post = get_post_by_id(db, post_id)
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
        setattr(post, field, value)
    elif field == "is_published":
        if not isinstance(value, bool):
            logger.warning(
                "Invalid value type for '%s': expected bool, got %s",
                field,
                type(value).__name__,
            )
            return False
        setattr(post, field, value)

    db.flush()
    db.refresh(post)
    logger.info("Updated %s for post %s", field, post_id)
    return True


def update_title_by_id(db: Session, post_id: int, title: str) -> bool:
    return update_post_field(db, post_id, "title", title)


def update_content_by_id(db: Session, post_id: int, content: str) -> bool:
    return update_post_field(db, post_id, "content", content)


def change_is_published_by_id(db: Session, post_id: int, is_published: bool) -> bool:
    return update_post_field(db, post_id, "is_published", is_published)
