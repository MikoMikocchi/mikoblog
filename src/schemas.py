from pydantic import BaseModel, Field


class PostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    content: str = Field(..., min_length=1, max_length=10000)
    is_published: bool = True


class PostOut(PostBase):
    id: int

    class Config:
        from_attributes = True
