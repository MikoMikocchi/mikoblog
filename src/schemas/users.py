from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


USERNAME_PATTERN = r"^[a-zA-Z0-9_-]+$"
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 50
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128
RESERVED_USERNAMES = {"admin", "root", "system", "api", "test"}
PASSWORD_SPECIAL_CHARS = '!@#$%^&*(),.?":{}|<>'


def is_strong_password(password: str) -> bool:
    return (
        len(password) >= MIN_PASSWORD_LENGTH
        and any(c.isupper() for c in password)
        and any(c.islower() for c in password)
        and any(c.isdigit() for c in password)
        and any(c in PASSWORD_SPECIAL_CHARS for c in password)
    )


def validate_password(password: str) -> str:
    if not is_strong_password(password):
        raise ValueError(
            "Password must be at least 12 characters long and contain at least one uppercase letter, "
            "one lowercase letter, one digit, and one special character."
        )
    return password


def validate_username(username: str) -> str:
    if username.lower() in RESERVED_USERNAMES:
        raise ValueError("Username not allowed")
    return username


class UserBase(BaseModel):
    """Base constraints for user identity."""

    username: str = Field(
        ...,
        min_length=MIN_USERNAME_LENGTH,
        max_length=MAX_USERNAME_LENGTH,
        pattern=USERNAME_PATTERN,
        description="Username containing only letters, numbers, underscores, and hyphens",
    )
    email: EmailStr = Field(..., description="Valid email address")


class UserCreate(UserBase):
    """Payload to create a new user."""

    password: str = Field(
        ...,
        min_length=MIN_PASSWORD_LENGTH,
        max_length=MAX_PASSWORD_LENGTH,
        description="Password must meet complexity requirements",
    )

    @field_validator("password")
    def validate_password_strength(cls, v: str) -> str:
        return validate_password(v)

    @field_validator("username")
    def validate_reserved_usernames(cls, v: str) -> str:
        return validate_username(v)


class UserReplace(BaseModel):
    """Full replacement payload (PUT) with required fields."""

    username: str = Field(
        ...,
        min_length=MIN_USERNAME_LENGTH,
        max_length=MAX_USERNAME_LENGTH,
        pattern=USERNAME_PATTERN,
        description="New username",
    )
    email: EmailStr = Field(..., description="New email address")
    password: str = Field(
        ...,
        min_length=MIN_PASSWORD_LENGTH,
        max_length=MAX_PASSWORD_LENGTH,
        description="New password",
    )

    @field_validator("password")
    def validate_password_strength(cls, v: str) -> str:
        return validate_password(v)

    @field_validator("username")
    def validate_reserved_usernames(cls, v: str) -> str:
        return validate_username(v)


class UserQuery(BaseModel):
    """Query filters for listing users with exact matches."""

    username: Optional[str] = Field(
        None,
        min_length=MIN_USERNAME_LENGTH,
        max_length=MAX_USERNAME_LENGTH,
        pattern=USERNAME_PATTERN,
        description="Exact username filter",
    )
    email: Optional[EmailStr] = Field(None, description="Exact email filter")


class UserUpdate(BaseModel):
    """Partial update (PATCH)."""

    username: Optional[str] = Field(
        None,
        min_length=MIN_USERNAME_LENGTH,
        max_length=MAX_USERNAME_LENGTH,
        pattern=USERNAME_PATTERN,
        description="New username",
    )
    email: Optional[EmailStr] = Field(None, description="New email address")
    password: Optional[str] = Field(
        None,
        min_length=MIN_PASSWORD_LENGTH,
        max_length=MAX_PASSWORD_LENGTH,
        description="New password",
    )

    @field_validator("password")
    def validate_password_strength(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_password(v)

    @field_validator("username")
    def validate_reserved_usernames(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_username(v)


class UserOut(UserBase):
    """Response projection for user."""

    id: int = Field(..., description="User ID")
    role: str = Field(..., pattern="^(user|admin)$", description="User role")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    username_or_email: str = Field(
        ..., min_length=3, max_length=100, description="Username or email address"
    )
    password: str = Field(
        ..., min_length=1, max_length=MAX_PASSWORD_LENGTH, description="User password"
    )


class UserPasswordChange(BaseModel):
    current_password: str = Field(
        ...,
        min_length=1,
        max_length=MAX_PASSWORD_LENGTH,
        description="Current password",
    )
    new_password: str = Field(
        ...,
        min_length=MIN_PASSWORD_LENGTH,
        max_length=MAX_PASSWORD_LENGTH,
        description="New password",
    )

    @field_validator("new_password")
    def validate_new_password_strength(cls, v: str) -> str:
        return validate_password(v)


class UserProfile(UserOut):
    post_count: Optional[int] = Field(None, description="Number of posts by user")
    is_active: bool = Field(default=True, description="Whether user account is active")


class UserStatistics(BaseModel):
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    new_users_today: int = Field(..., description="New users registered today")
