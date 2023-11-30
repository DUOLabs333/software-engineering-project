from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from utils import users
from sqlalchemy import func, select

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
    type: Mapped[int]
    following: Mapped[str]
    blocked: Mapped[str]
    tips: Mapped[float]
    avatar: Mapped[str]
    liked_posts: Mapped[str]
    disliked_posts: Mapped[str]
    inbox: Mapped[int]
    profile: Mapped[int]
    applied: Mapped[int]
    
    SURFER=0
    ORDINARY=1
    TRENDY=2
    CORPORATE=3
    SUPER = 4
    BANNED = 5
    
    def addType(self,_type):
        print(self.type)
        if (self.hasType(self.CORPORATE) or self.hasType(self.SUPER)) and _type==self.TRENDY: #SUPER and CORPORATE Users can not become TRENDY
            return
        elif _type in [self.CORPORATE,self.SUPER]: #If TRENDY users become CORPORATE or SUPER, they can no longer be TRENDY
            self.removeType(self.TRENDY)
            
        self.type|= (1<<_type)
    
    def removeType(self,_type):
        self.type&= ~(1<<type)
    
    @hybrid_method
    def hasType(self,_type):
        return (self.type & (1<<_type))==_type
    
    def listTypes(self):
        result=[]
        for attr in dir(self):
            value=getattr(self,attr)
            if not(attr.isupper() and (not attr.startswith("_")) and (not attr.endswith("_")) and isinstance(value,int)):
                continue
            if self.hasType(value):
                result.append(attr)
        return result
    
    @hybrid_method
    def has_blocked(self,id):
        return f" {id} " in self.blocked
    
    @has_blocked.expression
    def has_blocked(cls,id):
        return cls.blocked.contains(" "+str(id)+" ")
    
    @hybrid_method
    def has_followed(self,id):
        return f" {id} " in self.following
    
    @has_blocked.expression
    def has_followed(cls,id):
        return cls.following.contains(" "+str(id)+" ")
    
    def update_trendy_status(self):
        users.update_trendy_status(self)
    
    @hybrid_property
    def trendy_ranking(self):
        return 0 #Nothing to return --- everything is implemented in the expression
    
    @trendy_ranking.expression
    def trendy_ranking(cls):
        return func.coalesce(select(func.sum(Post.likes)/(func.sum(Post.dislikes)+1)).where(Post.author==cls.id),0)

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
    type: Mapped[int]
    parent_post: Mapped[int] = mapped_column(nullable=True,index=True)
    hidden: Mapped[bool] = mapped_column(default=False)
    
    @hybrid_property
    def is_trendy(self):
        return self.views>10 & (self.likes>=3*self.dislikes) & (self.type=="POST") & (self.time_posted>time.time()-5*60*60)
    
    @hybrid_property
    def trendy_ranking(self):
        return self.views/(self.dislikes+1)

class Balance(BaseTable):
    __tablename__="BALANCE"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    balance: Mapped[float]

class Upload(BaseTable):
    __tablename__="UPLOADS"
    
    id: Mapped[int]= mapped_column(primary_key=True,autoincrement=True)
    path: Mapped[str]
    type: Mapped[str]