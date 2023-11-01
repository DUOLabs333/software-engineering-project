from ..utils import common, tables, posts, users

from common import app

from flask import request
from sqlalchemy import select
from sqlalchemy import Session
from sqlalchemy import desc

import base64, json, time
import multiprocessing

lock=multiprocessing.Lock()


@app.route("/users/<int:uid>/homepage")
def homepage(uid):
    result={}
    if not common.hasAccess(uid):
        result["error"]="ACCESS_DENIED"
        return result
    
    limit=request.args.get("limit",50)
    before=request.args.get("before",float("inf"))
    
    user=common.getUser(uid)
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
        
        blocked=common.getUser(uid).blocked
        blocked=common.fromStringList(blocked)
        
        while len(result["result"])<50:
            query=select(tables.Post.id).where((tables.Post.id < before) & (tables.Post.author.not_in(blocked))).limit(limit-len(result["result"])).order_by(desc(tables.Post.id))
            
            count=0
            for row in session.scalars(query).all():
                count+=1
                if not posts.isTrendyPost(row):
                    continue
                result["result"].append(row)
            
            if count==0: #No more posts left to iterate through
                break
        
        return result

def createPost(type,data):
    post=tables.Post()
   
    with Session(common.database) as session:
        lock.acquire()
        
        post.id=(session.scalars(select(tables.Post.id).order_by(desc(tables.Post.id)).limit(1)).first() or 0)+1 #Get next biggest id
        post.time_posted=int(time.time())
        
        for attr in ["author","keywords","text"]:
            setattr(post,attr,data[attr])
        
        post.parent_post=None
        post.post_type=type
        
        for attr in ["views","likes","dislikes"]:
            setattr(post,attr,0)
        
        for attr in ["has_picture","has_video"]:
            setattr(post,attr,data.get(attr,False)) #Need to find a way to parse markdown for links --- maybe use regex for ![alt-text](link)
        
        session.add(post)
        session.commit(post)
        lock.release()
    return post.id
    
@app.route("/users/<int:uid>/posts/create")
def post(uid):
    result={}
    if not common.hasAccess(uid):
        result["error"]="ACCESS_DENIED"
        return result
    
    data=request.args.get("data")
    data=base64.b64decode(data)
    data=json.decode(data)
    
    result["id"]=createPost("POST", data)
    
    return result

@app.route("/users/<int:uid>/posts/delete")
def delete(uid):
    result={}
    if not common.hasAccess(uid):
        result["error"]="ACCESS_DENIED"
        return result
    
    
    lock.acquire()
    
    post_id=request.args.get("id",type=int)
    
    #If anything: Can delete if author, if comment, can delete if parent post's author is you
    with Session(common.database) as session:
        post=session.scalars(select(tables.Post).where(tables.Post.id==post_id)).first()
        can_delete=False
        
        user=common.getUser(uid)
        
        if post.type=="INBOX":
            can_delete=False
        elif post.type=="COMMENT":
            parent_post=session.scalars(select(tables.Post).where(tables.Post.id==post.parent_id)).first()
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

    
    
    