from sqlalchemy.orm import Session

from src.core.security import get_password_hash
from src.db.models.user import User


def create_user(
    db: Session,
    *,
    username: str = "user1",
    email: str = "user1@example.com",
    password: str = "Str0ng!Passw0rd",
    role: str = "user",
) -> User:
    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        role=role,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


def create_admin(
    db: Session,
    *,
    username: str = "admin",
    email: str = "admin@example.com",
    password: str = "Admin!Passw0rd",
) -> User:
    return create_user(
        db,
        username=username,
        email=email,
        password=password,
        role="admin",
    )
