from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

import time
# declarative base class
class BaseTable(DeclarativeBase):
    pass

class User(BaseTable):
    __tablename__ = "USERS"

    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    username: Mapped[str]
    password_hash: Mapped[str]
    creation_time: Mapped[int]
    user_type: Mapped[int]
    following: Mapped[str]
    blocked: Mapped[str]
    tips: Mapped[float]
    avatar: Mapped[str]
    liked_posts: Mapped[str]
    disliked_posts: Mapped[str]
    inbox: Mapped[int]
    profile: Mapped[int]


class Post(BaseTable):
    __tablename__ = "POSTS"
    id: Mapped[int] = mapped_column(primary_key=True)
    author: Mapped[int] = mapped_column(index=True)
    time_posted: Mapped[int]
    keywords: Mapped[str]
    title: Mapped[str] = mapped_column(nullable=True)
    text: Mapped[str]
    views: Mapped[int]
    likes: Mapped[int]
    dislikes: Mapped[int]
    has_picture: Mapped[bool]
    has_video: Mapped[bool]
    post_type: Mapped[int]
    parent_post: Mapped[int] = mapped_column(nullable=True,index=True)
    
    @hybrid_property
    def is_trending(self):
        self.views>10 & (self.views>=3*self.dislikes)
    
    @hybrid_property
    def trending_ranking(self):
        return self.views/self.dislikes
        

class JobApplication(BaseTable):
    __tablename__="JOBS"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    author: Mapped[int]
    questions: Mapped[str]
    time_posted: Mapped[int]
    due_date: Mapped[int] = mapped_column(nullable=True)
    
class Balance(BaseTable):
    __tablename__="BALANCE"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    balance: Mapped[float]

class Upload(BaseTable):
    __tablename__="UPLOADS"
    
    id: Mapped[int]= mapped_column(primary_key=True,autoincrement=True)
    path: Mapped[str]
    type: Mapped[str]