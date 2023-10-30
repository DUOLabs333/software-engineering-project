from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

# declarative base class
class BaseTable(DeclarativeBase):
    pass

class User(BaseTable):
    __tablename__ = "USERS"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str]
    password_hash: Mapped[str]
    creation_time: Mapped[int]
    user_type: Mapped[int]
    following: Mapped[str]
    followers: Mapped[str]
    balance: Mapped[float]
    tips: Mapped[float]
    avatar: Mapped[str]
    liked_posts: Mapped[str]
    inbox: Mapped[int]

class Post(BaseTable):
    __tablename__ = "POSTS"
    id: Mapped[int] = mapped_column(primary_key=True)
    author: Mapped[int] = mapped_column(index=True)
    time_posted: Mapped[int]
    keywords: Mapped[str]
    views: Mapped[int]
    likes: Mapped[int]
    dislikes: Mapped[int]
    has_picture: Mapped[bool]
    has_video: Mapped[bool]
    post_type: Mapped[int]
    parent_post: Mapped[int] = mapped_column(nullable=True)

class JobApplication(BaseTable):
    __tablename__="JOBS"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    author: Mapped[int]
    questions: Mapped[str]
    time_posted: Mapped[int]
    due_date: Mapped[int] = mapped_column(nullable=True)
    
