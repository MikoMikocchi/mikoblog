from sqlalchemy.orm import Session
from schemas.users import UserCreate, UserOut
from db.repositories import user_repository
from core.security import get_password_hash
from schemas.responses import APIResponse
from fastapi import HTTPException, status


def create_user(db: Session, user_data: UserCreate):

    if user_repository.get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    if user_repository.get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    hashed_password = get_password_hash(user_data.password)

    db_user = user_repository.create_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
    )

    return APIResponse(
        status="success", content=UserOut.model_validate(db_user).model_dump()
    )


def get_user_by_id(db: Session, user_id: int):
    user = user_repository.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return APIResponse(
        status="success", content=UserOut.model_validate(user).model_dump()
    )
