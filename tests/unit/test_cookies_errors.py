from fastapi import Response
import pytest

from src.api.utils import cookies


@pytest.mark.unit
async def test_set_refresh_cookie():
    response = Response()

    cookies.set_refresh_cookie(response, "test_token")

    # Check that the cookie was set correctly
    assert "set-cookie" in response.headers
    cookie_header = response.headers["set-cookie"]
    assert "__Host-rt=test_token" in cookie_header
    assert "Max-Age=604800" in cookie_header  # 7 days in seconds
    assert "HttpOnly" in cookie_header
    assert "Secure" in cookie_header
    assert "SameSite=strict" in cookie_header
    assert "Path=/" in cookie_header  # default path


@pytest.mark.unit
async def test_clear_refresh_cookie():
    response = Response()

    cookies.clear_refresh_cookie(response)

    # Check that the cookie was cleared correctly
    assert "set-cookie" in response.headers
    cookie_header = response.headers["set-cookie"]
    assert "__Host-rt=" in cookie_header
    assert "Max-Age=0" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "Secure" in cookie_header
    assert "SameSite=strict" in cookie_header
    assert "Path=/" in cookie_header  # default path
