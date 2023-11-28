from utils import common, tables, users

from utils import posts

from utils.common import app

from flask import request, send_file
from sqlalchemy import select
from sqlalchemy.orm import Session

import base64, json, time, os, random
import multiprocessing
from pathlib import Path

lock=multiprocessing.Lock() #Not enough to use autoincrement ---- autoincrement doesn't neccessarily create monotonically increasing IDs, only unique ones. However, we need it in a specific order.


@app.route("/users/homepage", methods = ['POST'])
def homepage():
    result={}
    if not common.hasAccess():
        result["error"]="ACCESS_DENIED"
        return result
    
    limit=request.json.get("limit",50)
    before=request.json.get("before",float("inf"))
    
    uid=request.json["uid"]
    user=users.getUser(uid)
    with Session(common.database) as session:
        blocked=user.blocked
        blocked=common.fromStringList(blocked)
        
        following=user.following
        following=common.fromStringList(following)
        
        query=select(tables.Post.id).where((tables.Post.author.in_(following)) & (tables.Post.id < before) & (tables.Post.author.not_in(blocked)) & (tables.Post.type=="POST") ).limit(limit).order_by(desc(tables.Post.id))
        
        result["result"]=[]
        for row in session.scalars(query).all():
            result["result"].append(row)
        
        return result
        
            
@app.route("/users/trending", methods = ['POST'])
def trending():
    result={}
    if not common.hasAccess():
        result["error"]="ACCESS_DENIED"
        return result
    
    limit=request.json.get("limit",50)
    before=request.json.get("before",float("inf"))
    
    uid=request.json["uid"]
    with Session(common.database) as session:
        result["result"]=[]
        
        blocked=users.getUser(uid).blocked
        blocked=common.fromStringList(blocked)
        
        while len(result["result"])<50:
            query=select(tables.Post.id).where((tables.Post.id < before) & (tables.Post.author.not_in(blocked)) & (tables.Post.is_trending==True) & (tables.Post.type=="POST")).limit(limit-len(result["result"])).order_by(desc(tables.Post.trendy_ranking))
            
            count=0
            for row in session.scalars(query).all():
                count+=1
                result["result"].append(row)
            
            if count==0: #No more posts left to iterate through
                break
        
        return result


@app.route("/users/posts/create", methods = ['POST'])
def post():
    result={}
    if not common.hasAccess():
        result["error"]="ACCESS_DENIED"
        return result
    
    uid=request.json["uid"]
    user=users.getUser(uid)
    if not common.hasType(user.user_type,users.ORDINARY):
        result["error"]="INSUFFICIENT_PERMISSION" #If not OU, can't post, dislike, like, etc.
        return result
    
    result["id"]=posts.createPost("POST", request.json)
    
    return result

@app.route("/users/posts/info", methods = ['POST'])
def post_info():
    result={}
    if not common.hasAccess():
        result["error"]="ACCESS_DENIED"
        return result
    
    post=posts.getPost(request.json.get("id"))
    if post is None:
        result["error"]="POST_NOT_FOUND"
        return result
        
    result["result"]={}
    
    for col in post.__mapper__.attrs.keys():
        value=getattr(post,col)
        
        if col=="keywords":
            value=common.fromStringList(value)
            
        result["result"][col]=value
    return result

@app.route("/users/posts/edit", methods = ['POST'])
def post_edit():
    result={}
    if not common.hasAccess():
        result["error"]="ACCESS_DENIED"
        return result
    
    uid=request.json["uid"]
    user=users.getUser(uid)
    if not common.hasType(user.user_type,users.ORDINARY):
        result["error"]="INSUFFICIENT_PERMISSION" #If not OU, can't post, dislike, like, etc.
        return result
        
    with Session(common.database) as session:
        post=posts.getPost(request.json["id"])
        for key in request.json:
            value=request.json[key]
            
            if (not hasattr(post, key)) or key=="id":
                continue
            elif key=="keywords":
                value=common.toStringList(value)
                
            setattr(post,key,value)
            
    return result
    
@app.route("/users/posts/delete", methods = ['POST'])
def post_delete():
    result={}
    if not common.hasAccess():
        result["error"]="ACCESS_DENIED"
        return result
    
    
    lock.acquire()
    
    post_id=request.json.get("id",type=int)
    
    with Session(common.database) as session:
        post=posts.getPost(post_id)
        can_delete=False
        
        uid=request.json["uid"]
        user=users.getUser(uid)
        
        if post.type=="INBOX":
            can_delete=False
        elif post.type=="COMMENT":
            parent_post=posts.getPost(post.parent_id)
            if parent_post.author==uid:
                can_delete=True
        elif post.author==uid:
            can_delete=True
        elif users.checkForType(user.user_type, users.SUPER):
            can_delete=True
        
        if not can_delete:
            result["error"]="INSUFFICIENT_PERMISSION"
            lock.release()
            return result
        else:
            session.delete(post)
            session.commit()
            lock.release()
            return result

random_string = lambda N: ''.join(random.choices(string.ascii_uppercase + string.digits, k=N))

upload_lock=multiprocessing.Lock()
@app.route("/users/upload", methods = ['POST'])
def upload():
    result={}
    if not common.hasAccess():
        result["error"]="ACCESS_DENIED"
        return result
    
    uid=request.json["uid"]
    user=users.getUser(uid)
    if not common.hasType(user.user_type,users.ORDINARY):
        result["error"]="INSUFFICIENT_PERMISSION" #If not OU, can't post, dislike, like, etc.
        return result
        
    data=request.json.get("data")  
    type=request.json.get("type")
    
    data_size=(len(data) * 3) / 4 - data.count('=', -2)
    
    if data_size> 10*(10**6): #More than 10MB
        result["error"]="FILE_TOO_LARGE"
        return result
        
    upload_lock.acquire()
    with Session(common.database) as session:
        upload=tables.Upload()
        
        while True: #Make sure there is not a row already with this filename
            upload.path="/".join("images",random_string(10))
            if session.scalars(select(tables.Upload.id).where(tables.Upload.path==upload.path)).first() is None:
                break
            
            
        upload.type=type
        
        session.add(upload)
        session.commit()
        
        upload_lock.release()
        
        Path("images").mkdir(parents=True, exist_ok=True)
        
        with open(upload.path.replace("/",os.path.sep),"wb+") as f: #Windows. That is all I'll say.
            f.write(base64.b64decode(data))
            
        result["url"]=f"images/{upload.id}"
        return result

@app.route("/images/id", methods = ['POST'])
def image():
    
    id=request.json["id"]
    with Session(common.database) as session:
        path, type =session.scalars(select(tables.Upload.path, tables.Upload.type).where(tables.Upload.id==id)).first()
        path=path.replace("/",os.path.sep)
        
        return send_file(path, mimetype=type)
        
    
    
    
    