from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status


@dataclass(eq=False)
class BlogException(Exception):
    message: str
    code: str = "error"
    details: dict | None = None

    def __str__(self) -> str:
        return self.message


class ValidationError(BlogException):
    code = "validation_error"


class AuthenticationError(BlogException):
    code = "authentication_error"


class AuthorizationError(BlogException):
    code = "authorization_error"


class NotFoundError(BlogException):
    code = "not_found"


class ConflictError(BlogException):
    code = "conflict"


class RateLimitError(BlogException):
    code = "rate_limited"


class DatabaseError(BlogException):
    code = "database_error"


EXC_TO_STATUS: dict[type[BlogException], int] = {
    ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AuthorizationError: status.HTTP_403_FORBIDDEN,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
    DatabaseError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def map_exception_to_http(exc: BlogException) -> HTTPException:
    status_code = status.HTTP_400_BAD_REQUEST
    for typ, st in EXC_TO_STATUS.items():
        if isinstance(exc, typ):
            status_code = st
            break

    headers = None
    if isinstance(exc, AuthenticationError):
        headers = {"WWW-Authenticate": "Bearer"}

    return HTTPException(status_code=status_code, detail=exc.message, headers=headers or {})
