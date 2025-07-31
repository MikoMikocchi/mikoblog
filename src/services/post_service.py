from sqlalchemy.orm import Session
from schemas.responses import APIResponse
import schemas.posts
import db.repositories.post_repository as post_repository
from fastapi import HTTPException, status


def get_all_posts(db: Session, page: int = 1, limit: int = 10):
    skip = (page - 1) * limit
    posts = post_repository.get_posts_paginated(db, skip=skip, limit=limit)
    total = post_repository.count_posts(db)

    return APIResponse(
        status="success",
        content={
            "posts": [
                schemas.posts.PostOut.model_validate(p).model_dump() for p in posts
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit,
            },
        },
    )


def get_post_by_id(db: Session, post_id: int):
    post = post_repository.get_post_by_id(db, post_id)
    if post:
        return APIResponse(
            status="success",
            content=schemas.posts.PostOut.model_validate(post).model_dump(),
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id {post_id} not found",
        )


def create_post(db: Session, new_post: schemas.posts.PostBase):
    post = post_repository.create_post(
        db=db,
        title=new_post.title,
        content=new_post.content,
        is_published=new_post.is_published,
    )
    if post:
        return APIResponse(
            status="success",
            content=schemas.posts.PostOut.model_validate(post).model_dump(),
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create post",
        )


def update_title(db: Session, post_id: int, title: str):
    result = post_repository.update_title_by_id(db=db, post_id=post_id, title=title)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update title",
        )

    updated_post = post_repository.get_post_by_id(db, post_id)
    if not updated_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found after update"
        )

    return APIResponse(
        status="success",
        content=schemas.posts.PostOut.model_validate(updated_post).model_dump(),
    )


def update_content(db: Session, post_id: int, content: str):
    result = post_repository.update_content_by_id(
        db=db, post_id=post_id, content=content
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update content",
        )

    updated_post = post_repository.get_post_by_id(db, post_id)
    if not updated_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found after update"
        )

    return APIResponse(
        status="success",
        content=schemas.posts.PostOut.model_validate(updated_post).model_dump(),
    )


def delete_post(db: Session, post_id: int):
    result = post_repository.delete_post_by_id(db=db, post_id=post_id)
    if result:
        return APIResponse(status="success", content="Post deleted")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete post",
        )
