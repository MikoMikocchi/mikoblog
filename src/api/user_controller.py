# api/user_controller.py
from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from db.database import get_db
from schemas.responses import PaginatedResponse, SuccessResponse
from schemas.users import (
    UserCreate,
    UserOut,
    UserQuery,
    UserReplace,
    UserUpdate,
)
from services import user_service

users_router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@users_router.get(
    "",
    response_model=PaginatedResponse[UserOut],
    summary="List users",
    description="Get a paginated list of users ordered by id ASC with optional exact filters.",
    response_model_exclude_none=True,
)
async def list_users(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    limit: int = Query(10, ge=1, le=100, description="Page size (1..100)"),
    username: str | None = Query(None, description="Exact username filter"),
    email: str | None = Query(None, description="Exact email filter"),
):
    query = UserQuery(username=username, email=email)
    return user_service.list_users(db=db, page=page, limit=limit, query=query)


@users_router.get(
    "/{user_id}",
    response_model=SuccessResponse[UserOut],
    summary="Get user by ID",
    description="Fetch a single user by ID.",
    response_model_exclude_none=True,
)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    return user_service.get_user_by_id(db=db, user_id=user_id)


@users_router.post(
    "",
    response_model=SuccessResponse[UserOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Register a new user with a unique username, email, and strong password.",
    response_model_exclude_none=True,
)
async def create_user(user_data: UserCreate = Body(...), db: Session = Depends(get_db)):
    return user_service.create_user(db=db, user_data=user_data)


@users_router.patch(
    "/{user_id}",
    response_model=SuccessResponse[UserOut],
    summary="Partially update user",
    description="Update one or several fields for a user. Enforces uniqueness and hashes password.",
    response_model_exclude_none=True,
)
async def update_user_patch(
    user_id: int, patch: UserUpdate = Body(...), db: Session = Depends(get_db)
):
    return user_service.update_user_patch(db=db, user_id=user_id, patch=patch)


@users_router.put(
    "/{user_id}",
    response_model=SuccessResponse[UserOut],
    summary="Replace user (PUT)",
    description="Full replacement of user fields. Enforces uniqueness and hashes password.",
    response_model_exclude_none=True,
)
async def replace_user(
    user_id: int, payload: UserReplace = Body(...), db: Session = Depends(get_db)
):
    return user_service.replace_user_put(db=db, user_id=user_id, payload=payload)


@users_router.delete(
    "/{user_id}",
    response_model=SuccessResponse[str],
    summary="Delete user",
    description="Delete a user by ID. Returns a confirmation message.",
)
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    return user_service.delete_user(db=db, user_id=user_id)
