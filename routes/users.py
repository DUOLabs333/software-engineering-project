from ..utils import common, tables
from common import app

from ..utils import users

from flask import request
from sqlalchemy import select
from sqlalchemy import Session
import multiprocessing
import base64, json, time

import posts

lock=multiprocessing.Lock()

#Lock table when deleting, creating, and renaming

@app.route("/users/<username>/info")
def info(username):
    result={}
    if not common.hasAccess(username):
        result["error"]="ACCESS_DENIED"
        return result
    
    with Session(common.database) as session:
        query=select(tables.User).where(tables.User.username==username)
        user=session.scalars(query).first()
        
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
                
            result["result"][col]=value
        
        return result

@app.route("/users/create")
def create():
    result={}
    data=json.loads(base64.b64decode(request.get_data()).decode())
    
    if data["username"] is not None:
        with Session(common.database) as session:
            lock.acquire()
            if session.scalars(select(tables.User.id).where(tables.User.username==data["username"])).first() is not None:
                lock.release()
                result["error"]="USERNAME_EXISTS"
                return result
    
    user=tables.User()
    
    user.id=(session.scalars(select(tables.User.id).order_by(desc(tables.User.id)).limit(1)).first() or 0)+1
    
    for attr in ["username","password_hash"]:
        setattr(user,attr,data[attr])
    
    user.creation_time=int(time.time())
    
    user.user_type=users.addType(0, users.SURFER)
    
    for attr in ["following","followers","blocked","liked_posts"]:
        setattr(user,attr,common.toStringList([]))
    
    user.inbox=posts.createPost("INBOX",{"author": user.id, "text":"This is your inbox.","keywords":[]})
    
    for attr in ["balance","tips"]:
        setattr(user,attr,0)
    
    user.avatar=""
    
    with Session(common.database) as session:
        session.add(user)
        session.commit()
        lock.release()
    result["id"]=user.id
    return result
                        