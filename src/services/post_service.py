from fastapi import Depends, HTTPException, status, Form
from sqlalchemy.orm import Session

from schemas.responses import APIResponse
import schemas.posts
import db.repositories.post_repository as post_repository
from db.database import get_db


def get_all_posts(page: int = 1, limit: int = 10, db: Session = Depends(get_db)):
    skip = (page - 1) * limit
    posts = post_repository.get_posts_paginated(db, skip=skip, limit=limit)
    total = post_repository.count_posts(db=db)

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
            detail="Post with id {post_id} not found",
        )


def create_post(new_post: schemas.posts.PostBase, db: Session = Depends(get_db)):
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
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create post"
        )


def update_title(
    post_id: int,
    title: str = Form(...),
    db: Session = Depends(get_db),
):
    result = post_repository.update_title_by_id(db=db, post_id=post_id, title=title)
    if result:
        return APIResponse(status="success", content="Title updated")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update title"
        )


def update_content(
    post_id: int,
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    result = post_repository.update_content_by_id(
        db=db, post_id=post_id, content=content
    )
    if result:
        return APIResponse(status="success", content="Content updated")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update content"
        )


async def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
):
    result = post_repository.delete_post_by_id(db=db, post_id=post_id)
    if result:
        return APIResponse(status="success", content="Post deleted")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to delete post"
        )
