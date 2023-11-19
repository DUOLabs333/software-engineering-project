import tables, common

import braintree

gateway = braintree.BraintreeGateway(
  braintree.Configuration(
    environment=braintree.Environment.Sandbox,
    merchant_id='prvgcb88ztrbh7tm',
    public_key='4hzdkcwrb5ktpdrz',
    private_key='663c2fa5b4e345c5dba2e81e5541ba2f'
  )
)

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy import desc

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

def tipping(id1,id2,amount):
    with Session(common.database) as session:
        query1=select(tables.Balance).where(tables.Balance.id==id1)
        query2=select(tables.Balance).where(tables.Balance.id==id2)
        balance1=session.scalars(query1).first()
        balance2=session.scalars(query2).first()
        if balance1 is None:
            return balance1
        if balance2 is None:
            return balance2
        if balance1.balance < amount:
            return -1
        else:
            RemoveFromBalance(id1,amount)
            AddToBalance(id2,amount)
        session.commit()
        
        return balance1.balance