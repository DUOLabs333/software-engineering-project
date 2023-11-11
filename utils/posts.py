import utils.common
import utils.tables
from sqlalchemy import select
import time
import utils.users
from datetime import datetime
current_utc_time = datetime.utcnow()

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
    
def getPost(post_id):
    with Session(common.database) as session:
        query=select(tables.Post).where(tables.Post.id==post_id)
        return session.scalars(query).first()