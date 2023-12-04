from utils import tables, common

from sqlalchemy import select
from sqlalchemy.orm import Session

def GetBalance(id):
    with Session(common.database) as session:
        query=select(tables.Balance.balance).where(tables.Balance.id==id)
        return session.scalars(query).first()

def AddToBalance(id,amount):
    with Session(common.database) as session:
        query=select(tables.Balance).where(tables.Balance.id==id)
        balance=session.scalars(query).first()
        
        balance.balance+=amount
        
        session.commit()
        
        return balance.balance

def RemoveFromBalance(id,amount):
    with Session(common.database) as session:
        query=select(tables.Balance).where(tables.Balance.id==id)
        balance=session.scalars(query).first()
        
        if balance.balance < amount:
            return None
            
        balance.balance-=amount
        
        session.commit()
        
        return balance.balance

def RegisterBalance(id):
    balance=tables.Balance()
    balance.balance=0
    balance.id=id
    with Session(common.database) as session:
        session.add(balance)
        session.commit()

def import_from_CC(data):
    error=AddToBalance(data["uid"],data["amount"])
    if error<0:
        return error
    return 0 #Since this is a school project, we're not going to actually implement CC verification/ checking for balance

def export_to_CC(data):
    result=RemoveFromBalance(data["uid"],data["amount"])
    if result==-1:
        return result
    #Return -2 if some other error occurred
    return 0 #See above