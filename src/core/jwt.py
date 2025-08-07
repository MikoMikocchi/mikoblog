from datetime import UTC, datetime, timedelta
from typing import Any
import uuid

import jwt

from core.exceptions import AuthenticationError

from .jwt_keys import load_keypair


def _now_utc() -> datetime:
    return datetime.now(UTC)


def make_jti() -> str:
    """Generate a new UUID4 string to be used as JWT JTI."""
    return str(uuid.uuid4())


def _get_alg_and_exp() -> tuple[str, int, int]:
    # Expiration parameters from env; algorithm is fixed to RS256
    alg = "RS256"
    access_minutes = int(__import__("os").getenv("JWT_ACCESS_MINUTES", "15"))
    refresh_days = int(__import__("os").getenv("JWT_REFRESH_DAYS", "7"))
    return alg, access_minutes, refresh_days


def encode_access_token(user_id: int, *, jti: str | None = None) -> str:
    """
    Create an access token with claims: sub, iat, exp, jti, typ=access.
    """
    private_key, _ = load_keypair()
    alg, access_minutes, _ = _get_alg_and_exp()
    issued_at = _now_utc()
    expires_at = issued_at + timedelta(minutes=access_minutes)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": jti or make_jti(),
        "typ": "access",
    }
    token = jwt.encode(payload, private_key, algorithm=alg)
    return token


def encode_refresh_token(user_id: int, *, jti: str) -> str:
    """
    Create a refresh token with claims: sub, iat, exp, jti, typ=refresh.
    """
    private_key, _ = load_keypair()
    alg, _, refresh_days = _get_alg_and_exp()
    issued_at = _now_utc()
    expires_at = issued_at + timedelta(days=refresh_days)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": jti,
        "typ": "refresh",
    }
    token = jwt.encode(payload, private_key, algorithm=alg)
    return token


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate the RS256 access/refresh token signature.
    PyJWT exceptions are mapped to HTTP 401.
    """
    try:
        _, public_key = load_keypair()
        # Enforce RS256 explicitly and disallow others
        decoded: dict[str, Any] = jwt.decode(token, public_key, algorithms=["RS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token expired") from None
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token") from None


def validate_typ(decoded: dict[str, Any], expected_typ: str) -> None:
    """
    Ensure the claim 'typ' matches the expected value ("access" or "refresh").
    """
    typ = decoded.get("typ")
    if typ != expected_typ:
        raise AuthenticationError(f"Invalid token type: expected {expected_typ}")
