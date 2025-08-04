import os
from functools import lru_cache
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseModel):
    url: str = Field(..., description="Database connection URL")
    echo: bool = Field(default=False, description="Enable SQL query logging")
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0, le=100)
    pool_timeout: int = Field(default=30, ge=1, le=300)
    pool_pre_ping: bool = Field(default=True)


class SecurityConfig(BaseModel):
    secret_key: str = Field(..., min_length=32, description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    password_min_length: int = Field(default=12, ge=8, le=128)

    @field_validator("secret_key")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v


class ServerConfig(BaseModel):
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    reload: bool = Field(default=False, description="Enable auto-reload in development")


class LoggingConfig(BaseModel):
    level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class Settings(BaseSettings):

    # Environment
    environment: str = Field(
        default="development", pattern="^(development|staging|production)$"
    )
    debug: bool = Field(default=False)

    # Database
    database: Optional[DatabaseConfig] = None

    # Security
    security: Optional[SecurityConfig] = None

    # Server
    server: ServerConfig = ServerConfig()

    # Logging
    logging: LoggingConfig = LoggingConfig()

    # API
    api_title: str = Field(default="MikoBlog API")
    api_version: str = Field(default="1.0.0")
    api_description: str = Field(default="A modern blog API built with FastAPI")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Initialize database config
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        self.database = DatabaseConfig(
            url=database_url,
            echo=self.environment == "development" and self.debug,
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
        )

        # Initialize security config
        secret_key = os.getenv("SECRET_KEY")
        if not secret_key:
            if self.environment == "production":
                raise ValueError(
                    "SECRET_KEY environment variable is required in production"
                )
            # Generate a development key (should never be used in production)
            secret_key = "dev-secret-key-not-for-production-use-32-chars-minimum"

        self.security = SecurityConfig(
            secret_key=secret_key,
            algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "30")),
        )

        # Adjust logging for environment
        if self.environment == "production":
            self.logging.level = "WARNING"
        elif self.environment == "development":
            self.logging.level = "DEBUG"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Global settings instance
settings = get_settings()
