import utils
import tables
from sqlalchemy import select

def isTrendyPost(id):
    #Calculates trendy status
    query=select(tables.Post.likes,tables.Post.dislikes,tables.Post.views).where(tables.Post.id==id)
    with Session(database) as session:
        likes,dislikes,view=session.execute(query).first()
        
    return views>10 and (views>=3*dislikes)
    
def checkTrendyStatus(id): #Calculates if trendy, adds/removes usertype from mask as needed, commits to table, and returns True or False
    pass