from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import schemas.posts
import db.repositories.post_repository as post_repository
from schemas.responses import (
    SuccessResponse,
    PaginatedResponse,
    PaginationMeta,
)


def get_all_posts(
    db: Session, page: int = 1, limit: int = 10
) -> PaginatedResponse[schemas.posts.PostOut]:
    # Validate input to ensure consistent pagination contract
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="page must be >= 1",
        )
    if limit < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="limit must be >= 1",
        )

    offset = (page - 1) * limit
    posts = post_repository.get_posts_paginated(db=db, offset=offset, limit=limit)
    total = post_repository.count_posts(db)

    items = [schemas.posts.PostOut.model_validate(p).model_dump() for p in posts]
    total_pages = max(1, (total + limit - 1) // limit)
    pagination = PaginationMeta(
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )
    payload = {"success": True, "data": items, "pagination": pagination.model_dump()}
    return PaginatedResponse[schemas.posts.PostOut].model_validate(payload)


def get_post_by_id(db: Session, post_id: int) -> SuccessResponse[schemas.posts.PostOut]:
    post = post_repository.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id {post_id} not found",
        )
    payload = {
        "success": True,
        "data": schemas.posts.PostOut.model_validate(post).model_dump(),
    }
    return SuccessResponse[schemas.posts.PostOut].model_validate(payload)


def create_post(
    db: Session, post_data: schemas.posts.PostCreate
) -> SuccessResponse[schemas.posts.PostOut]:
    post = post_repository.create_post(
        db=db,
        title=post_data.title,
        content=post_data.content,
        is_published=post_data.is_published,
        author_id=post_data.author_id,
    )
    if not post:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create post",
        )
    payload = {
        "success": True,
        "data": schemas.posts.PostOut.model_validate(post).model_dump(),
    }
    return SuccessResponse[schemas.posts.PostOut].model_validate(payload)


def update_title(
    db: Session, post_id: int, title: str
) -> SuccessResponse[schemas.posts.PostOut]:
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

    payload = {
        "success": True,
        "data": schemas.posts.PostOut.model_validate(updated_post).model_dump(),
    }
    return SuccessResponse[schemas.posts.PostOut].model_validate(payload)


def update_content(
    db: Session, post_id: int, content: str
) -> SuccessResponse[schemas.posts.PostOut]:
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

    payload = {
        "success": True,
        "data": schemas.posts.PostOut.model_validate(updated_post).model_dump(),
    }
    return SuccessResponse[schemas.posts.PostOut].model_validate(payload)


def delete_post(db: Session, post_id: int) -> SuccessResponse[str]:
    result = post_repository.delete_post_by_id(db=db, post_id=post_id)
    if not result:
        # Return 404 when post was not found/deleted as per repository behavior
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    payload = {"success": True, "data": "Post deleted"}
    return SuccessResponse[str].model_validate(payload)
