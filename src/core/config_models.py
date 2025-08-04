from pydantic import BaseModel, Field, field_validator


class DatabaseConfig(BaseModel):
    """Database connection and engine configuration."""

    url: str = Field(..., description="Database connection URL")
    echo: bool = Field(default=False, description="Enable SQL query logging")
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0, le=100)
    pool_timeout: int = Field(default=30, ge=1, le=300)
    pool_pre_ping: bool = Field(default=True)


class SecurityConfig(BaseModel):
    """Security configuration for JWT and auth."""

    secret_key: str = Field(..., min_length=32, description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return value


class ServerConfig(BaseModel):
    """Server runtime configuration."""

    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    reload: bool = Field(default=False, description="Enable auto-reload in development")
    check_db_on_start: bool = Field(
        default=True, description="Run DB connection check on startup"
    )


class LoggingConfig(BaseModel):
    """Application logging configuration."""

    level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
