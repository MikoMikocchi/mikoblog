# api/post_controller.py
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user
from db.database import get_db
from db.models.user import User
import schemas.posts as posts
from schemas.responses import PaginatedResponse, SuccessResponse
from services import post_service

posts_router = APIRouter(prefix="/posts", tags=["Posts"])


@posts_router.get(
    "",
    response_model=PaginatedResponse[posts.PostOut],
    summary="List posts",
    description="Get a paginated list of posts ordered by ID with author preloaded.",
    response_model_exclude_none=True,
)
async def get_all_posts(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    limit: int = Query(10, ge=1, le=100, description="Page size (1..100)"),
) -> PaginatedResponse[posts.PostOut]:
    return await post_service.get_all_posts(db=db, page=page, limit=limit)


@posts_router.get(
    "/{post_id}",
    response_model=SuccessResponse[posts.PostOut],
    summary="Get post by ID",
    description="Fetch a single post by its identifier with the author included.",
    response_model_exclude_none=True,
)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]) -> SuccessResponse[posts.PostOut]:
    return await post_service.get_post_by_id(db=db, post_id=post_id)


@posts_router.post(
    "",
    response_model=SuccessResponse[posts.PostOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create post",
    description="Create a new post with title, content, author and publication status.",
    response_model_exclude_none=True,
)
async def create_post(
    db: Annotated[AsyncSession, Depends(get_db)],
    post_data: Annotated[posts.PostCreate, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[posts.PostOut]:
    return await post_service.create_post(db=db, post_data=post_data, current_user=current_user)


@posts_router.patch(
    "/{post_id}/title",
    response_model=SuccessResponse[posts.PostOut],
    summary="Update post title",
    description="Update only the title of a post.",
)
async def update_title(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: Annotated[posts.PostTitleUpdate, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[posts.PostOut]:
    return await post_service.update_title(db=db, post_id=post_id, title=payload.title, current_user=current_user)


@posts_router.patch(
    "/{post_id}/content",
    response_model=SuccessResponse[posts.PostOut],
    summary="Update post content",
    description="Update only the content of a post.",
)
async def update_content(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: Annotated[posts.PostContentUpdate, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[posts.PostOut]:
    return await post_service.update_content(db=db, post_id=post_id, content=payload.content, current_user=current_user)


@posts_router.delete(
    "/{post_id}",
    response_model=SuccessResponse[str],
    summary="Delete post",
    description="Delete a post by ID. Returns a confirmation message.",
)
async def delete_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[str]:
    return await post_service.delete_post(db=db, post_id=post_id, current_user=current_user)
