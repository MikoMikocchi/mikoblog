from datetime import datetime, timedelta, timezone
import uuid
from typing import Any, Dict, Tuple

import jwt
from fastapi import HTTPException, status

from .jwt_keys import load_keypair
from .config import settings


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def make_jti() -> str:
    """Generate a new UUID4 string to be used as JWT JTI."""
    return str(uuid.uuid4())


def _get_alg_and_exp() -> Tuple[str, int, int]:
    # Параметры экспирации из .env/настроек
    alg = (
        getattr(settings.security, "algorithm", "RS256")
        if getattr(settings, "security", None)
        else "RS256"
    )
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

    payload: Dict[str, Any] = {
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

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": jti,
        "typ": "refresh",
    }
    token = jwt.encode(payload, private_key, algorithm=alg)
    return token


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate the RS256 access/refresh token signature.
    PyJWT exceptions are mapped to HTTP 401.
    """
    try:
        _, public_key = load_keypair()
        # Алгоритм ожидаем RS256 (по умолчанию), запрещаем none/другие
        decoded: Dict[str, Any] = jwt.decode(token, public_key, algorithms=["RS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def validate_typ(decoded: Dict[str, Any], expected_typ: str) -> None:
    """
    Ensure the claim 'typ' matches the expected value ("access" or "refresh").
    """
    typ = decoded.get("typ")
    if typ != expected_typ:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token type: expected {expected_typ}",
            headers={"WWW-Authenticate": "Bearer"},
        )
