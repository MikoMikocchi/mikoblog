import logging
from typing import List

from fastapi import HTTPException, Path

from db.models.post import Post
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def create_post(
    db: Session, title: str, content: str, is_published: bool = True
) -> Post:
    try:
        new_post = Post(
            title=title,
            content=content,
            is_published=is_published,
        )
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        logger.info(f"Created new post with id {new_post.id}")
        return new_post
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error while creating post: {e}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error while creating post: {e}")
        raise


def get_all_posts(db: Session) -> List[Post]:
    try:
        posts = db.query(Post).order_by(Post.id).all()
        return posts or []
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching all posts: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while fetching all posts: {e}")
        raise


def count_posts(db: Session):
    return db.query(Post).count()


def get_existing_post(db: Session, post_id: int = Path(gt=0)) -> Post:
    post = get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


def get_post_by_id(db: Session, post_id: int) -> Post:
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            logger.warning(f"Post with id {post_id} not found")
            raise ValueError(f"Post with id {post_id} not found")
        return post
    except ValueError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching post {post_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while fetching post {post_id}: {e}")
        raise


def get_posts_paginated(db: Session, offset: int, limit: int) -> List[Post]:
    try:
        posts = db.query(Post).offset(offset).limit(limit).all()
        return posts or []
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching paginated posts: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while fetching paginated posts: {e}")
        raise


def delete_post_by_id(db: Session, post_id: int) -> bool:
    try:
        post = get_post_by_id(db, post_id)
        db.delete(post)
        db.commit()
        logger.info(f"Deleted post with id {post_id}")
        return True
    except ValueError:
        return False
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error while deleting post {post_id}: {e}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error while deleting post {post_id}: {e}")
        raise


def update_post_field(db: Session, post_id: int, field: str, value) -> bool:
    try:
        post = get_post_by_id(db, post_id)
        setattr(post, field, value)
        db.commit()
        db.refresh(post)
        logger.info(f"Updated {field} for post {post_id}")
        return True
    except ValueError:
        return False
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error while updating {field} for post {post_id}: {e}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error while updating {field} for post {post_id}: {e}")
        raise


def update_title_by_id(db: Session, post_id: int, title: str) -> bool:
    return update_post_field(db, post_id, "title", title)


def update_content_by_id(db: Session, post_id: int, content: str) -> bool:
    return update_post_field(db, post_id, "content", content)


def change_is_published_by_id(db: Session, post_id: int, is_published: bool) -> bool:
    return update_post_field(db, post_id, "is_published", is_published)
