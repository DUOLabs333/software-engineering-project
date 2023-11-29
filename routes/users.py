from utils import common, tables
from utils.common import app

from utils import users, posts

from flask import request

from sqlalchemy import select
from sqlalchemy import desc

from sqlalchemy.orm import Session
import multiprocessing
import base64, json, time

import random
import string 

lock=multiprocessing.Lock() #We lock not because of the IDs (autoincrement is enough), but because of the usernames

#Lock table when deleting, creating, and renaming
#To get followers, we must use table.User.following.contains(f" {user.id} ")

def checkIfUsernameExists(username): #You must have the USERS database locked, and you must not unlock it until you placed the (new) username into the database
    with Session(common.database) as session:
        return session.scalars(select(tables.User.id).where(tables.User.username==username)).first() is not None

#CRUD: Create, Read, Update, Delete

@app.route("/users/create", methods = ['POST'])
def create():
    result={}
    anonymous=request.json.get("anonymous",False)
    
    lock.acquire()
    
    if anonymous:
        while True:
            request.json["username"]="anon_"+random.randint(0,10000000)
            if not checkIfUsernameExists(request.json["user"]):
                break
        result["password"]=''.join(random.choices(string.ascii_uppercase + string.digits, k=256))
    
    username=request.json["username"]
    
    if checkIfUsernameExists(username):
        lock.release()
        result["error"]="USERNAME_EXISTS"
        return result
        
    user=tables.User()
    
    for attr in ["username","password_hash"]:
        setattr(user,attr,request.json[attr])
    
    user.creation_time=int(time.time())
    
    user_type=request.json.get("user_type","SURFER")
    
    if user_type not in ["SURFER","ORDINARY","CORPORATE"]:
        result["error"]="INVALID_USER_TYPE"
        return result
    
    user.user_type=0   
    user.addType(getattr(user,user_type))
    
    for attr in ["following","blocked","liked_posts","disliked_posts"]:
        setattr(user,attr,common.toStringList([]))
    
    for attr in ["tips"]:
        setattr(user,attr,0)
    
    user.avatar=""
    
    with Session(common.database) as session:
        user.inbox=0 #Placeholder, so we can add it without it failing the 'NOT NULL' constraint
        user.profile=0 #See above
        
        session.add(user)
        session.commit()
        
        user.inbox=posts.createPost("INBOX",{"author": user.id, "text":"This is your inbox.","keywords":[]})
        user.profile=posts.createPost("PROFILE",{"author": user.id, "text":"This is your profile.","keywords":[]})
        session.commit()
        
        lock.release()
        result["id"]=user.id
        if anonymous:
            result["password_hash"]=user.password_hash
    return result

@app.route("/users/info", methods = ['POST'])
@common.authenticate
def info():
    result={}
    id=request.json.get("id",uid) #By default, use the current uid
    
    with Session(common.database) as session:
        
        user=users.getUser(id)
        if user is None:
            result["error"]="USER_NOT_FOUND"
            return result
        
        for col in user.__mapper__.attrs.keys():
            value=getattr(user,col)
            
            if col=="password_hash":
                continue
            elif col=="user_type":
                value=user.listTypes()
            elif col=="following":
                value=common.fromStringList(value)
            elif col in ["inbox","blocked","id"] and id!=uid:
                continue
            result[col]=value
        
        return result
        
@app.route("/users/modify", methods = ['POST'])
@common.authenticate
def modify():
    result={}
    username=request.json.get("username",None)
    password=request.json.get("password_hash",None)
    uid=request.json["uid"]
    with Session(common.database) as session:
        lock.acquire()
        user=users.getUser(uid)
        
        if username is not None:
            if user.username==username:
                result["error"]="NAME_NOT_CHANGED"
                lock.release()
                return result
            elif session.scalars(select(tables.User.id).where(tables.User.username==username)).first() is not None:
                result["error"]="NAME_ALREADY_TAKEN"
                lock.release()
                return result
            else:
                user.username=username
                session.commit()
                lock.release()
        
        if password is not None:
            user.password_hash=password
            session.commit()
        return result

@app.route("/users/block", methods = ['POST'])
@common.authenticate
def block():
    result={}

    blocked_id=request.json["blocked_id"]
        
    uid=request.json["uid"]
    with Session(common.database) as session:
        user=users.getUser(uid)
        
        user.blocked=appendToStringList(user.blocked,blocked_id)
        session.commit()
    return result
    
@app.route("/users/delete", methods = ['POST'])
@common.authenticate
def delete():
    result={}
    with Session(common.database) as session:
        lock.acquire()
        
        uid=request.json["uid"]
        user=users.getUser(uid)
        
        session.delete(user)
        session.commit()
        lock.release()
        return result

@app.route("/users/signin", methods = ['POST'])
def signin():
    result={}
    with Session(common.database) as session:
        username=request.json["username"]
        password=request.json["password_hash"]
            
        user=session.scalars(select(tables.User).where(tables.User.username==request.json["username"])).first()
        
        if user is None:
            result["error"]="USER_NOT_FOUND"
            return result
        
        if password!=user.password_hash:
            result["error"]="PASSWORD_INCORRECT"
            return result
            
        result["uid"]=user.id
        return result                        