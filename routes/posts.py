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


@app.route("/users/<int:uid>/homepage")
def homepage(uid):
    result={}
    if not common.hasAccess(uid):
        result["error"]="ACCESS_DENIED"
        return result
    
    limit=request.args.get("limit",50)
    before=request.args.get("before",float("inf"))
    
    user=users.getUser(uid)
    with Session(common.database) as session:
        blocked=user.blocked
        blocked=common.fromStringList(blocked)
        
        following=user.following
        following=common.fromStringList(following)
        
        query=select(tables.Post.id).where((tables.Post.author.in_(following)) & (tables.Post.id < before) & (tables.Post.author.not_in(blocked))).limit(limit).order_by(desc(tables.Post.id))
        
        result["result"]=[]
        for row in session.scalars(query).all():
            result["result"].append(row)
        
        return result
        
            
@app.route("/users/<int:uid>/trending")
def trending(uid):
    result={}
    if not common.hasAccess(uid):
        result["error"]="ACCESS_DENIED"
        return result
    
    limit=request.args.get("limit",50)
    before=request.args.get("before",float("inf"))
    
    with Session(common.database) as session:
        result["result"]=[]
        
        blocked=users.getUser(uid).blocked
        blocked=common.fromStringList(blocked)
        
        while len(result["result"])<50:
            query=select(tables.Post.id).where((tables.Post.id < before) & (tables.Post.author.not_in(blocked)) & (tables.Post.is_trending==True)).limit(limit-len(result["result"])).order_by(desc(tables.Post.trendy_ranking))
            
            count=0
            for row in session.scalars(query).all():
                count+=1
                result["result"].append(row)
            
            if count==0: #No more posts left to iterate through
                break
        
        return result


@app.route("/users/<int:uid>/posts/create")
def post(uid):
    result={}
    if not common.hasAccess(uid):
        result["error"]="ACCESS_DENIED"
        return result
    
    user=users.getUser(uid)
    if not common.hasType(user.user_type,users.ORDINARY):
        result["error"]="INSUFFICIENT_PERMISSION" #If not OU, can't post, dislike, like, etc.
        return result
    data=request.args.get("data")
    data=base64.b64decode(data)
    data=json.decode(data)
    
    result["id"]=posts.createPost("POST", data)
    
    return result

@app.route("/users/<int:uid>/posts/info")
def post_info(uid):
    result={}
    if not common.hasAccess(uid):
        result["error"]="ACCESS_DENIED"
        return result
    
    post=posts.getPost(requests.args.get("id"))
    
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

@app.route("/users/<int:uid>/posts/edit")
def post_edit(uid):
    result={}
    if not common.hasAccess(uid):
        result["error"]="ACCESS_DENIED"
        return result
    
    user=users.getUser(uid)
    if not common.hasType(user.user_type,users.ORDINARY):
        result["error"]="INSUFFICIENT_PERMISSION" #If not OU, can't post, dislike, like, etc.
        return result
        
    with Session(common.database) as session:
        data=json.decode(base64.decode(requests.args.get("data")).decode())
        post=posts.getPost(data["id"])
        for key in data:
            value=data[key]
            
            if key=="id":
                continue
            elif key=="keywords":
                value=common.toStringList(value)
                
            setattr(post,key,value)
            
    return result
    
@app.route("/users/<int:uid>/posts/delete")
def post_delete(uid):
    result={}
    if not common.hasAccess(uid):
        result["error"]="ACCESS_DENIED"
        return result
    
    
    lock.acquire()
    
    post_id=request.args.get("id",type=int)
    
    with Session(common.database) as session:
        post=posts.getPost(post_id)
        can_delete=False
        
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
@app.route("/users/<int:uid>/upload")
def upload(uid):
    result={}
    if not common.hasAccess(uid):
        result["error"]="ACCESS_DENIED"
        return result
        
    user=users.getUser(uid)
    if not common.hasType(user.user_type,users.ORDINARY):
        result["error"]="INSUFFICIENT_PERMISSION" #If not OU, can't post, dislike, like, etc.
        return result
        
    data=request.args.get("data")  
    type=request.args.get("type")
    
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

@app.route("/images/<int:id>")
def image(id):
    with Session(common.database) as session:
        path, type =session.scalars(select(tables.Upload.path, tables.Upload.type).where(tables.Upload.id==id)).first()
        path=path.replace("/",os.path.sep)
        
        return send_file(path, mimetype=type)
        
    
    
    
    