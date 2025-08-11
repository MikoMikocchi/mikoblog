from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import require_admin
from db.database import get_db
from db.models.user import User
from schemas.responses import PaginatedResponse, SuccessResponse
from schemas.users import UserCreate, UserOut, UserQuery, UserReplace, UserUpdate
from services import user_service

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "",
    response_model=PaginatedResponse[UserOut],
    summary="List users",
    description="Get a paginated list of users ordered by id ASC with optional exact filters.",
    response_model_exclude_none=True,
)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    limit: int = Query(10, ge=1, le=100, description="Page size (1..100)"),
    username: str | None = Query(None, description="Exact username filter"),
    email: str | None = Query(None, description="Exact email filter"),
) -> PaginatedResponse[UserOut]:
    query = UserQuery(username=username, email=email)
    return await user_service.list_users(db=db, page=page, limit=limit, query=query)


@router.get(
    "/{user_id}",
    response_model=SuccessResponse[UserOut],
    summary="Get user by ID",
    description="Fetch a single user by ID.",
    response_model_exclude_none=True,
)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]) -> SuccessResponse[UserOut]:
    return await user_service.get_user_by_id(db=db, user_id=user_id)


@router.post(
    "",
    response_model=SuccessResponse[UserOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Register a new user with a unique username, email, and strong password.",
    response_model_exclude_none=True,
)
async def create_user(
    user_data: Annotated[UserCreate, Body(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[UserOut]:
    return await user_service.create_user(db=db, user_data=user_data)


@router.patch(
    "/{user_id}",
    response_model=SuccessResponse[UserOut],
    summary="Partially update user",
    description="Update one or several fields for a user.",
    response_model_exclude_none=True,
)
async def update_user_patch(
    user_id: int,
    patch: Annotated[UserUpdate, Body(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
) -> SuccessResponse[UserOut]:
    return await user_service.update_user_patch(db=db, user_id=user_id, patch=patch)


@router.put(
    "/{user_id}",
    response_model=SuccessResponse[UserOut],
    summary="Replace user (PUT)",
    description="Full replacement of user fields.",
    response_model_exclude_none=True,
)
async def replace_user(
    user_id: int,
    payload: Annotated[UserReplace, Body(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
) -> SuccessResponse[UserOut]:
    return await user_service.replace_user_put(db=db, user_id=user_id, payload=payload)


@router.delete(
    "/{user_id}",
    response_model=SuccessResponse[str],
    summary="Delete user",
    description="Delete a user by ID. Returns a confirmation message. Admin only.",
)
async def delete_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
) -> SuccessResponse[str]:
    return await user_service.delete_user(db=db, user_id=user_id)
