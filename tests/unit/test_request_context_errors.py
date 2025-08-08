from fastapi import Request
import pytest

from src.api.utils import request_context
from src.core.exceptions import AuthenticationError


@pytest.mark.unit
async def test_get_refresh_cookie_missing_cookie():
    # Create a mock request without cookie
    scope = {"type": "http", "headers": []}
    request = Request(scope)
    request._cookies = {}

    with pytest.raises(AuthenticationError) as exc_info:
        request_context.get_refresh_cookie(request)

    assert str(exc_info.value) == "Missing refresh cookie"


@pytest.mark.unit
async def test_get_refresh_cookie_empty_cookie():
    # Create a mock request with empty cookie
    scope = {"type": "http", "headers": []}
    request = Request(scope)
    request._cookies = {"__Host-rt": ""}

    with pytest.raises(AuthenticationError) as exc_info:
        request_context.get_refresh_cookie(request)

    assert str(exc_info.value) == "Missing refresh cookie"


@pytest.mark.unit
async def test_get_refresh_cookie_valid_cookie():
    # Create a mock request with valid cookie
    scope = {"type": "http", "headers": []}
    request = Request(scope)
    request._cookies = {"__Host-rt": "valid_cookie"}

    result = request_context.get_refresh_cookie(request)

    assert result == "valid_cookie"
