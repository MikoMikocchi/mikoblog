import pytest
from sqlalchemy.exc import SQLAlchemyError

from db.utils import transactional


@pytest.mark.unit
async def test_transactional_success(monkeypatch):
    # Mock session
    class MockSession:
        def __init__(self):
            self.committed = False
            self.rolled_back = False
            self.is_active = True

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True

    # Create a function decorated with @transactional
    @transactional
    def mock_function(db: MockSession, value: int) -> int:
        return value * 2

    session = MockSession()
    result = mock_function(session, 5)

    # Check that the function executed correctly
    assert result == 10

    # Check that the session was committed
    assert session.committed


@pytest.mark.unit
async def test_transactional_sqlalchemy_error(monkeypatch):
    # Mock session
    class MockSession:
        def __init__(self):
            self.committed = False
            self.rolled_back = False
            self.is_active = True

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True

    # Create a function decorated with @transactional that raises SQLAlchemyError
    @transactional
    def mock_function(db: MockSession, value: int) -> int:
        raise SQLAlchemyError("Database error")

    session = MockSession()

    with pytest.raises(SQLAlchemyError):
        mock_function(session, 5)

    # Check that the session was rolled back
    assert session.rolled_back

    # Check that the session was not committed
    assert not session.committed


@pytest.mark.unit
async def test_transactional_non_sqlalchemy_error(monkeypatch):
    # Mock session
    class MockSession:
        def __init__(self):
            self.committed = False
            self.rolled_back = False
            self.is_active = True

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True

    # Create a function decorated with @transactional that raises a non-SQLAlchemy error
    @transactional
    def mock_function(db: MockSession, value: int) -> int:
        raise ValueError("Invalid value")

    session = MockSession()

    with pytest.raises(ValueError):
        mock_function(session, 5)

    # Check that the session was rolled back
    assert session.rolled_back

    # Check that the session was not committed
    assert not session.committed


@pytest.mark.unit
async def test_transactional_session_as_kwarg(monkeypatch):
    # Mock session
    class MockSession:
        def __init__(self):
            self.committed = False
            self.rolled_back = False
            self.is_active = True

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True

    # Create a function decorated with @transactional
    @transactional
    def mock_function(value: int, db: MockSession) -> int:
        return value * 2

    session = MockSession()
    result = mock_function(5, db=session)

    # Check that the function executed correctly
    assert result == 10

    # Check that the session was committed
    assert session.committed


@pytest.mark.unit
async def test_transactional_no_session(monkeypatch):
    # Create a function decorated with @transactional
    @transactional
    def mock_function(value: int) -> int:
        return value * 2

    result = mock_function(5)

    # Check that the function executed correctly
    assert result == 10
