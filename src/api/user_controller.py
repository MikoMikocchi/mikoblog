# api/user_controller.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from db.database import get_db
from schemas.users import UserCreate
from services import user_service
from schemas.responses import APIResponse

users_router = APIRouter(prefix="/users", tags=["Users"])


@users_router.post("/", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    return user_service.create_user_service(db=db, user_data=user_data)


@users_router.get("/{user_id}", response_model=APIResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    return user_service.get_user_by_id(db=db, user_id=user_id)
