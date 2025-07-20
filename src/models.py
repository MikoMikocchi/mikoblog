from database import Base, init_db
from sqlalchemy import Column, Integer, Text, String, Boolean


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    is_published = Column(Boolean, default=True)
