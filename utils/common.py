#Should be imported by all relevant files

import sys,os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")))

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

def hasAccess():
    uid=request.json["uid"]
    hash=request.json["key"]
    
    user=users.getUser(uid)
    return (user is not None) and (hash==user.password_hash)