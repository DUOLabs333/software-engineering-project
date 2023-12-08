#Should be imported by all relevant files

import sys,os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from flask import Flask, request
from flask_cors import CORS

database = create_engine("sqlite:///test_db.db")

import utils.users as users

app=Flask("backend_server")

def getItem(cls,id,session=None):
    session_exists=True
    if session is None:
        session_exists=False #Have to make one
        session=Session(database,expire_on_commit=False) #Can be used outside session
        
    query=select(cls).where(cls.id==id)
    result=session.scalars(query).one_or_none()
    
    if not session_exists:
        session.close() 
    return result
    
def post_wrap(func):
    def wrapper(*args,**kwargs):
        key="methods"
        kwargs[key]=kwargs.get(key,[])
        if key in kwargs:
            if "POST" not in kwargs[key]:
                kwargs[key].append("POST")
        return func(*args,**kwargs)
    return wrapper

setattr(app,"route",post_wrap(app.route))
            
CORS(app)

import functools
def fromStringList(string):
    return string.removeprefix(" ").removesuffix(" ").split(" ") if string!="" else []

def toStringList(lst):
    return "" if lst==[] else " "+(" ".join(lst))+" "

def appendToStringList(lst,val):
    lst=fromStringList(lst)
    lst.append(str(val))
    return toStringList(lst)

def removeFromStringList(lst,val):
    lst=fromStringList(lst)
    lst.remove(str(val))
    return toStringList(lst)
 
def authenticate(func): #There is a possible race-condition with two etc. /likes, where two different processes will be working on two different lists, and write two lists. The only way to do this is with dynamic Locks (one for each user) --- Subclass defaultdict to only delete when the lock's.__acquires<=0. Subclass Lock to keep track of __acquires. It doesn't totally eliminate race conditions, but it lowers the chance significantly. However, this isn't a thing in Python (Locks are gained through inheritance). Other languages like Go do not have this issue (they use threading, so sharing memory is easy).
   @functools.wraps(func)
   def wrapper(*args,**kwargs):
       uid=request.json["uid"]
       hash=request.json["key"]
       
       user=users.getUser(uid)
       
       has_access=(user is not None) and (hash==user.password_hash)
       
       if not has_access:
           result={"error":"ACCESS_DENIED"}
           return result
       else:
           return func(*args,**kwargs)
   return wrapper

def last(lst):
    if len(lst)==0:
        return None
    else:
        return lst[-1]