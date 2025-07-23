from pydantic import BaseModel


class PostBase(BaseModel):
    title: str
    content: str
    is_published: bool = True


class PostOut(PostBase):
    id: int

    class Config:
        from_attributes = True
