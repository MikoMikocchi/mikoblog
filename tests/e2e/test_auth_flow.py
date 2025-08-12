from httpx import AsyncClient
import pytest
from sqlalchemy.orm import Session


@pytest.mark.e2e
@pytest.mark.anyio
async def test_full_auth_flow_register_login_access_refresh_logout(client: AsyncClient, db_session: Session):
    # 1) Register
    # Generate unique registration data per run to avoid 409 conflicts in repeated or parallel runs
    import uuid as _uuid

    _suffix = _uuid.uuid4().hex[:8]
    reg_payload = {
        "username": f"e2euser_{_suffix}",
        "email": f"e2euser_{_suffix}@example.com",
        "password": "Str0ng!Passw0rd",
    }
    resp = await client.post("/api/v1/auth/register", json=reg_payload)
    assert resp.status_code == 201, resp.text

    # 2) Login — use the same unique credentials as in registration
    login_payload = {
        "username_or_email": reg_payload["username"],
        "password": reg_payload["password"],
    }
    resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert resp.status_code == 200, resp.text
    # Debug: ensure Set-Cookie is present and cookie jar keeps __Host-rt for current base host
    print("Set-Cookie headers:", resp.headers.get_list("set-cookie"))
    # httpx ASGITransport stores cookies under the exact netloc used in base_url.
    # We use https://testserver.local in conftest, so use that for subsequent requests and lookups.
    # __Host- cookies must have Path="/"; httpx Cookies.get requires exact path match
    cookie_val = client.cookies.get("__Host-rt", domain="testserver.local", path="/")
    assert cookie_val is not None, "Refresh cookie was not stored in client cookie jar"
    access = resp.json()["data"]["access_token"]

    # 3) Access protected test-only endpoint using dependency get_current_user
    headers = {"Authorization": f"Bearer {access}"}
    r_ok = await client.get("/e2e/protected", headers=headers)
    assert r_ok.status_code == 200
    body = r_ok.json()
    assert body["ok"] is True
    assert isinstance(body["user_id"], int)

    # 4) Refresh using cookie set by login
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200, resp.text
    new_access = resp.json()["data"]["access_token"]
    assert isinstance(new_access, str)

    # New token should also access the protected endpoint
    r_ok2 = await client.get("/e2e/protected", headers={"Authorization": f"Bearer {new_access}"})
    assert r_ok2.status_code == 200

    # 5) Logout and ensure refresh token revoked
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 200

    # 6) After logout, refresh should fail because cookie is cleared or revoked
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401

    # 7) Access protected endpoint without Authorization should be 401
    r_no_auth = await client.get("/e2e/protected")
    assert r_no_auth.status_code == 401
