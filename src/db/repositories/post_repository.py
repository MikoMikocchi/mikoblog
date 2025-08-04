import logging
from typing import List, Optional, Any

from db.models.post import Post
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from db.utils import transactional
from core.exceptions import ValidationError, NotFoundError, DatabaseError

logger = logging.getLogger(__name__)

DEFAULT_MAX_LIMIT = 100

ALLOWED_UPDATE_FIELDS = frozenset({"title", "content", "is_published"})


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
    # commit will be done by decorator
    db.flush()
    db.refresh(new_post)
    logger.info("Created new post with id %s", new_post.id)
    return new_post


def get_all_posts(db: Session) -> List[Post]:
    try:
        posts: List[Post] = db.query(Post).order_by(Post.id).all()
        return posts
    except SQLAlchemyError as e:
        logger.error("Database error while fetching all posts: %s", e)
        raise DatabaseError("Failed to fetch all posts")


def count_posts(db: Session) -> int:
    return db.query(Post).count()


def get_post_by_id(db: Session, post_id: int) -> Optional[Post]:
    if not isinstance(post_id, int) or post_id <= 0:
        logger.warning("Invalid post_id: %s (must be > 0)", post_id)
        return None
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            logger.info("Post with id %s not found", post_id)
        return post
    except SQLAlchemyError as e:
        logger.error("Database error while fetching post %s: %s", post_id, e)
        raise DatabaseError("Failed to fetch post")


def get_posts_paginated(db: Session, offset: int, limit: int) -> List[Post]:
    if not isinstance(offset, int) or offset < 0:
        raise ValidationError("offset must be an integer >= 0")
    if not isinstance(limit, int) or limit <= 0 or limit > DEFAULT_MAX_LIMIT:
        raise ValidationError(f"limit must be in 1..{DEFAULT_MAX_LIMIT}")

    try:
        posts: List[Post] = (
            db.query(Post).order_by(Post.id).offset(offset).limit(limit).all()
        )
        return posts
    except SQLAlchemyError as e:
        logger.error("Database error while fetching paginated posts: %s", e)
        raise DatabaseError("Failed to fetch paginated posts")


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
        raise DatabaseError("Failed to delete post")


@transactional
def update_post_field(db: Session, post_id: int, field: str, value: Any) -> bool:
    post = get_post_by_id(db, post_id)
    if not post:
        logger.info("Skip update: post %s not found", post_id)
        return False

    if field not in ALLOWED_UPDATE_FIELDS:
        logger.warning(
            "Attempt to update disallowed field '%s' for post %s", field, post_id
        )
        return False

    if field == "title" or field == "content":
        if not isinstance(value, str):
            logger.warning(
                "Invalid value type for '%s': expected str, got %s",
                field,
                type(value).__name__,
            )
            return False
    elif field == "is_published":
        if not isinstance(value, bool):
            logger.warning(
                "Invalid value type for '%s': expected bool, got %s",
                field,
                type(value).__name__,
            )
            return False

    setattr(post, field, value)
    # commit will be done by decorator
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
