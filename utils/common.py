#Should be imported by all relevant files

import sys,os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from flask import Flask, request
from flask_cors import CORS

database = create_engine("sqlite:///test_db.db")

import utils.users

app=Flask("backend_server")

CORS(app)

import functools
def fromStringList(string):
    return string.removeprefix(" ").removesuffix(" ").split(" ")

def toStringList(lst):
    return " "+(" ".join(lst))+" "

def appendToStringList(lst,val):
    lst=fromStringList(lst)
    lst.append(str(val))
    return toStringList(lst)
 
def authenticate(func):
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