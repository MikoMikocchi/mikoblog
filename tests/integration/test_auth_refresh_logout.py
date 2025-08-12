from httpx import AsyncClient
import pytest
from sqlalchemy.orm import Session


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_refresh_success_rotates_cookie_and_issues_new_access(client: AsyncClient, db_session: Session):
    """
    Reliable scenario "login -> refresh":
      1) Create a user via factory (inside test transaction).
      2) Login via /auth/login — controller creates refresh record and sets __Host-rt cookie.
      3) Call /auth/refresh — expect 200, new access and new refresh cookie (rotation).
    """
    import uuid

    uname = f"refuser_{uuid.uuid4().hex[:8]}"
    email = f"{uname}@example.com"

    r_reg = await client.post(
        "/api/v1/auth/register",
        json={"username": uname, "email": email, "password": "Str0ng!Passw0rd"},
    )
    assert r_reg.status_code == 201, r_reg.text

    r_login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": uname, "password": "Str0ng!Passw0rd"},
    )
    assert r_login.status_code == 200, r_login.text
    set_cookie_headers = r_login.headers.get_list("set-cookie")
    assert any("__Host-rt=" in h for h in set_cookie_headers)

    r_ref = await client.post("/api/v1/auth/refresh")
    assert r_ref.status_code == 200, r_ref.text

    body = r_ref.json()
    assert body.get("success") is True
    data = body.get("data") or {}
    assert isinstance(data.get("access_token"), str) and data.get("access_token")
    set_cookie_headers2 = r_ref.headers.get_list("set-cookie")
    assert any("__Host-rt=" in h for h in set_cookie_headers2)


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_refresh_missing_cookie_returns_401(client: AsyncClient):
    # no cookie
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_refresh_inactive_token_returns_401(client: AsyncClient, db_session: Session):
    import uuid

    uname = f"inactiveu_{uuid.uuid4().hex[:8]}"
    email = f"{uname}@example.com"

    r_reg = await client.post(
        "/api/v1/auth/register",
        json={"username": uname, "email": email, "password": "Str0ng!Passw0rd"},
    )
    assert r_reg.status_code == 201, r_reg.text

    r_login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": uname, "password": "Str0ng!Passw0rd"},
    )
    assert r_login.status_code == 200, r_login.text

    r_out_all = await client.post("/api/v1/auth/logout-all")
    assert r_out_all.status_code == 200, r_out_all.text

    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_logout_revokes_current_refresh(client: AsyncClient, db_session: Session):
    """
    Complete path through public endpoints:
    register -> login (sets __Host-rt) -> logout -> refresh(401)
    """
    import uuid

    uname = f"logoutu_{uuid.uuid4().hex[:8]}"
    email = f"{uname}@example.com"

    r_reg = await client.post(
        "/api/v1/auth/register",
        json={"username": uname, "email": email, "password": "Str0ng!Passw0rd"},
    )
    assert r_reg.status_code == 201, r_reg.text

    r_login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": uname, "password": "Str0ng!Passw0rd"},
    )
    assert r_login.status_code == 200, r_login.text
    set_cookie_headers = r_login.headers.get_list("set-cookie")
    assert any("__Host-rt=" in h for h in set_cookie_headers)

    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 200, resp.text

    r_try = await client.post("/api/v1/auth/refresh")
    assert r_try.status_code == 401


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_logout_without_cookie_is_idempotent(client: AsyncClient):
    resp = await client.post("/api/v1/auth/logout")
    # Controller clears cookie and returns OK even when there is no cookie
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_logout_all_revokes_all_user_tokens(app, client: AsyncClient, db_session: Session):
    # Create user via API to ensure proper commit/visibility for subsequent login
    r_reg = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "logoutallu",
            "email": "logoutall@example.com",
            "password": "Str0ng!Passw0rd",
        },
    )
    assert r_reg.status_code in (200, 201), r_reg.text

    r1 = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "logoutallu", "password": "Str0ng!Passw0rd"},
    )
    assert r1.status_code == 200, r1.text
    # Ensure refresh cookie stored in client's jar
    set_cookie_headers1 = r1.headers.get_list("set-cookie")
    assert any("__Host-rt=" in h for h in set_cookie_headers1)
    assert client.cookies.get("__Host-rt") is not None

    from httpx import AsyncClient as _AsyncClient

    from tests.conftest import _create_asgi_transport

    async with _AsyncClient(
        transport=_create_asgi_transport(app),
        base_url=str(client.base_url),
        follow_redirects=True,
    ) as c2:
        r2 = await c2.post(
            "/api/v1/auth/login",
            json={"username_or_email": "logoutallu", "password": "Str0ng!Passw0rd"},
        )
        assert r2.status_code == 200, r2.text

        # Ensure original client's cookie still present before logout-all
        assert client.cookies.get("__Host-rt") is not None
        r_out_all = await client.post("/api/v1/auth/logout-all")
        assert r_out_all.status_code == 200, r_out_all.text

        r_try1 = await client.post("/api/v1/auth/refresh")
        r_try2 = await c2.post("/api/v1/auth/refresh")
        assert r_try1.status_code == 401
        assert r_try2.status_code == 401
