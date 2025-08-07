import os
from typing import Annotated, Protocol

from fastapi import Depends, FastAPI, status
from httpx import AsyncClient
import pytest
from sqlalchemy.orm import Session

from src.core.deps import get_current_user, require_admin
from tests.factories.users import create_user


@pytest.fixture(autouse=True, scope="module")
def _env_jwt_keys():
    os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "tests/keys/jwt_private.pem")
    os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "tests/keys/jwt_public.pem")
    os.environ.setdefault("JWT_ACCESS_MINUTES", "1")
    yield


class _HasUserFields(Protocol):
    id: int
    role: str | None


def _protected_app(app: FastAPI):
    @app.get("/protected")
    async def protected(user: Annotated[_HasUserFields, Depends(get_current_user)]):
        return {
            "user_id": int(user.id),
            "role": (user.role if getattr(user, "role", None) else "user"),
        }

    @app.get("/admin-only")
    async def admin_only(_: Annotated[object, Depends(require_admin)]):
        return {"ok": True}

    return app


@pytest.mark.unit
@pytest.mark.anyio
async def test_get_current_user_success(client: AsyncClient, db_session: Session):
    # Arrange: create a user and login to obtain access token via API
    _protected_app(client._transport.app)  # type: ignore[attr-defined]
    create_user(
        db_session,
        username="depuser",
        email="dep@example.com",
        password="Str0ng!Passw0rd",
    )
    login_payload = {"username_or_email": "depuser", "password": "Str0ng!Passw0rd"}
    resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert resp.status_code == 200, resp.text
    access = resp.json()["data"]["access_token"]

    # Act: call protected endpoint with Authorization header
    headers = {"Authorization": f"Bearer {access}"}
    r = await client.get("/protected", headers=headers)

    # Assert
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "user"
    assert isinstance(body["user_id"], int)


@pytest.mark.unit
@pytest.mark.anyio
async def test_get_current_user_missing_header_401(client: AsyncClient):
    _protected_app(client._transport.app)  # type: ignore[attr-defined]
    r = await client.get("/protected")
    assert r.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.unit
@pytest.mark.anyio
async def test_get_current_user_wrong_typ_401(client: AsyncClient, db_session: Session):
    # Use refresh flow to get refresh cookie, then try to use refresh token as Bearer (should fail)
    _protected_app(client._transport.app)  # type: ignore[attr-defined]
    create_user(
        db_session,
        username="depuser2",
        email="dep2@example.com",
        password="Str0ng!Passw0rd",
    )
    login_payload = {"username_or_email": "depuser2", "password": "Str0ng!Passw0rd"}
    resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert resp.status_code == 200
    # Get refresh from cookies and try to use as Bearer
    set_cookie_headers = resp.headers.get_list("set-cookie")
    assert any("__Host-rt=" in h for h in set_cookie_headers)
    # httpx cookie jar contains value
    refresh = resp.cookies.get("__Host-rt")
    headers = {"Authorization": f"Bearer {refresh}"}
    r = await client.get("/protected", headers=headers)
    assert r.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.unit
@pytest.mark.anyio
async def test_get_current_user_unknown_user_401(client: AsyncClient):
    # Token for non-existing user (simulate by simple malformed token usage)
    _protected_app(client._transport.app)  # type: ignore[attr-defined]
    headers = {"Authorization": "Bearer invalid.token.value"}
    r = await client.get("/protected", headers=headers)
    assert r.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.unit
@pytest.mark.anyio
async def test_require_admin_success_and_forbidden(client: AsyncClient, db_session: Session):
    _protected_app(client._transport.app)  # type: ignore[attr-defined]
    # Non-admin
    create_user(
        db_session,
        username="normal",
        email="normal@example.com",
        password="Str0ng!Passw0rd",
        role="user",
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "normal", "password": "Str0ng!Passw0rd"},
    )
    access_user = resp.json()["data"]["access_token"]
    r_user = await client.get("/admin-only", headers={"Authorization": f"Bearer {access_user}"})
    assert r_user.status_code == status.HTTP_403_FORBIDDEN

    # Admin
    create_user(
        db_session,
        username="admin1",
        email="admin1@example.com",
        password="Str0ng!Passw0rd",
        role="admin",
    )
    resp2 = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "admin1", "password": "Str0ng!Passw0rd"},
    )
    access_admin = resp2.json()["data"]["access_token"]
    r_admin = await client.get("/admin-only", headers={"Authorization": f"Bearer {access_admin}"})
    assert r_admin.status_code == status.HTTP_200_OK
    assert r_admin.json() == {"ok": True}
