from datetime import datetime
from sqlalchemy import (Column, Integer, String, DateTime, Boolean,
                        Numeric, ForeignKey, Text, Enum)
from sqlalchemy.orm import declarative_base, relationship
from enum import Enum as PyEnum

Base = declarative_base()

class PostStatus(PyEnum):
    PLANNED = "planned"
    POSTED = "posted"
    SKIPPED = "skipped"
    ERROR = "error"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True, nullable=False)
    vk_group_id = Column(String)
    vk_token = Column(String)
    theme = Column(String)
    style = Column(String)
    posts_per_day = Column(Numeric, default=2)
    tariff = Column(String)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    text = Column(Text)
    image_url = Column(String)
    scheduled_at = Column(DateTime)
    status = Column(Enum(PostStatus), default=PostStatus.PLANNED)
    posted_at = Column(DateTime)
    user = relationship("User", back_populates="posts")

User.posts = relationship("Post", order_by=Post.scheduled_at, back_populates="user")