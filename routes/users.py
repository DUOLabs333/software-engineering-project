from utils import common, tables
from utils.common import app

from utils import users

from flask import request
from sqlalchemy import select
from sqlalchemy.orm import Session
import multiprocessing
import base64, json, time

from routes import users
import random

lock=multiprocessing.Lock()

#Lock table when deleting, creating, and renaming
#To get followers, we must use table.User.following.contains(f" {user.id} ")

def checkIfUsernameExists(username): #You must have the USERS database locked, and you must not unlock it until you placed the (new) username into the database
    with Session(common.database) as session:
        return session.scalars(select(tables.User.id).where(tables.User.username==data["username"])).first() is not None

#CRUD: Create, Read, Update, Delete

@app.route("/users/create")
def create():
    result={}
    data=json.loads(base64.b64decode(request.get_data()).decode())
    
    lock.acquire()
    if data["username"] is not None:
        if checkIfUsernameExists(data["username"]):
            lock.release()
            result["error"]="USERNAME_EXISTS"
            return result
                
    else:
        while True:
            data["username"]="anon_"+random.randint(0,10000000)
            if not checkIfUsernameExists(data["user"]):
                break
        
        
    user=tables.User()
    
    user.id=(session.scalars(select(tables.User.id).order_by(desc(tables.User.id)).limit(1)).first() or 0)+1
    
    for attr in ["username","password_hash"]:
        setattr(user,attr,data[attr])
    
    user.creation_time=int(time.time())
    
    user.user_type=users.addType(0, users.SURFER)
    
    for attr in ["following","blocked","liked_posts"]:
        setattr(user,attr,common.toStringList([]))
    
    user.inbox=posts.createPost("INBOX",{"author": user.id, "text":"This is your inbox.","keywords":[]})
    
    for attr in ["tips"]:
        setattr(user,attr,0)
    
    user.avatar=""
    
    with Session(common.database) as session:
        session.add(user)
        session.commit()
        lock.release()
    result["id"]=user.id
    return result

@app.route("/users/<int:uid>/info")
def info(uid):
    result={}
    if not common.hasAccess(uid):
        result["error"]="ACCESS_DENIED"
        return result
    
    with Session(common.database) as session:
        
        user=users.getUser(uid)
        if user is None:
            result["error"]="USER_NOT_FOUND"
            return result
        
        result["result"]={}
        for col in user.__mapper__.attrs.keys():
            value=getattr(user,col)
            
            if col=="password_hash":
                continue
            elif col=="user_type":
                value=users.listTypes(value)
            elif col=="following":
                value=common.fromStringList(value)
                
            result["result"][col]=value
        
        return result
        
@app.route("/users/<int:uid>/rename")
def rename(uid):
    result={}
    if not common.hasAccess(uid):
        result["error"]="ACCESS_DENIED"
        return result
    
    new_name=request.args.get("new_name")
    
    with Session(common.database) as session:
        lock.acquire()
        user=users.getUser(uid)
        if user.username==new_name:
            result["error"]="NAME_NOT_CHANGED"
            lock.release()
            return result
        elif session.scalars(select(tables.User.id).where(tables.User.username==new_name)).first() is not None:
            result["error"]="NAME_ALREADY_TAKEN"
            lock.release()
            return result
        else:
            user.username=new_name
            session.commit()
            lock.release()
            return result
            
@app.route("/users/<int:uid>/delete")
def delete(uid):
    result={}
    if not common.hasAccess(uid):
        result["error"]="ACCESS_DENIED"
        return result
    
    with Session(common.database) as session:
        lock.acquire()
        
        user=users.getUser(uid)
        
        session.delete(user)
        session.commit()
        lock.release()
        return result

@app.route("/users/<int:user_id>/add_type")
def add_user_type(user_id):
    result = {}
    current_user_id = common.getCurrentUserId()

    if not users.isSuperUser(current_user_id) or current_user_id == user_id:
        result["error"] = "ACCESS_DENIED"
        return result

    type_to_add = request.args.get("type_to_add")
    if not type_to_add or not hasattr(users, type_to_add):
        result["error"] = "INVALID_TYPE_PROVIDED"
        return result

    with Session(common.database) as session:
        user = users.getUser(user_id, session)
        if user:
            user_type_constant = getattr(users, type_to_add)
            user.user_type = users.addType(user.user_type, user_type_constant)
            session.commit()
            # Only return the updated user types
            result["user_type"] = users.listTypes(user.user_type)
        else:
            result["error"] = "USER_NOT_FOUND"
            return result
    
    return result  

@app.route("/users/<int:user_id>/remove_type")
def remove_user_type(user_id):
    result = {}
    current_user_id = common.getCurrentUserId()

    if not users.isSuperUser(current_user_id) or current_user_id == user_id:
        result["error"] = "ACCESS_DENIED"
        return result

    type_to_remove = request.args.get("type_to_remove")
    if not type_to_remove or not hasattr(users, type_to_remove):
        result["error"] = "INVALID_TYPE_PROVIDED"
        return result

    with Session(common.database) as session:
        user = users.getUser(user_id, session)
        if user:
            user_type_constant = getattr(users, type_to_remove)
            user.user_type = users.removeType(user.user_type, user_type_constant)
            session.commit()
            # Only return the updated user types
            result["user_type"] = users.listTypes(user.user_type)
        else:
            result["error"] = "USER_NOT_FOUND"
            return result
    
    return result  