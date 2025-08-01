# schemas/post.py
from pydantic import BaseModel, Field
from datetime import datetime
from schemas.users import UserOut


class PostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    content: str = Field(..., min_length=1, max_length=10000)
    is_published: bool = True


class PostOut(PostBase):
    id: int
    created_at: datetime
    updated_at: datetime
    author: UserOut

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    content: str = Field(..., min_length=1, max_length=10000)
    is_published: bool = True
    author_id: int
