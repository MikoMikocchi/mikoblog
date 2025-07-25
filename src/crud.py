import logging
from typing import Union
from models import Post
from sqlalchemy.orm import Session


def create_post(
    db: Session, title: str, content: str, is_published: bool = True
) -> Union[Post, None]:

    try:
        new_post = Post(title=title, content=content, is_published=is_published)
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        return new_post
    except Exception as e:
        logging.error(f"Error was occured while creating new post: {e}")

    return None


def get_all_posts(db: Session) -> Union[list[Post], None]:
    try:
        all_posts = db.query(Post).order_by(Post.id).all()
        return all_posts
    except Exception as e:
        logging.error(f"Error was occured while fetching posts: {e}")

    return None


def get_post_by_id(db: Session, post_id: int) -> Post:
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise ValueError("Post not found")
        return post
    except Exception as e:
        logging.error(f"Error fetching post by id {post_id}: {e}")
        raise e


def delete_post_by_id(db: Session, post_id: int) -> bool:
    try:
        post = get_post_by_id(db, post_id)

        if post is not None:
            db.delete(post)
            db.commit()

            return True
    except Exception as e:
        logging.error(f"Error was occured while deleting post by id {post_id}: {e}")

    return False


def update_title_by_id(db: Session, post_id: int, title: str) -> bool:
    try:
        post = get_post_by_id(db, post_id)

        if post is not None:
            post.title = title
            db.commit()

            return True
    except Exception as e:
        logging.error(
            f"Error was occured while updating post's title by id {post_id}: {e}"
        )

    return False


def update_content_by_id(db: Session, post_id: int, content: str) -> bool:
    try:
        post = get_post_by_id(db, post_id)

        if post is not None:
            post.content = content
            db.commit()

            return True
    except Exception as e:
        logging.error(
            f"Error was occured while updating post's content by id {post_id}: {e}"
        )

    return False


def change_is_published_by_id(db: Session, post_id: int, is_published: bool) -> bool:
    try:
        post = get_post_by_id(db, post_id)

        if post is not None:
            post.is_published = is_published
            db.commit()

            return is_published
    except Exception as e:
        logging.error(
            f"Error was occured while updating post's content by id {post_id}: {e}"
        )

    return False
