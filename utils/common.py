#Should be imported by all relevant files

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from flask import Flask, request

database = create_engine("sqlite:///test_db.db")

import utils.users

app=Flask("backend_server")

def fromStringList(string):
    return string.removeprefix(" ").removesuffix(" ").split(" ")

def toStringList(lst):
    return " "+(" ".join(lst))+" "

def hasAccess(uid):
    hash=request.get_data(as_text=True)
    
    user=users.getUser(uid)
    return (user is not None) and (hash==user.password_hash)