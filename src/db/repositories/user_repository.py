import logging
from typing import Any, cast

from sqlalchemy import and_, select, text as _sql_text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.user import User
from db.repositories.decorators import handle_db_errors, with_retry

logger = logging.getLogger(__name__)


@with_retry(log_prefix="fetching user")
async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Return a user by primary key."""
    return await db.get(User, user_id)


@with_retry(log_prefix="fetching user by username")
async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Return a user by exact username."""
    stmt = select(User).where(User.username == username)
    res = await db.execute(stmt)
    return res.scalars().first()


@with_retry(log_prefix="fetching user by email")
async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Return a user by exact email."""
    stmt = select(User).where(User.email == email)
    res = await db.execute(stmt)
    return res.scalars().first()


@with_retry(log_prefix="counting users")
async def count_users(db: AsyncSession, username: str | None = None, email: str | None = None) -> int:
    """Count users with optional exact filters."""
    from sqlalchemy import func

    conditions: list[Any] = []
    if username is not None:
        conditions.append(User.username == username)
    if email is not None:
        conditions.append(User.email == email)

    stmt = select(func.count(User.id))
    if conditions:
        stmt = stmt.where(and_(*conditions))

    res = await db.execute(stmt)
    return cast(int, res.scalar_one())


@with_retry(log_prefix="listing users")
async def get_users_paginated(
    db: AsyncSession,
    offset: int,
    limit: int,
    username: str | None = None,
    email: str | None = None,
) -> list[User]:
    """Return users page with optional exact filters, ordered by id ASC."""
    conditions: list[Any] = []
    if username is not None:
        conditions.append(User.username == username)
    if email is not None:
        conditions.append(User.email == email)

    stmt = select(User).order_by(User.id.asc()).offset(offset).limit(limit)
    if conditions:
        stmt = stmt.where(and_(*conditions))

    res = await db.execute(stmt)
    return list(res.scalars().all())


@handle_db_errors(entity_name="user")
async def create_user(db: AsyncSession, username: str, email: str, hashed_password: str) -> User:
    """Create new user using async SQL with NOWAIT preflight and ON CONFLICT DO NOTHING RETURNING id."""
    # Reasonable local timeouts
    try:
        await db.execute(_sql_text("SET LOCAL lock_timeout = '1500ms'"))
        await db.execute(_sql_text("SET LOCAL statement_timeout = '2500ms'"))
    except Exception:
        pass

    # Preflight with NOWAIT to avoid waiting on locked rows
    preflight_sql = _sql_text(
        """
        SELECT 1
        FROM users
        WHERE username = :username OR email = :email
        FOR KEY SHARE NOWAIT
        LIMIT 1
        """
    )
    pre = (await db.execute(preflight_sql, {"username": username, "email": email})).first()
    if pre is not None:
        raise IntegrityError(
            "duplicate username/email",
            params={},
            orig=Exception("unique conflict"),
        )

    insert_sql = _sql_text(
        """
        INSERT INTO users (username, email, hashed_password, created_at, updated_at, role)
        VALUES (:username, :email, :hashed_password, NOW(), NOW(), 'user')
        ON CONFLICT DO NOTHING
        RETURNING id
        """
    )
    row = (
        await db.execute(
            insert_sql,
            {
                "username": username,
                "email": email,
                "hashed_password": hashed_password,
            },
        )
    ).fetchone()
    if row is None:
        raise IntegrityError(
            "duplicate username/email",
            params={},
            orig=Exception("unique conflict"),
        )

    pk = int(row[0])
    created = await db.get(User, pk)
    if created is None:
        raise SQLAlchemyError("inserted row not found after RETURNING")
    logger.info("Created new user with id %s, username='%s'", pk, username)
    return created


@handle_db_errors(entity_name="user")
async def update_user_partial(
    db: AsyncSession,
    user_id: int,
    *,
    username: str | None = None,
    email: str | None = None,
    hashed_password: str | None = None,
) -> User | None:
    """Apply partial update (PATCH) to user."""
    user = await get_user_by_id(db, user_id)
    if not user:
        logger.info("Skip patch: user %s not found", user_id)
        return None

    u = cast(Any, user)
    if username is not None:
        object.__setattr__(u, "username", username)
    if email is not None:
        object.__setattr__(u, "email", email)
    if hashed_password is not None:
        object.__setattr__(u, "hashed_password", hashed_password)

    await db.flush()
    await db.refresh(user)
    logger.info("Patched user %s", user_id)
    return user


@handle_db_errors(entity_name="user")
async def replace_user(
    db: AsyncSession,
    user_id: int,
    *,
    username: str,
    email: str,
    hashed_password: str,
) -> User | None:
    """Replace user state (PUT). Returns None if user not found."""
    user = await get_user_by_id(db, user_id)
    if not user:
        logger.info("Skip replace: user %s not found", user_id)
        return None

    u = cast(Any, user)
    object.__setattr__(u, "username", username)
    object.__setattr__(u, "email", email)
    object.__setattr__(u, "hashed_password", hashed_password)

    await db.flush()
    await db.refresh(user)
    logger.info("Replaced user %s", user_id)
    return user


@handle_db_errors(entity_name="user")
async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """Delete user by id."""
    user = await get_user_by_id(db, user_id)
    if not user:
        logger.info("Skip delete: user %s not found", user_id)
        return False
    await db.delete(user)
    logger.info("Deleted user with id %s", user_id)
    return True
