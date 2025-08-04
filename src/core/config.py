import os
from functools import lru_cache
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .config_models import (
    DatabaseConfig,
    LoggingConfig,
    SecurityConfig,
    ServerConfig,
)


class Settings(BaseSettings):
    """Application settings assembled from environment variables and defaults."""

    # Environment
    environment: str = Field(
        default="development", pattern="^(development|staging|production)$"
    )
    debug: bool = Field(default=False)

    # API
    api_title: str = Field(default="MikoBlog API")
    api_version: str = Field(default="1.0.0")
    api_description: str = Field(default="A modern blog API built with FastAPI")

    # Server
    server: ServerConfig = ServerConfig()

    # Logging
    logging: LoggingConfig = LoggingConfig()

    # Database (populated in validator)
    database: Optional[DatabaseConfig] = None

    # Security (populated in validator)
    security: Optional[SecurityConfig] = None

    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def _assemble_subconfigs(self):
        """Assemble nested configurations from environment variables."""
        # DATABASE_URL
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        # DatabaseConfig assembly from env with defaults
        pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        echo = self.environment == "development" and self.debug

        self.database = DatabaseConfig(
            url=database_url,
            echo=echo,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
        )

        # SECRET_KEY
        secret_key = os.getenv("SECRET_KEY")
        if not secret_key:
            if self.environment == "production":
                raise ValueError(
                    "SECRET_KEY environment variable is required in production"
                )
            # Development fallback (never for production)
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

        # Server env overrides
        check_flag = os.getenv("DB_CHECK_ON_START")
        if isinstance(check_flag, str):
            self.server.check_db_on_start = check_flag.strip().lower() in (
                "1",
                "true",
                "yes",
                "on",
            )

        return self


@lru_cache()
def get_settings() -> "Settings":
    """Return cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
