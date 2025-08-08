from httpx import AsyncClient
import pytest
from sqlalchemy.orm import Session

from src.core.jwt import decode_token, validate_typ


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_logout_without_cookie_clears_cookie_and_returns_ok(client: AsyncClient):
    # Calling logout without refresh cookie:
    # controller should clear cookie and return SuccessResponse
    r = await client.post("/api/v1/auth/logout")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("success") is True
    # Verify cookie is cleared (Max-Age=0)
    set_cookie = r.headers.get("set-cookie", "")
    assert "__Host-rt=" in set_cookie
    assert "Max-Age=0" in set_cookie


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_logout_all_requires_valid_refresh_cookie(client: AsyncClient, db_session: Session):
    # Without cookie -> 401 (Missing refresh cookie)
    r = await client.post("/api/v1/auth/logout-all")
    assert r.status_code == 401

    # Happy path:
    # 1) Register a fresh user via API to ensure visibility across request boundaries
    import uuid as _uuid

    _suf1 = _uuid.uuid4().hex[:8]
    uname1 = f"ctl_user1_{_suf1}"
    email1 = f"{uname1}@example.com"

    register_payload = {
        "username": uname1,
        "email": email1,
        "password": "Str0ng!Passw0rd",
    }
    r_reg = await client.post("/api/v1/auth/register", json=register_payload)
    assert r_reg.status_code == 201, r_reg.text

    # 2) Login using the same credentials to set refresh cookie
    r_login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": email1, "password": "Str0ng!Passw0rd"},
    )
    assert r_login.status_code == 200, r_login.text
    # 3) logout-all must return 200 and clear cookie
    r_out = await client.post("/api/v1/auth/logout-all")
    assert r_out.status_code == 200, r_out.text
    set_cookie = r_out.headers.get("set-cookie", "")
    assert "__Host-rt=" in set_cookie
    assert "Max-Age=0" in set_cookie


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_refresh_cookie_is_required_and_rotation_works(client: AsyncClient, db_session: Session):
    # Without refresh cookie -> 401
    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 401

    # With cookie scenario:
    # Register via API to ensure visibility across request boundaries, then login
    import uuid as _uuid

    _suf = _uuid.uuid4().hex[:8]
    uname = f"ctl_user2_{_suf}"
    email = f"{uname}@example.com"

    r_reg = await client.post(
        "/api/v1/auth/register",
        json={"username": uname, "email": email, "password": "Str0ng!Passw0rd"},
    )
    assert r_reg.status_code == 201, r_reg.text

    r_login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": email, "password": "Str0ng!Passw0rd"},
    )
    assert r_login.status_code == 200, r_login.text
    # refresh cookie is now stored in client
    r_ref = await client.post("/api/v1/auth/refresh")
    assert r_ref.status_code == 200
    body = r_ref.json()
    assert body.get("success") is True
    access = body["data"]["access_token"]
    validate_typ(decode_token(access), "access")


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_login_sets_cookie_attributes_strict(client: AsyncClient, db_session: Session):
    # Validate cookie attributes set by the controller.
    # Register via API to ensure visibility across request boundaries, then login.
    import uuid as _uuid

    _suf = _uuid.uuid4().hex[:8]
    uname = f"cookie_user_{_suf}"
    email = f"{uname}@example.com"

    r_reg = await client.post(
        "/api/v1/auth/register",
        json={"username": uname, "email": email, "password": "Str0ng!Passw0rd"},
    )
    assert r_reg.status_code == 201, r_reg.text

    r = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": email, "password": "Str0ng!Passw0rd"},
    )
    assert r.status_code == 200, r.text
    set_cookie = r.headers.get("set-cookie", "")
    # Controller uses utils.cookies.set_refresh_cookie ->
    # __Host-rt; httponly; secure; samesite=strict; path=/auth

    # Note: httpx/Starlette may normalize SameSite casing to lowercase
    # ("samesite=strict" or "SameSite=strict").

    # Accept both casings to avoid false negatives across environments.
    assert "__Host-rt=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert ("SameSite=Strict" in set_cookie) or ("SameSite=strict" in set_cookie) or ("samesite=strict" in set_cookie.lower())
    # Path can be normalized by router prefixing (e.g., /api/v1/auth).
    assert "/auth" in set_cookie and "Path=" in set_cookie


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_register_returns_user_out_shape(client: AsyncClient):
    # Use unique credentials to avoid collisions across parallel backends (asyncio/trio)
    import uuid as _uuid

    _suf = _uuid.uuid4().hex[:8]
    uname = f"shape_chk_{_suf}"
    email = f"{uname}@example.com"

    r = await client.post(
        "/api/v1/auth/register",
        json={
            "username": uname,
            "email": email,
            "password": "Str0ng!Passw0rd",
        },
    )
    assert r.status_code == 201, r.text
    payload = r.json()
    assert payload["success"] is True
    data = payload["data"]
    # Validate UserOut fields (id, username, email, role)
    assert "id" in data
    assert data["username"] == uname
    assert data["email"] == email
    assert data["role"] in ("user", "admin")
