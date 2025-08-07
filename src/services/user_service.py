import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BlogException, ConflictError, NotFoundError, ValidationError
from core.security import get_password_hash
from db.repositories import user_repository
from schemas.responses import PaginatedResponse, PaginationMeta, SuccessResponse
from schemas.users import UserCreate, UserOut, UserQuery, UserReplace, UserUpdate

logger = logging.getLogger(__name__)


async def get_user_by_id(db: AsyncSession, user_id: int) -> SuccessResponse[UserOut]:
    """Get a single user by ID."""
    user = await user_repository.get_user_by_id(db, user_id)
    if user is None:
        logger.info("User %s not found", user_id)
        raise NotFoundError(f"User with id {user_id} not found")
    return SuccessResponse[UserOut].ok(UserOut.model_validate(user))


async def list_users(
    db: AsyncSession,
    page: int = 1,
    limit: int = 10,
    query: UserQuery | None = None,
) -> PaginatedResponse[UserOut]:
    """List users with pagination and optional exact filters."""
    if page < 1:
        raise ValidationError("page must be >= 1")
    if limit < 1:
        raise ValidationError("limit must be >= 1")

    q_username = query.username if query else None
    q_email = query.email if query else None

    offset = (page - 1) * limit
    items_orm = list(await user_repository.get_users_paginated(db=db, offset=offset, limit=limit, username=q_username, email=q_email))
    total = await user_repository.count_users(db=db, username=q_username, email=q_email)

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


async def create_user(db: AsyncSession, user_data: UserCreate) -> SuccessResponse[UserOut]:
    """Create new user with uniqueness checks and password hashing."""
    try:
        if await user_repository.get_user_by_username(db, user_data.username):
            logger.warning("Username '%s' already exists", user_data.username)
            raise ConflictError("Username already registered")

        if await user_repository.get_user_by_email(db, user_data.email):
            logger.warning("Email '%s' already exists", user_data.email)
            raise ConflictError("Email already registered")

        hashed_password = get_password_hash(user_data.password)

        try:
            db_user = await user_repository.create_user(
                db=db,
                username=user_data.username,
                email=user_data.email,
                hashed_password=hashed_password,
            )
            await db.commit()
        except IntegrityError as ie:
            await db.rollback()
            logger.warning("IntegrityError on user create (username/email uniqueness): %s", ie)
            raise ConflictError("Username or email already registered") from ie

        return SuccessResponse[UserOut].ok(UserOut.model_validate(db_user))

    except BlogException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Unexpected error while creating user: %s", e)
        raise ValidationError("Unexpected error while creating user") from e


async def _ensure_unique_on_change(
    db: AsyncSession,
    *,
    user_id: int,
    new_username: str | None,
    new_email: str | None,
) -> None:
    """Ensure username/email uniqueness if changed for a specific user."""
    if new_username is not None:
        existing = await user_repository.get_user_by_username(db, new_username)
        if existing is not None and int(getattr(existing, "id", 0)) != int(user_id):
            raise ConflictError("Username already registered")
    if new_email is not None:
        existing = await user_repository.get_user_by_email(db, new_email)
        if existing is not None and int(getattr(existing, "id", 0)) != int(user_id):
            raise ConflictError("Email already registered")


async def update_user_patch(db: AsyncSession, user_id: int, patch: UserUpdate) -> SuccessResponse[UserOut]:
    """Partially update a user. Hash password if provided; enforce uniqueness."""
    user = await user_repository.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError(f"User with id {user_id} not found")

    new_username = patch.username if patch.username is not None else None
    new_email = patch.email if patch.email is not None else None
    await _ensure_unique_on_change(db, user_id=user_id, new_username=new_username, new_email=new_email)

    hashed_password: str | None = None
    if patch.password is not None:
        hashed_password = get_password_hash(patch.password)

    updated = await user_repository.update_user_partial(
        db=db,
        user_id=user_id,
        username=new_username,
        email=new_email,
        hashed_password=hashed_password,
    )
    if not updated:
        raise NotFoundError(f"User with id {user_id} not found after update")

    await db.commit()
    return SuccessResponse[UserOut].ok(UserOut.model_validate(updated))


async def replace_user_put(db: AsyncSession, user_id: int, payload: UserReplace) -> SuccessResponse[UserOut]:
    """Full replacement update (PUT)."""
    user = await user_repository.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError(f"User with id {user_id} not found")

    await _ensure_unique_on_change(db, user_id=user_id, new_username=payload.username, new_email=payload.email)

    hashed_password = get_password_hash(payload.password)

    replaced = await user_repository.replace_user(
        db=db,
        user_id=user_id,
        username=payload.username,
        email=payload.email,
        hashed_password=hashed_password,
    )
    if not replaced:
        raise NotFoundError(f"User with id {user_id} not found after replace")

    await db.commit()
    return SuccessResponse[UserOut].ok(UserOut.model_validate(replaced))


async def delete_user(db: AsyncSession, user_id: int) -> SuccessResponse[str]:
    """Delete a user by ID."""
    user = await user_repository.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError(f"User with id {user_id} not found")
    deleted = await user_repository.delete_user(db=db, user_id=user_id)
    if not deleted:
        raise NotFoundError(f"User with id {user_id} not found")
    await db.commit()
    return SuccessResponse[str].ok("User deleted")
