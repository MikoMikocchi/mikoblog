import os

from httpx import AsyncClient
import pytest
from sqlalchemy.orm import Session

from tests.factories.users import create_user


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_login_success_with_username_sets_refresh_cookie(client: AsyncClient, db_session: Session):
    # Register via API to ensure visibility across request boundaries, then login by username
    import uuid as _uuid

    _suf = _uuid.uuid4().hex[:8]
    uname = f"loginuser_{_suf}"
    email = f"{uname}@example.com"

    r_reg = await client.post(
        "/api/v1/auth/register",
        json={"username": uname, "email": email, "password": "Str0ng!Passw0rd"},
    )
    assert r_reg.status_code == 201, r_reg.text

    payload = {"username_or_email": uname, "password": "Str0ng!Passw0rd"}
    resp = await client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert "access_token" in data and isinstance(data["access_token"], str)
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0

    # Verify refresh cookie attributes
    cookie = resp.cookies.get("__Host-rt")
    assert cookie is not None

    # httpx doesn't expose all cookie flags directly; we check via headers
    set_cookie_headers = resp.headers.get_list("set-cookie")
    assert any("__Host-rt=" in h for h in set_cookie_headers)
    # Required cookie attributes by controller:
    # HttpOnly; Secure; SameSite=Strict; Max-Age≈7 days; Path=/ (per __Host- spec)
    attr_line = ";".join(set_cookie_headers)
    lower_attr = attr_line.lower()
    assert "httponly" in lower_attr
    assert "secure" in lower_attr
    assert "samesite=strict" in lower_attr
    # Accept case variations/spaces for Max-Age; some stacks may emit Expires instead
    expected_days = int(os.getenv("JWT_REFRESH_DAYS", "7"))
    expected_seconds = expected_days * 24 * 60 * 60
    assert (f"max-age={expected_seconds}" in lower_attr) or (f"max-age= {expected_seconds}" in lower_attr) or ("expires=" in lower_attr)
    # __Host- cookies must have Path=/
    assert "path=/" in lower_attr


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_login_success_with_email(client: AsyncClient, db_session: Session):
    # Register via API to ensure visibility across request boundaries, then login by email
    import uuid as _uuid

    _suf = _uuid.uuid4().hex[:8]
    uname = f"loginuser2_{_suf}"
    email = f"{uname}@example.com"

    r_reg = await client.post(
        "/api/v1/auth/register",
        json={"username": uname, "email": email, "password": "Str0ng!Passw0rd"},
    )
    assert r_reg.status_code == 201, r_reg.text

    payload = {"username_or_email": email, "password": "Str0ng!Passw0rd"}

    resp = await client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert "access_token" in body["data"]


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_login_invalid_credentials_wrong_password(client: AsyncClient, db_session: Session):
    create_user(
        db_session,
        username="badpass",
        email="badpass@example.com",
        password="Str0ng!Passw0rd",
    )
    payload = {"username_or_email": "badpass", "password": "WrongPass123!"}

    resp = await client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_login_user_not_found(client: AsyncClient):
    payload = {"username_or_email": "missinguser", "password": "Str0ng!Passw0rd"}
    resp = await client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload",
    [
        {"username_or_email": "", "password": "x"},
        {"username_or_email": "a", "password": ""},
        {"username_or_email": "", "password": ""},
    ],
)
async def test_login_validation_errors(client: AsyncClient, payload):
    # Pydantic will enforce min lengths -> 422
    resp = await client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 422
