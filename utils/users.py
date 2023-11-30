from utils import tables, common
from sqlalchemy import select
from sqlalchemy.orm import Session

def getUser(user_id,session=None):
    session_exists=True
    if session is None:
        session_exists=False #Have to make one
        session=Session(common.database,expire_on_commit=False) #Can be used outside session
        
    query=select(tables.User).where(tables.User.id==user_id)
    result=session.scalars(query).first()
    
    if session_exists:
        session.close() 
    return result


def is_trendy(user):
    #Define conditions, so you can check whether it should be trnedy at evey sub/unsub, view like/dislike, etc by someone else. If so, add TU to type. If not, remove TU. Also, use select as needed. Check for warnings (must have <=3)
    
    result=True #Start with the assumption that it is true
    
    with Session(common.database) as session:
        query=select(tables.User.id).where(tables.User.has_followed(user.id))
        result &= (len(session.scalars(query).all())>10) #Have >10 followers
        
        likes=0
        dislikes=0
        query=select(tables.Post.likes,tables.Post.dislikes).where(tables.Post.author==user.id)
        
        for row in session.execute(query):
            likes+=row[0]
            dislikes+=row[1]
        
        result&=((likes>10*dislikes) or user.tips>100) #received >$100 in tips or have >10 more likes than dislikes
        
        query=select(tables.Post.id).where((tables.Post.author==user.id) & (tables.Post.is_trendy==True))
        
        result &= (len(session.scalars(query).all())>=2) #wrote at least two trendy posts
        
        query=select(tables.Post.id).where((tables.Post.type=="WARNING") & (tables.Post.parent_post==user.inbox))
        
        result &= (len(session.scalars(query).all())<=3) #Must have at most three warnings
        
    return result

def update_trendy_status(user):
    with Session(common.database) as session:
        user=getUser(user.id,session)
        if is_trendy(user):
            user.addType(user.TRENDY)
        else:
            user.removeType(user.TRENDY)
        session.commit()