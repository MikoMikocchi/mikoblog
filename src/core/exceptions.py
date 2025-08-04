from fastapi import HTTPException, status


class BlogException(Exception):
    def __init__(self, message: str):
        super().__init__(message)

    def __str__(self):
        return self.args[0]


class ValidationError(BlogException):
    def __init__(self, message="Validation failed"):
        super().__init__(message)


class NotFoundError(BlogException):
    def __init__(self, message="Resource not found"):
        super().__init__(message)


class ConflictError(BlogException):
    def __init__(self, message="Resource already exists"):
        super().__init__(message)


class AuthenticationError(BlogException):
    def __init__(self, message="Authentication required"):
        super().__init__(message)


class AuthorizationError(BlogException):
    def __init__(self, message="Insufficient permissions"):
        super().__init__(message)


class DatabaseError(BlogException):
    def __init__(self, message="Database operation failed"):
        super().__init__(message)


class HTTPNotFoundError(HTTPException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class HTTPConflictError(HTTPException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class HTTPValidationError(HTTPException):
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )


class HTTPAuthenticationError(HTTPException):
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class HTTPAuthorizationError(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class HTTPInternalServerError(HTTPException):
    def __init__(self, detail: str = "Internal server error"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )


def map_exception_to_http(exc: BlogException) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPNotFoundError(str(exc))
    elif isinstance(exc, ConflictError):
        return HTTPConflictError(str(exc))
    elif isinstance(exc, ValidationError):
        return HTTPValidationError(str(exc))
    elif isinstance(exc, AuthenticationError):
        return HTTPAuthenticationError(str(exc))
    elif isinstance(exc, AuthorizationError):
        return HTTPAuthorizationError(str(exc))
    elif isinstance(exc, DatabaseError):
        return HTTPInternalServerError(str(exc))
    else:
        return HTTPInternalServerError("An unexpected error occurred")
