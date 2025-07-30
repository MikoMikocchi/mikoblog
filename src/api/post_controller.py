from fastapi import Depends, Form, status, APIRouter
from sqlalchemy.orm import Session

import schemas.posts as posts
import services.post_service
from db.database import get_db
from schemas.responses import APIResponse

posts_router = APIRouter(prefix="/posts")


@posts_router.get("", response_model=APIResponse)
async def get_all_posts(page: int = 1, limit: int = 10, db: Session = Depends(get_db)):
    return services.post_service.get_all_posts(page=page, limit=limit, db=db)


@posts_router.get("/{post_id}", response_model=APIResponse)
async def get_post(post_id: int, db: Session = Depends(get_db)):
    return services.post_service.get_post_by_id(post_id=post_id, db=db)


@posts_router.post(
    "/posts", response_model=APIResponse, status_code=status.HTTP_201_CREATED
)
async def create_post(new_post: posts.PostBase, db: Session = Depends(get_db)):
    return services.post_service.create_post(new_post=new_post, db=db)


@posts_router.patch("/posts/{post_id}/title", response_model=APIResponse)
async def update_title(
    post_id: int,
    title: str = Form(...),
    db: Session = Depends(get_db),
):
    return services.post_service.update_title(post_id=post_id, title=title, db=db)


@posts_router.patch("/posts/{post_id}/content", response_model=APIResponse)
async def update_content(
    post_id: int,
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    return services.post_service.update_content(post_id=post_id, content=content, db=db)


@posts_router.delete("/posts/{post_id}", response_model=APIResponse)
async def delete_post(post_id: int, db: Session = Depends(get_db)):
    return services.post_service.delete_post(post_id=post_id, db=db)
