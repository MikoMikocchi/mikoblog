from jwt import ExpiredSignatureError, InvalidTokenError
import pytest

from src.core import jwt
from src.core.exceptions import AuthenticationError


@pytest.mark.unit
async def test_decode_token_expired_signature(monkeypatch):
    # Mock jwt.decode to raise ExpiredSignatureError
    def mock_decode(*args, **kwargs):
        raise ExpiredSignatureError("Signature has expired")

    monkeypatch.setattr("src.core.jwt.jwt.decode", mock_decode)

    with pytest.raises(AuthenticationError) as exc_info:
        jwt.decode_token("expired_token")

    assert str(exc_info.value) == "Token expired"


@pytest.mark.unit
async def test_decode_token_invalid_token(monkeypatch):
    # Mock jwt.decode to raise InvalidTokenError
    def mock_decode(*args, **kwargs):
        raise InvalidTokenError("Invalid token")

    monkeypatch.setattr("src.core.jwt.jwt.decode", mock_decode)

    with pytest.raises(AuthenticationError) as exc_info:
        jwt.decode_token("invalid_token")

    assert str(exc_info.value) == "Invalid token"


@pytest.mark.unit
async def test_validate_typ_invalid_type():
    decoded = {"typ": "refresh"}

    with pytest.raises(AuthenticationError) as exc_info:
        jwt.validate_typ(decoded, expected_typ="access")

    assert str(exc_info.value) == "Invalid token type: expected access"


@pytest.mark.unit
async def test_validate_typ_missing_typ():
    decoded = {}

    with pytest.raises(AuthenticationError) as exc_info:
        jwt.validate_typ(decoded, expected_typ="access")

    assert str(exc_info.value) == "Invalid token type: expected access"
