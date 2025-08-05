# api/post_controller.py
from fastapi import Body, Depends, status, APIRouter, Query
from sqlalchemy.orm import Session

import schemas.posts as posts
import services.post_service
from db.database import get_db
from schemas.responses import SuccessResponse, PaginatedResponse
from schemas.posts import PostOut
from core.deps import get_current_user  # direct import for clarity and typing

posts_router = APIRouter(
    prefix="/posts",
    tags=["Posts"],
)


@posts_router.get(
    "",
    response_model=PaginatedResponse[PostOut],
    summary="List posts",
    description="Get a paginated list of posts ordered by ID with author preloaded.",
    response_model_exclude_none=True,
)
async def get_all_posts(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    limit: int = Query(10, ge=1, le=100, description="Page size (1..100)"),
):
    return services.post_service.get_all_posts(db=db, page=page, limit=limit)


@posts_router.get(
    "/{post_id}",
    response_model=SuccessResponse[PostOut],
    summary="Get post by ID",
    description="Fetch a single post by its identifier with the author included.",
    response_model_exclude_none=True,
)
async def get_post(post_id: int, db: Session = Depends(get_db)):
    return services.post_service.get_post_by_id(db=db, post_id=post_id)


@posts_router.post(
    "",
    response_model=SuccessResponse[PostOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create post",
    description="Create a new post with title, content, author and publication status.",
    response_model_exclude_none=True,
)
async def create_post(
    db: Session = Depends(get_db),
    post_data: posts.PostCreate = Body(...),
    current_user=Depends(get_current_user),  # auth required
):
    return services.post_service.create_post(
        db=db, post_data=post_data, current_user=current_user
    )


@posts_router.patch("/{post_id}/title", response_model=SuccessResponse[PostOut])
async def update_title(
    post_id: int,
    db: Session = Depends(get_db),
    payload: posts.PostTitleUpdate = Body(...),
    current_user=Depends(get_current_user),
):
    return services.post_service.update_title(
        db=db, post_id=post_id, title=payload.title, current_user=current_user
    )


@posts_router.patch("/{post_id}/content", response_model=SuccessResponse[PostOut])
async def update_content(
    post_id: int,
    db: Session = Depends(get_db),
    payload: posts.PostContentUpdate = Body(...),
    current_user=Depends(get_current_user),
):
    return services.post_service.update_content(
        db=db, post_id=post_id, content=payload.content, current_user=current_user
    )


@posts_router.delete(
    "/{post_id}",
    response_model=SuccessResponse[str],
    summary="Delete post",
    description="Delete a post by ID. Returns a confirmation message.",
)
async def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return services.post_service.delete_post(
        db=db, post_id=post_id, current_user=current_user
    )
