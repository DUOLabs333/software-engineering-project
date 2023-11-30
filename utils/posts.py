import utils.common as common
import utils.tables as tables
from sqlalchemy import select
from sqlalchemy import desc
from sqlalchemy.orm import Session
import time
from routes.posts import lock

def getPost(post_id,session=None):
    session_exists=True
    if session is None:
        session_exists=False #Have to make one
        session=Session(common.database,expire_on_commit=False) #Can be used outside session
        
    query=select(tables.Post).where(tables.Post.id==post_id)
    result=session.scalars(query).first()
    
    if session_exists:
        session.close() 
    return result

def createPost(data):
    post=tables.Post()
   
    with Session(common.database) as session:
        lock.acquire()
        
        post.id=(session.scalars(select(tables.Post.id).order_by(desc(tables.Post.id)).limit(1)).first() or 0)+1 #Get next biggest id
        post.time_posted=int(time.time())
        
        for attr in ["author","text"]:
            setattr(post,attr,data[attr])
        
        post.keywords=common.toStringList(data.get("keywords",[]))
        
        post.parent_post=data.get("parent_post",None)
        post.type=data.get("post_type","POST")
        
        for attr in ["views","likes","dislikes"]:
            setattr(post,attr,0)
        
        for attr in ["has_picture","has_video"]:
            setattr(post,attr,data.get(attr,False)) #Need to find a way to parse markdown for links --- maybe use regex for ![alt-text](link)
        
        session.add(post)
        session.commit()
        lock.release()
        return post.id