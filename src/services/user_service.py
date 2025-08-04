# services/user_service.py
import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.exceptions import ConflictError, NotFoundError, ValidationError
from core.security import get_password_hash
from db.repositories import user_repository
from schemas.responses import PaginatedResponse, PaginationMeta, SuccessResponse
from schemas.users import (
    UserCreate,
    UserOut,
    UserQuery,
    UserReplace,
    UserUpdate,
)

logger = logging.getLogger(__name__)


def get_user_by_id(db: Session, user_id: int) -> SuccessResponse[UserOut]:
    """Get single user by id."""
    user = user_repository.get_user_by_id(db, user_id)
    if user is None:
        logger.info("User %s not found", user_id)
        raise NotFoundError(f"User with id {user_id} not found")
    return SuccessResponse[UserOut].ok(UserOut.model_validate(user))


def list_users(
    db: Session,
    page: int = 1,
    limit: int = 10,
    query: Optional[UserQuery] = None,
) -> PaginatedResponse[UserOut]:
    """List users with pagination and optional exact filters."""
    if page < 1:
        raise ValidationError("page must be >= 1")
    if limit < 1:
        raise ValidationError("limit must be >= 1")

    q_username = query.username if query else None
    q_email = query.email if query else None

    offset = (page - 1) * limit
    items_orm = list(
        user_repository.get_users_paginated(
            db=db, offset=offset, limit=limit, username=q_username, email=q_email
        )
    )
    total = user_repository.count_users(db=db, username=q_username, email=q_email)

    items = [UserOut.model_validate(u) for u in items_orm]
    total_pages = max(1, (total + limit - 1) // limit)
    pagination = PaginationMeta(
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )
    return PaginatedResponse[UserOut].ok(items=items, pagination=pagination)


def create_user(db: Session, user_data: UserCreate) -> SuccessResponse[UserOut]:
    """Create new user with uniqueness checks and password hashing."""
    try:
        if user_repository.get_user_by_username(db, user_data.username):
            logger.warning("Username '%s' already exists", user_data.username)
            raise ConflictError("Username already registered")

        if user_repository.get_user_by_email(db, user_data.email):
            logger.warning("Email '%s' already exists", user_data.email)
            raise ConflictError("Email already registered")

        hashed_password = get_password_hash(user_data.password)

        db_user = user_repository.create_user(
            db=db,
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
        )

        return SuccessResponse[UserOut].ok(UserOut.model_validate(db_user))

    except HTTPException:
        raise

    except ConflictError:
        raise

    except Exception as e:
        logger.error("Unexpected error while creating user: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


def _ensure_unique_on_change(
    db: Session,
    *,
    user_id: int,
    new_username: Optional[str],
    new_email: Optional[str],
) -> None:
    """Ensure username/email uniqueness if changed for a specific user."""
    if new_username is not None:
        existing = user_repository.get_user_by_username(db, new_username)
        if existing is not None and int(getattr(existing, "id")) != user_id:
            raise ConflictError("Username already registered")
    if new_email is not None:
        existing = user_repository.get_user_by_email(db, new_email)
        if existing is not None and int(getattr(existing, "id")) != user_id:
            raise ConflictError("Email already registered")


def update_user_patch(
    db: Session, user_id: int, patch: UserUpdate
) -> SuccessResponse[UserOut]:
    """Partially update user. Hash password if provided; enforce uniqueness."""
    user = user_repository.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError(f"User with id {user_id} not found")

    new_username = patch.username if patch.username is not None else None
    new_email = patch.email if patch.email is not None else None
    _ensure_unique_on_change(
        db, user_id=user_id, new_username=new_username, new_email=new_email
    )

    hashed_password: Optional[str] = None
    if patch.password is not None:
        hashed_password = get_password_hash(patch.password)

    updated = user_repository.update_user_partial(
        db=db,
        user_id=user_id,
        username=new_username,
        email=new_email,
        hashed_password=hashed_password,
    )
    if not updated:
        raise NotFoundError(f"User with id {user_id} not found after update")

    return SuccessResponse[UserOut].ok(UserOut.model_validate(updated))


def replace_user_put(
    db: Session, user_id: int, payload: UserReplace
) -> SuccessResponse[UserOut]:
    """Full replacement update (PUT)."""
    user = user_repository.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError(f"User with id {user_id} not found")

    _ensure_unique_on_change(
        db, user_id=user_id, new_username=payload.username, new_email=payload.email
    )

    hashed_password = get_password_hash(payload.password)

    replaced = user_repository.replace_user(
        db=db,
        user_id=user_id,
        username=payload.username,
        email=payload.email,
        hashed_password=hashed_password,
    )
    if not replaced:
        raise NotFoundError(f"User with id {user_id} not found after replace")

    return SuccessResponse[UserOut].ok(UserOut.model_validate(replaced))


def delete_user(db: Session, user_id: int) -> SuccessResponse[str]:
    """Delete user by id."""
    user = user_repository.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError(f"User with id {user_id} not found")
    deleted = user_repository.delete_user(db=db, user_id=user_id)
    if not deleted:
        raise NotFoundError(f"User with id {user_id} not found")
    return SuccessResponse[str].ok("User deleted")
