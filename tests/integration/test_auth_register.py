from httpx import AsyncClient
import pytest
from sqlalchemy.orm import Session


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_register_success(client: AsyncClient, db_session: Session):
    payload = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "Str0ng!Passw0rd",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["username"] == payload["username"]
    assert data["email"] == payload["email"]
    assert data["role"] == "user"
    # password must not be present in response
    assert "hashed_password" not in data


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_register_conflict_username(client: AsyncClient, db_session: Session):
    # pre-create a user with the same username via API to ensure commit/visibility
    resp0 = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "dupuser",
            "email": "dup@example.com",
            "password": "Str0ng!Passw0rd",
        },
    )
    assert resp0.status_code in (200, 201, 409), resp0.text
    payload = {
        "username": "dupuser",
        "email": "new2@example.com",
        "password": "Str0ng!Passw0rd",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409
    body = resp.json()
    # global exception handler returns JSONResponse with success False or message
    assert (body.get("success") is False) or ("message" in body)


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_register_conflict_email(client: AsyncClient, db_session: Session):
    resp0 = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "uniqueuser",
            "email": "dup@example.com",
            "password": "Str0ng!Passw0rd",
        },
    )
    assert resp0.status_code in (200, 201, 409), resp0.text
    payload = {
        "username": "uniqueuser2",
        "email": "dup@example.com",
        "password": "Str0ng!Passw0rd",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload,field",
    [
        (
            {"username": "nu", "email": "a@b.c", "password": "Str0ng!Passw0rd"},
            "username",
        ),
        (
            {
                "username": "validuser",
                "email": "bad-email",
                "password": "Str0ng!Passw0rd",
            },
            "email",
        ),
        (
            {"username": "validuser", "email": "v@example.com", "password": "weak"},
            "password",
        ),
    ],
)
async def test_register_validation_errors(client: AsyncClient, payload, field):
    resp = await client.post("/api/v1/auth/register", json=payload)
    # Pydantic body validation -> 422
    assert resp.status_code == 422
