# api/user_controller.py
from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.orm import Session

from db.database import get_db
from schemas.users import UserCreate, UserOut
from services import user_service
from schemas.responses import SuccessResponse

users_router = APIRouter(prefix="/users", tags=["Users"])


@users_router.get("/{user_id}", response_model=SuccessResponse[UserOut])
async def get_user(user_id: int, db: Session = Depends(get_db)):
    return user_service.get_user_by_id(db=db, user_id=user_id)


@users_router.post(
    "",
    response_model=SuccessResponse[UserOut],
    status_code=status.HTTP_201_CREATED,
)
async def create_user(user_data: UserCreate = Body(...), db: Session = Depends(get_db)):
    return user_service.create_user(db=db, user_data=user_data)
