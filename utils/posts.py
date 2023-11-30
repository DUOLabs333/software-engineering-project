import utils.common as common
import utils.tables as tables
from sqlalchemy import select
from sqlalchemy import desc
from sqlalchemy.orm import Session
import time
import utils.users
from routes.posts import lock

def checkTrendyStatus(id): #Calculates if trendy, adds/removes usertype from mask as needed, commits to table, and returns True or False. May need to run in a loop every n hours (effectively caching it), in the background, or maybe only when accessing Trendy-only information.
    limit=datetime.utcnow().time()-(5*60*60)
    
    query=select(tables.Post).where((tables.Post.author==id) & (datetime.utcnow().time()-tables.Post.time_posted<5*60*60))
    
    trendy_posts=0
    likes=0
    dislikes=0
    with Session(common.database) as session:
        for result in session.scalars(query):
            if result.is_trending:
                trendy_posts+=1
            likes+=result.likes
            dislikes+=result.dislikes
        
        user=session.scalars(select(tables.User).where(tables.User.id==id)).first()
        
        isTrendy=user.followers>10 and (user.tips>100 or likes-dislikes>10) and trendy_posts>=2
        
        if not isTrendy:
            user.user_type = users.removeType(user.user_type, users.TRENDY)
        else:
            user.user_type=users.addType(user.user_type,users.TRENDY)
            
        session.commit()
        
        return isTrendy
    
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

def createPost(type,data):
    post=tables.Post()
   
    with Session(common.database) as session:
        lock.acquire()
        
        post.id=(session.scalars(select(tables.Post.id).order_by(desc(tables.Post.id)).limit(1)).first() or 0)+1 #Get next biggest id
        post.time_posted=int(time.time())
        
        for attr in ["author","text"]:
            setattr(post,attr,data[attr])
        
        post.keywords=common.toStringList(data.get("keywords",[]))
        
        post.parent_post=data.get("parent_post",None)
        post.post_type=data.get("post_type","POST")
        
        for attr in ["views","likes","dislikes"]:
            setattr(post,attr,0)
        
        for attr in ["has_picture","has_video"]:
            setattr(post,attr,data.get(attr,False)) #Need to find a way to parse markdown for links --- maybe use regex for ![alt-text](link)
        
        session.add(post)
        session.commit()
        lock.release()
        return post.id