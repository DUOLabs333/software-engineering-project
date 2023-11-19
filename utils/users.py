import functools
from sqlalchemy.orm import Session
from sqlalchemy import select
from utils import common, tables
SURFER=0
ORDINARY=1
TRENDY=2
CORPORATE=3
SUPER = 4
BANNED = 5

def addType(mask,type):
    if isinstance(type,list):
        type=functools.reduce(lambda x,y: x | y,type)
        
    if checkForType(mask, CORPORATE) or checkForType(mask, SUPER): #SUPER and CORPORATE Users can not become TRENDY
        type=removeType(type, TRENDY)
    elif checkForType(type, CORPORATE) or checkForType(type, SUPER): #If TRENDY users become CORPORATE or SUPER, they can no longer be TRENDY
        mask=removeType(mask, TRENDY)
        
    return mask | (1<<type)

def removeType(mask,type):
    if isinstance(type,list):
        type=functools.reduce(lambda x,y: x | y,type)
        
    return mask & ~(1<<type)

def checkForType(mask,type):
    return bool(mask & (1<<type)==type)

def listTypes(mask): #Lists all types that are present in mask
    result=[]
    
    for pos in globals():
        if not(pos.isupper() and isinstance(globals()[pos],int)):
            continue
        if checkForType(mask, globals()[pos]):
         result.append(pos)
    
    return result

def getUser(user_id):
    with Session(common.database) as session:
        query=select(tables.User).where(tables.User.id==user_id)
        return session.scalars(query).first()