import pytest

from db import database


@pytest.mark.unit
async def test_check_db_connection_success(monkeypatch):
    # Mock engine.begin to succeed
    class MockConnection:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def execute(self, *args, **kwargs):
            pass

    class MockEngine:
        async def begin(self):
            return MockConnection()

    monkeypatch.setattr(database, "engine", MockEngine())

    result = await database.check_db_connection()

    assert result is True


@pytest.mark.unit
async def test_check_db_connection_failure(monkeypatch):
    # Mock engine.begin to raise an exception
    class MockEngine:
        async def begin(self):
            raise Exception("Database connection failed")

    monkeypatch.setattr(database, "engine", MockEngine())

    result = await database.check_db_connection()

    assert result is False


@pytest.mark.unit
async def test_get_db_info_success(monkeypatch):
    # Mock engine to succeed
    class MockEngine:
        pass

    monkeypatch.setattr(database, "engine", MockEngine())

    result = await database.get_db_info()

    assert result == {"status": "healthy"}


@pytest.mark.unit
async def test_get_db_info_failure(monkeypatch):
    # Mock engine to raise an exception
    class MockEngine:
        pass

    monkeypatch.setattr(database, "engine", MockEngine())

    # Mock logger to capture error
    class MockLogger:
        def error(self, *args, **kwargs):
            pass

    monkeypatch.setattr(database, "logger", MockLogger())

    # Force an exception in get_db_info
    def mock_getattr(obj, name, default=None):
        if name == "status":
            raise Exception("Database error")
        return default

    monkeypatch.setattr(database, "getattr", mock_getattr)

    result = await database.get_db_info()

    assert result == {"status": "error", "message": "Database error"}
