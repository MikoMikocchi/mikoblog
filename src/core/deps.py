from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from db.database import get_db
from db.repositories.user_repository import get_user_by_id
from core.jwt import decode_token, validate_typ

# HTTP Bearer scheme (no auto_error to control 401 shape)
bearer_scheme = HTTPBearer(auto_error=False)


def _extract_bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    """Extract Bearer token from Authorization header or raise 401."""
    if (
        credentials is None
        or not credentials.scheme
        or credentials.scheme.lower() != "bearer"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
):
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(user=Depends(get_current_user)):
    """Require admin role. Returns user if role == 'admin' else 403."""
    role = getattr(user, "role", "user")
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user
