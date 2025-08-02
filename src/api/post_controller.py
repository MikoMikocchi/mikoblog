# api/post_controller.py
from fastapi import Body, Depends, Form, status, APIRouter
from sqlalchemy.orm import Session

import schemas.posts as posts
import services.post_service
from db.database import get_db
from schemas.responses import APIResponse

posts_router = APIRouter(prefix="/posts", tags=["Posts"])


@posts_router.get("", response_model=APIResponse)
async def get_all_posts(db: Session = Depends(get_db), page: int = 1, limit: int = 10):
    return services.post_service.get_all_posts(db=db, page=page, limit=limit)


@posts_router.get("/{post_id}", response_model=APIResponse)
async def get_post(post_id: int, db: Session = Depends(get_db)):
    return services.post_service.get_post_by_id(db=db, post_id=post_id)


@posts_router.post(
    "",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(
    db: Session = Depends(get_db), post_data: posts.PostCreate = Body(...)
):
    return services.post_service.create_post(db=db, post_data=post_data)


@posts_router.patch("/{post_id}/title", response_model=APIResponse)
async def update_title(
    post_id: int,
    db: Session = Depends(get_db),
    title: str = Form(...),
):
    return services.post_service.update_title(db=db, post_id=post_id, title=title)


@posts_router.patch("/{post_id}/content", response_model=APIResponse)
async def update_content(
    post_id: int,
    db: Session = Depends(get_db),
    content: str = Form(...),
):
    return services.post_service.update_content(db=db, post_id=post_id, content=content)


@posts_router.delete("/{post_id}", response_model=APIResponse)
async def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
):
    return services.post_service.delete_post(db=db, post_id=post_id)
