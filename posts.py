import utils
import tables
from sqlalchemy import select
import time

def isTrendyPost(id):
    #Calculates trendy status
    query=select(tables.Post.likes,tables.Post.dislikes,tables.Post.views).where(tables.Post.id==id)
    with Session(database) as session:
        likes,dislikes,view=session.scalars(query).first()
        
    return views>10 and (views>=3*dislikes)
    
def checkTrendyStatus(id): #Calculates if trendy, adds/removes usertype from mask as needed, commits to table, and returns True or False
    limit=datetime.utcnow().time()-(5*60*60)
    
    query=select(tables.Post.id,tables.Post.likes,tables.Post.dislikes).where((tables.Post.author==id) & (datetime.utcnow().time()-tables.Post.time_posted<5*60*60))
    
    trendy_posts=0
    likes=0
    dislikes=0
    with Session(database) as session:
        for result in session.scalars(query):
            _id,_likes,_dislikes=result
            if isTrendyPost(_id):
                trendy_posts+=1
            likes+=_likes
            dislikes+=_dislikes
        
        user=session.scalars(select(tables.User).where(tables.User.id==id)).first()
        
        return user.followers>10 and (user.tips>100 or likes-dislikes>10) and trendy_posts>=2
    
    