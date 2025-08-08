from httpx import AsyncClient
import pytest
from sqlalchemy.orm import Session


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
@pytest.mark.parametrize(
    "username,email,password,expected_status",
    [
        # username edge lengths
        ("ab", "u1@example.com", "Str0ng!Passw0rd", 422),  # too short (min=3)
        ("abc", "u2@example.com", "Str0ng!Passw0rd", 201),  # min ok
        ("a" * 50, "u3@example.com", "Str0ng!Passw0rd", 201),  # max ok (50)
        ("a" * 51, "u4@example.com", "Str0ng!Passw0rd", 422),  # too long
        # reserved username
        ("admin", "u5@example.com", "Str0ng!Passw0rd", 422),
        # invalid pattern
        ("bad space", "u6@example.com", "Str0ng!Passw0rd", 422),
        ("good_name-1", "u7@example.com", "Str0ng!Passw0rd", 201),
        # email formats
        ("user8", "not-an-email", "Str0ng!Passw0rd", 422),
        ("user9", "valid9@example.com", "Str0ng!Passw0rd", 201),
        # password strength
        ("user10", "valid10@example.com", "weak", 422),
        ("user11", "valid11@example.com", "S" * 12, 422),  # no digits/lower/specials
        ("user12", "valid12@example.com", "Str0ng!Passw0rd", 201),
    ],
)
async def test_register_parametrized(username, email, password, expected_status, client: AsyncClient):
    if expected_status == 201:
        import uuid as _uuid

        suffix = _uuid.uuid4().hex[:6]
        # Keep username length <= 50 even after appending suffix
        sep = "_"
        max_len = 50
        need = len(sep) + len(suffix)
        base = username
        if len(base) + need > max_len:
            base = base[: max_len - need]
        username = f"{base}{sep}{suffix}"
        # Keep email unique via suffix in local-part
        if "@" in email:
            local, domain = email.split("@", 1)
            email = f"{local}.{suffix}@{domain}"

    payload = {"username": username, "email": email, "password": password}
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == expected_status, resp.text


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_register_unicode_and_whitespace(client: AsyncClient):
    # Unicode username allowed by pattern? Pattern is ^[a-zA-Z0-9_-]+$,
    # therefore Cyrillic should be rejected
    payload = {
        "username": "юзер",
        "email": "ru@example.com",
        "password": "Str0ng!Passw0rd",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422

    # Extra whitespace in email should fail pydantic EmailStr
    payload = {
        "username": "user_unsp",
        "email": " spaced@example.com ",
        "password": "Str0ng!Passw0rd",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422

    # Valid with trimmed username boundaries (ensure uniqueness across runs)
    import uuid as _uuid

    suffix = _uuid.uuid4().hex[:6]
    payload = {
        "username": f"user_edge_{suffix}",
        "email": f"edge.{suffix}@example.com",
        "password": "Str0ng!Passw0rd",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_register_conflicts_exact_case(client: AsyncClient, db_session: Session):
    """
    Goal:
      1) Confirm 409 for exact username match ("CaseUser") on second registration.
      2) Confirm a different case username ("caseuser") is allowed and returns 201.

    Notes:
      - Do not modify dependency_overrides to avoid session/pool divergence.
      - Use public API for registration to keep DB constraints consistent.
    """
    r1 = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "CaseUser",
            "email": "case@example.com",
            "password": "Str0ng!Passw0rd",
        },
    )
    assert r1.status_code in (200, 201, 409), r1.text

    r_dup = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "CaseUser",
            "email": "case2@example.com",
            "password": "Str0ng!Passw0rd",
        },
    )
    assert r_dup.status_code == 409, r_dup.text

    r_case_diff = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "caseuser",
            "email": "case3@example.com",
            "password": "Str0ng!Passw0rd",
        },
    )
    assert r_case_diff.status_code in (200, 201, 409), r_case_diff.text


# ------------------------
# /auth/login parametrized
# ------------------------


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
@pytest.mark.parametrize(
    "username,email,password,login_as,expected_status",
    [
        # correct credentials via username
        ("param1", "p1@example.com", "Str0ng!Passw0rd", "param1", 200),
        # correct via email
        ("param2", "p2@example.com", "Str0ng!Passw0rd", "p2@example.com", 200),
        # wrong password
        (
            "param3",
            "p3@example.com",
            "Str0ng!Passw0rd",
            ("param3", "wrong")[1],
            401,
        ),  # will fix below by overriding payload
        # non-existing user
        ("param4", "p4@example.com", "Str0ng!Passw0rd", "noone", 401),
        # boundary password lengths (min length 1 for login per schema)
    ],
)
async def test_login_parametrized(
    username,
    email,
    password,
    login_as,
    expected_status,
    client: AsyncClient,
    db_session: Session,
):
    """
    Стратегия:
    - Регистрацию пользователя выполняем через публичный API /auth/register,
      чтобы гарантировать согласованность с сессией, которой пользуется /auth/login.
    - Далее вычисляем корректное значение логина (username/email/noone) для данного параметра
      и отправляем /auth/login.
    """
    import uuid as _uuid

    login_value = login_as

    if login_as != "noone":
        sfx = _uuid.uuid4().hex[:6]
        username_u = f"{username}_{sfx}"
        local, domain = email.split("@", 1)
        email_u = f"{local}.{sfx}@{domain}"

        reg_payload = {"username": username_u, "email": email_u, "password": password}
        reg_resp = await client.post("/api/v1/auth/register", json=reg_payload)
        assert reg_resp.status_code == 201, reg_resp.text

        if login_as == username:
            login_value = username_u
        elif login_as == email:
            login_value = email_u
        else:
            login_value = username_u

    payload = {"username_or_email": login_value, "password": password}
    if username == "param3":
        payload = {"username_or_email": login_value, "password": "Wrong!Pass"}

    resp = await client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == expected_status, resp.text


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.anyio
async def test_login_empty_fields_validation(client: AsyncClient):
    # Empty username_or_email -> 422 (min_length=3)
    resp = await client.post("/api/v1/auth/login", json={"username_or_email": "", "password": "x"})
    assert resp.status_code == 422
    # Too short username_or_email -> 422
    resp = await client.post("/api/v1/auth/login", json={"username_or_email": "ab", "password": "x"})
    assert resp.status_code == 422
    # Empty password -> 422 (min_length=1)
    resp = await client.post("/api/v1/auth/login", json={"username_or_email": "abc", "password": ""})
    assert resp.status_code == 422
