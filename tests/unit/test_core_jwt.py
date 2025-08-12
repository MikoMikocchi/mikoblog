import os
import time

import jwt as pyjwt
import pytest

from core.jwt import decode_token, encode_access_token, encode_refresh_token, make_jti, validate_typ
from core.jwt_keys import load_keypair


@pytest.fixture(autouse=True, scope="module")
def _jwt_env_keys():
    # Ensure test keys from tests/keys are used
    os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "tests/keys/jwt_private.pem")
    os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "tests/keys/jwt_public.pem")
    # Speed up expiry tests
    os.environ.setdefault("JWT_ACCESS_MINUTES", "1")
    os.environ.setdefault("JWT_REFRESH_DAYS", "1")
    # Preload keys once to fail fast if keys are invalid
    load_keypair()
    yield


@pytest.mark.unit
def test_encode_and_decode_access_token_success():
    user_id = 123
    token = encode_access_token(user_id, jti=make_jti())
    decoded = decode_token(token)
    assert decoded["sub"] == str(user_id)
    assert decoded["typ"] == "access"
    assert "exp" in decoded and "iat" in decoded and "jti" in decoded


@pytest.mark.unit
def test_encode_and_decode_refresh_token_success():
    user_id = 456
    jti = make_jti()
    token = encode_refresh_token(user_id, jti=jti)
    decoded = decode_token(token)
    assert decoded["sub"] == str(user_id)
    assert decoded["typ"] == "refresh"
    assert decoded["jti"] == jti


@pytest.mark.unit
def test_validate_typ_raises_on_wrong_type():
    user_id = 1
    token = encode_access_token(user_id, jti=make_jti())
    decoded = decode_token(token)
    from core.exceptions import AuthenticationError

    with pytest.raises(AuthenticationError):
        validate_typ(decoded, expected_typ="refresh")


@pytest.mark.unit
def test_decode_token_invalid_signature_raises_http_401():
    # Forge token signed with a different key (self-signed HS256) to ensure InvalidTokenError
    forged = pyjwt.encode({"sub": "1", "typ": "access"}, "different-secret", algorithm="HS256")
    from core.exceptions import AuthenticationError

    with pytest.raises(AuthenticationError):
        decode_token(forged)


@pytest.mark.unit
def test_decode_token_expired_raises_http_401(monkeypatch):
    # Force very short lifetime and wait for expiration
    monkeypatch.setenv("JWT_ACCESS_MINUTES", "0")
    user_id = 1
    token = encode_access_token(user_id, jti=make_jti())
    time.sleep(1)
    from core.exceptions import AuthenticationError

    with pytest.raises(AuthenticationError):
        decode_token(token)


@pytest.mark.unit
def test_decode_token_missing_typ_treated_as_invalid():
    # Build a token manually without typ using test keypair to hit InvalidTokenError/401
    private_key, public_key = load_keypair()
    payload = {"sub": "1"}  # no typ
    tampered = pyjwt.encode(payload, private_key, algorithm="RS256")
    decoded = pyjwt.decode(tampered, public_key, algorithms=["RS256"])  # raw decode will pass
    # Our validate_typ should fail for missing/incorrect typ
    from core.exceptions import AuthenticationError

    with pytest.raises(AuthenticationError):
        validate_typ(decoded, expected_typ="access")
