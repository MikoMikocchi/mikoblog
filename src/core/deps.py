import logging
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AuthenticationError, AuthorizationError, DatabaseError
from core.jwt import decode_token, validate_typ
from db.database import get_db
from db.repositories.user_repository import get_user_by_id

logger = logging.getLogger(__name__)

# HTTP Bearer scheme (no auto_error to control 401 shape)
bearer_scheme = HTTPBearer(auto_error=False)


def _extract_bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    """Extract Bearer token from Authorization header or raise AuthenticationError."""
    if credentials is None or not credentials.scheme or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Missing or invalid Authorization header")
    token = credentials.credentials
    if not token:
        raise AuthenticationError("Missing bearer token")
    return token


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> object:
    """
    FastAPI dependency that:
    - Extracts Bearer access token
    - Decodes and validates signature/exp
    - Ensures typ=access
    - Loads user from DB and returns ORM User
    """
    token = _extract_bearer_token(credentials)
    decoded = decode_token(token)
    validate_typ(decoded, expected_typ="access")

    sub = decoded.get("sub")
    if not sub:
        raise AuthenticationError("Token is missing subject")

    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise AuthenticationError("Invalid subject") from None

    try:
        user = await get_user_by_id(db, user_id)
    except DatabaseError as e:
        logger.error("Database error while fetching user %s: %s", user_id, e)
        raise AuthenticationError("User not found") from e
    if user is None:
        raise AuthenticationError("User not found")
    return user


def require_admin(_auth: Annotated[object, Depends(get_current_user)]) -> object:
    """Require admin role. Returns user if role == 'admin' else AuthorizationError."""
    role = getattr(_auth, "role", "user")
    if role != "admin":
        raise AuthorizationError("Admin privileges required")
    return _auth
