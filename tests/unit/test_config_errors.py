import pytest

from src.core.config import Settings, get_settings


@pytest.mark.unit
async def test_settings_missing_database_url(monkeypatch):
    # Remove DATABASE_URL from environment
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValueError) as exc_info:
        Settings()

    assert str(exc_info.value) == "DATABASE_URL environment variable is required"


@pytest.mark.unit
async def test_settings_missing_secret_key_in_production(monkeypatch):
    # Set environment to production
    monkeypatch.setenv("ENVIRONMENT", "production")

    # Remove SECRET_KEY from environment
    monkeypatch.delenv("SECRET_KEY", raising=False)

    # Set DATABASE_URL
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")

    with pytest.raises(ValueError) as exc_info:
        Settings()

    assert "SECRET_KEY environment variable is required" in str(exc_info.value)


@pytest.mark.unit
async def test_settings_invalid_database_url(monkeypatch):
    # Set invalid DATABASE_URL
    monkeypatch.setenv("DATABASE_URL", "invalid_url")

    # Set SECRET_KEY
    monkeypatch.setenv("SECRET_KEY", "test_secret_key")

    settings = Settings()

    assert settings.database is not None
    assert settings.database.url == "invalid_url"


@pytest.mark.unit
async def test_get_settings_cached():
    # Get settings twice
    settings1 = get_settings()
    settings2 = get_settings()

    # Check that the same instance is returned
    assert settings1 is settings2
