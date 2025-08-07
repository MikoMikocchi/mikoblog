from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from src.core.jwt import encode_refresh_token, make_jti
from src.db.repositories import refresh_token_repository as rt_repo


def issue_refresh_for_user(
    db: Session,
    user_id: int,
    *,
    user_agent: str | None = "pytest",
    ip: str | None = "127.0.0.1",
    ttl_days: int = 1,
) -> tuple[str, str]:
    """
    Creates a refresh token record in the database and returns a tuple (jti, refresh_jwt).
    """
    now = datetime.now(tz=UTC)
    expires = now + timedelta(days=ttl_days)
    jti = make_jti()

    rt_repo.create(
        db=db,
        user_id=user_id,
        jti=jti,
        issued_at=now,
        expires_at=expires,
        user_agent=user_agent,
        ip=ip,
    )

    refresh_jwt = encode_refresh_token(user_id, jti=jti)
    return jti, refresh_jwt
