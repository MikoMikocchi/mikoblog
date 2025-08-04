from typing import Literal

from pydantic import BaseModel, EmailStr, Field
from schemas.users import UserOut


class AuthRegister(BaseModel):
    """Registration payload."""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email")
    password: str = Field(..., min_length=12, max_length=128, description="Password")


class AuthLogin(BaseModel):
    """Login payload."""

    username_or_email: str = Field(
        ..., min_length=3, max_length=100, description="Username or email"
    )
    password: str = Field(..., min_length=1, max_length=128, description="Password")


class TokenPayload(BaseModel):
    """Access token response payload."""

    access_token: str = Field(..., description="JWT access token")
    token_type: Literal["bearer"] = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., ge=1, description="Access token TTL in seconds")


# Reexports for convenience in response_model typing hints
UserOutResponse = UserOut
