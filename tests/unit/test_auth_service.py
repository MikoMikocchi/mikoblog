from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from src.core.jwt import decode_token, validate_typ
from src.db.repositories import refresh_token_repository as rt_repo, user_repository as users_repo
from src.schemas.auth import AuthLogin, AuthRegister
from src.schemas.responses import SuccessResponse
from src.services import auth_service


def _utcnow() -> datetime:
    return datetime.now(UTC)


@pytest.mark.unit
def test_register_success_creates_user_and_hashes_password(db_session: Session):
    payload = AuthRegister(username="unituser", email="unit@example.com", password="Str0ng!Passw0rd")
    resp = auth_service.register(db=db_session, payload=payload)
    assert isinstance(resp, SuccessResponse)
    out = resp.data
    assert out.username == "unituser"
    db_user = users_repo.get_user_by_username(db_session, "unituser")
    assert db_user is not None
    # password must not be stored in plain text
    hashed = getattr(db_user, "hashed_password", None)
    assert isinstance(hashed, str) and hashed != ""
    assert hashed != "Str0ng!Passw0rd"


@pytest.mark.unit
def test_register_conflicts_username_email(db_session: Session):
    payload = AuthRegister(username="dupuser", email="dup@example.com", password="Str0ng!Passw0rd")
    auth_service.register(db=db_session, payload=payload)

    from src.core.exceptions import ConflictError

    with pytest.raises(ConflictError) as ex1:
        auth_service.register(
            db=db_session,
            payload=AuthRegister(username="dupuser", email="new@example.com", password="Str0ng!Passw0rd"),
        )
    assert "Username already registered" in str(ex1.value)

    # email conflict
    with pytest.raises(ConflictError) as ex2:
        auth_service.register(
            db=db_session,
            payload=AuthRegister(username="dup2", email="dup@example.com", password="Str0ng!Passw0rd"),
        )
    assert "Email already registered" in str(ex2.value)


@pytest.mark.unit
def test_login_success_creates_refresh_and_returns_access(db_session: Session):
    # arrange user
    reg = AuthRegister(username="loginuser", email="login@example.com", password="Str0ng!Passw0rd")
    auth_service.register(db=db_session, payload=reg)

    # act
    resp, refresh_jwt = auth_service.login(
        db=db_session,
        payload=AuthLogin(username_or_email="loginuser", password="Str0ng!Passw0rd"),
        user_agent="pytest-agent",
        ip="127.0.0.1",
    )

    # assert
    assert isinstance(resp, SuccessResponse)
    token = resp.data.access_token
    decoded = decode_token(token)
    validate_typ(decoded, "access")
    # refresh record created
    decoded_refresh = decode_token(refresh_jwt)
    validate_typ(decoded_refresh, "refresh")
    jti = decoded_refresh.get("jti")
    assert jti
    assert rt_repo.is_active(db_session, jti)


@pytest.mark.unit
def test_login_invalid_credentials(db_session: Session):
    reg = AuthRegister(username="badlogin", email="badlogin@example.com", password="Str0ng!Passw0rd")
    auth_service.register(db=db_session, payload=reg)

    from src.core.exceptions import AuthenticationError

    with pytest.raises(AuthenticationError) as ex1:
        auth_service.login(
            db=db_session,
            payload=AuthLogin(username_or_email="badlogin", password="wrong"),
            user_agent=None,
            ip=None,
        )
    assert "Invalid credentials" in str(ex1.value)

    with pytest.raises(AuthenticationError) as ex2:
        auth_service.login(
            db=db_session,
            payload=AuthLogin(username_or_email="unknown", password="Str0ng!Passw0rd"),
            user_agent=None,
            ip=None,
        )
    assert "Invalid credentials" in str(ex2.value)


@pytest.mark.unit
def test_refresh_success_rotates_refresh_and_issues_new_access(db_session: Session):
    # arrange: register + login to get refresh JWT
    reg = AuthRegister(username="refuser", email="ref@example.com", password="Str0ng!Passw0rd")
    auth_service.register(db=db_session, payload=reg)
    _, refresh_jwt = auth_service.login(
        db=db_session,
        payload=AuthLogin(username_or_email="refuser", password="Str0ng!Passw0rd"),
        user_agent="pytest",
        ip="127.0.0.1",
    )

    # act
    resp, new_refresh = auth_service.refresh(db=db_session, refresh_jwt=refresh_jwt, user_agent="pytest2", ip="127.0.0.2")

    # assert
    assert isinstance(resp, SuccessResponse)
    new_access = resp.data.access_token
    validate_typ(decode_token(new_access), "access")
    # old refresh must become inactive
    old_jti = decode_token(refresh_jwt)["jti"]
    assert not rt_repo.is_active(db_session, old_jti)
    # new refresh is active
    new_jti = decode_token(new_refresh)["jti"]
    assert rt_repo.is_active(db_session, new_jti)


@pytest.mark.unit
def test_refresh_invalid_and_inactive_paths(db_session: Session, monkeypatch):
    from src.core.exceptions import AuthenticationError

    # invalid JWT format should fail authentication
    with pytest.raises(AuthenticationError):
        auth_service.refresh(db=db_session, refresh_jwt="not.a.jwt", user_agent=None, ip=None)

    reg = AuthRegister(username="inactive", email="inactive@example.com", password="Str0ng!Passw0rd")
    auth_service.register(db=db_session, payload=reg)
    _, refresh_jwt = auth_service.login(
        db=db_session,
        payload=AuthLogin(username_or_email="inactive", password="Str0ng!Passw0rd"),
        user_agent=None,
        ip=None,
    )
    jti = decode_token(refresh_jwt)["jti"]
    # revoke
    rt_repo.revoke_by_jti(db_session, jti=jti)
    # inactive/rotated refresh must raise AuthenticationError
    with pytest.raises(AuthenticationError) as ex:
        auth_service.refresh(db=db_session, refresh_jwt=refresh_jwt, user_agent=None, ip=None)
    assert "not active" in str(ex.value)


@pytest.mark.unit
def test_logout_by_refresh_token(db_session: Session):
    reg = AuthRegister(username="logoutu", email="logoutu@example.com", password="Str0ng!Passw0rd")
    auth_service.register(db=db_session, payload=reg)
    _, refresh_jwt = auth_service.login(
        db=db_session,
        payload=AuthLogin(username_or_email="logoutu", password="Str0ng!Passw0rd"),
        user_agent=None,
        ip=None,
    )
    jti = decode_token(refresh_jwt)["jti"]
    # should be active before logout
    assert rt_repo.is_active(db_session, jti)
    resp = auth_service.logout(db=db_session, refresh_jwt=refresh_jwt)
    assert isinstance(resp, SuccessResponse)
    assert not rt_repo.is_active(db_session, jti)


@pytest.mark.unit
def test_logout_all_revokes_all_active_for_user(db_session: Session):
    reg = AuthRegister(username="logoutall", email="logoutall@example.com", password="Str0ng!Passw0rd")
    auth_service.register(db=db_session, payload=reg)
    # create two active sessions (double login)
    _, r1 = auth_service.login(
        db=db_session,
        payload=AuthLogin(username_or_email="logoutall", password="Str0ng!Passw0rd"),
        user_agent="A",
        ip="1.1.1.1",
    )
    _, r2 = auth_service.login(
        db=db_session,
        payload=AuthLogin(username_or_email="logoutall", password="Str0ng!Passw0rd"),
        user_agent="B",
        ip="2.2.2.2",
    )
    uid = int(decode_token(r1)["sub"])
    # both are active before logout-all
    assert rt_repo.is_active(db_session, decode_token(r1)["jti"])
    assert rt_repo.is_active(db_session, decode_token(r2)["jti"])
    resp = auth_service.logout_all(db=db_session, user_id=uid)
    assert isinstance(resp, SuccessResponse)
    # after operation both should be inactive
    assert not rt_repo.is_active(db_session, decode_token(r1)["jti"])
    assert not rt_repo.is_active(db_session, decode_token(r2)["jti"])
