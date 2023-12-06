from utils import tables, common, balance
from sqlalchemy import select, func
from sqlalchemy.orm import Session

def getUser(user_id,session=None):
    session_exists=True
    if session is None:
        session_exists=False #Have to make one
        session=Session(common.database,expire_on_commit=False) #Can be used outside session
        
    query=select(tables.User).where(tables.User.id==user_id)
    result=session.scalars(query).one_or_none()
    
    if not session_exists:
        session.close() 
    return result


def is_trendy(user):
    #Define conditions, so you can check whether it should be trnedy at evey sub/unsub, view like/dislike, etc by someone else. If so, add TU to type. If not, remove TU. Also, use select as needed. Check for warnings (must have <=3)
    
    result=True #Start with the assumption that it is true
    
    with Session(common.database) as session:
        query=select(tables.User.id).where(tables.User.has_followed(user.id))
        result &= (len(session.scalars(query).all())>10) #Have >10 followers
        
        query=select(func.sum(tables.Post.likes)/(func.sum(tables.Post.dislikes)+1)).where(tables.Post.author==user.id)
        
        ratio=session.scalars(query).one_or_none() or 0
        result&=((user.tips>100) or (ratio>10)) #received >$100 in tips or have >10 more likes than dislikes
        
        query=select(tables.Post.id).where((tables.Post.author==user.id) & (tables.Post.is_trendy==True))
        
        result &= (len(session.scalars(query).all())>=2) #wrote at least two trendy posts
        
        query=select(tables.Post.id).where((tables.Post.type=="WARNING") & (tables.Post.parent_post==user.inbox))
        
        result &= (len(session.scalars(query).all())<3) #Must have less than warnings
        
        result &= user.hasType(user.ORDINARY)
        
    return result

def update_trendy_status(user):
    with Session(common.database) as session:
        user=getUser(user.id,session)
        if is_trendy(user):
            user.addType(user.TRENDY)
        else:
            user.removeType(user.TRENDY)
        session.commit()

def get_user_warnings_count(user):    #returns warnings for any given user
    with Session(common.database) as session:
            warnings_count= user.warnings
            return warnings_count
    
def handle_three_warnings(user):
    int amount =20
    with Session(common.database) as session:
        user=getUser(user.id,session)
        # Check if user is an ORDINARY User (OU) or CORPORATE User (CU)
        if user.hasType(user.ORDINARY) or user.hasType(user.CORPORATE):


            #logic for if they want to pay or not
            balance.RemoveFromBalance(user.id,amount)  #remove $20 from user balance
            #imagine an else statement here for if they want to pay or not
        
            if user.hasType(user.ORDINARY):
                user.removeType(user.ORDINARY)  #remove typing
            if user.hasType(user.CORPORATE)     
                user.removeType(user.CORPORATE) #remove typing
            user.addType(user.BANNED) #become banned


         if user.hasType(user.TRENDY):
            user.removeType(user.TRENDY)
            