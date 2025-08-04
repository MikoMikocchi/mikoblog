# services/user_service.py
import logging
from sqlalchemy.orm import Session
from schemas.users import UserCreate, UserOut
from db.repositories import user_repository
from core.security import get_password_hash
from schemas.responses import SuccessResponse
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def get_user_by_id(db: Session, user_id: int) -> SuccessResponse[UserOut]:
    user = user_repository.get_user_by_id(db, user_id)
    payload = {
        "success": True,
        "data": UserOut.model_validate(user).model_dump(),
    }
    return SuccessResponse[UserOut].model_validate(payload)


def create_user(db: Session, user_data: UserCreate) -> SuccessResponse[UserOut]:
    try:
        if user_repository.get_user_by_username(db, user_data.username):
            logger.warning("Username '%s' already exists", user_data.username)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )

        if user_repository.get_user_by_email(db, user_data.email):
            logger.warning("Email '%s' already exists", user_data.email)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        hashed_password = get_password_hash(user_data.password)

        db_user = user_repository.create_user(
            db=db,
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
        )

        payload = {
            "success": True,
            "data": UserOut.model_validate(db_user).model_dump(),
        }
        return SuccessResponse[UserOut].model_validate(payload)

    except HTTPException:
        raise

    except Exception as e:
        logger.error("Unexpected error while creating user: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )
