from datetime import datetime
from typing import Any, TypeVar

from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

# Type variable for generic responses
T = TypeVar("T")


class BaseResponse(BaseModel):
    """Base response schema with common fields."""

    success: bool = Field(..., description="Whether the operation was successful")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

    model_config = {"ser_json_timedelta": "float"}


class SuccessResponse[T](BaseResponse, GenericModel):
    """Generic success response with typed data."""

    data: T = Field(..., description="Response data")
    message: str | None = Field(None, description="Optional success message")

    @classmethod
    def ok(cls, data: T, message: str | None = None) -> "SuccessResponse[T]":
        """Convenience constructor to avoid payload dicts."""
        return cls.model_validate({"success": True, "data": data, "message": message})


class ErrorResponse(BaseResponse):
    """Error response schema."""

    error: dict[str, Any] = Field(..., description="Error details")
    message: str = Field(..., description="Error message")


class ValidationErrorResponse(ErrorResponse):
    """Validation error response schema."""

    error: dict[str, Any] = Field(..., description="Validation error details with field-specific errors")


class PaginationMeta(BaseModel):
    """Pagination metadata schema."""

    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=1, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse[T](BaseResponse, GenericModel):
    """Generic paginated response."""

    data: list[T] = Field(..., description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    message: str | None = Field(None, description="Optional message")

    @classmethod
    def ok(
        cls,
        items: list[T],
        pagination: PaginationMeta,
        message: str | None = None,
    ) -> "PaginatedResponse[T]":
        """Convenience constructor to avoid payload dicts."""
        return cls.model_validate(
            {
                "success": True,
                "data": items,
                "pagination": pagination,
                "message": message,
            }
        )


class TokenResponse(BaseResponse):
    """JWT token response schema."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: dict[str, Any] = Field(..., description="Authenticated user information")


class MessageResponse(BaseResponse):
    """Simple message response schema."""

    message: str = Field(..., description="Response message")


class HealthCheckResponse(BaseResponse):
    """Health check response schema."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    database: dict[str, Any] = Field(..., description="Database status")
    uptime: str = Field(..., description="Service uptime")


class StatisticsResponse(BaseResponse):
    """Statistics response schema."""

    statistics: dict[str, int | float | str] = Field(..., description="Statistics data")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Statistics generation time")


# Specific response types for common use cases
class UserResponse(SuccessResponse[Any]):
    """User-specific response schema."""

    pass


class PostResponse(SuccessResponse[Any]):
    """Post-specific response schema."""

    pass


class UserListResponse(PaginatedResponse[Any]):
    """User list response schema."""

    pass


class PostListResponse(PaginatedResponse[Any]):
    """Post list response schema."""

    pass
