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
        if balance is None:
            return balance
        
        balance.balance+=amount
        
        session.commit()
        
        return balance.balance

def RemoveFromBalance(id,amount):
    with Session(common.database) as session:
        query=select(tables.Balance).where(tables.Balance.id==id)
        balance=session.scalars(query).first()
        if balance is None:
            return balance
        
        if balance.balance < amount:
            return -1
            
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