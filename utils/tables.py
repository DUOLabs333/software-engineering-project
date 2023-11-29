from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method

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
    
    SURFER=0
    ORDINARY=1
    TRENDY=2
    CORPORATE=3
    SUPER = 4
    BANNED = 5
    
    def addType(self,_type):
        if (self.hasType(self.CORPORATE) or self.hasType(self.SUPER)) and _type==TRENDY: #SUPER and CORPORATE Users can not become TRENDY
            return
        elif _type in [CORPORATE,SUPER]: #If TRENDY users become CORPORATE or SUPER, they can no longer be TRENDY
            self.removeType(self.TRENDY)
            
        self.user_type|= (1<<_type)
    
    def removeType(self,_type):
        self.user_type&= ~(1<<type)
    
    @hybrid_method
    def hasType(self,_type):
        return (self.user_type & (1<<_type))==_type
    
    def listTypes(self):
        result=[]
        for attr in dir(self):
            value=getattr(self,attr)
            if not(attr.isupper() and (not attr.startswith("_")) and (not attr.endswith("_")) and isinstance(value,int)):
                continue
            if self.hasType(value):
                result.append(attr)
        return result
         
    def is_trendy(self):
        #Define conditions, so you can check whether it should be trnedy at evey sub/unsub, view like/dislike, etc by someone else. If so, add TU to type. If not, remove TU. Also, use select as needed. Check for warnings (must have <=3 
        self.views>10 & (self.views>=3*self.dislikes) & (self.post_type=="POST")
    
    

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
        self.views>10 & (self.views>=3*self.dislikes) & (self.post_type=="POST")
    
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