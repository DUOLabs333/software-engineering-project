#Should be imported by all relevant files

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from flask import Flask, request

database = create_engine("sqlite:///test_db.db")

app=Flask("backend_server")

def fromStringList(string):
    return string.split(" ")

def toStringList(lst):
    return " ".join(lst)

def getUser(uid):
    with Session(common.database) as session:
        query=select(tables.User).where(tables.User.id==uid)
        return session.scalars(query).first()
        
def hasAccess(uid):
    hash=request.get_data(as_text=True)
    
    user=getUser(uid)
    return (user is not None) and (hash==user.password_hash)