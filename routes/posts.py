from ..utils import common, tables, posts

from common import app

from flask import request
from sqlalchemy import select
from sqlalchemy import Session
from sqlalchemy import desc

import base64, json, time
import multiprocessing

lock=multiprocessing.Lock()


@app.route("/users/<username>/homepage")
def homepage(username):
    result={}
    if not common.hasAccess(username):
        result["error"]="ACCESS_DENIED"
        return result
    
    limit=request.args.get("limit",50)
    before=request.args.get("before",float("inf"))
    
    with Session(common.database) as session:
        blocked=select(tables.User.blocked).where(tables.User.username==username)
        blocked=session.scalars(blocked).first()
        blocked=common.fromStringList(blocked)
        
        following=select(tables.User.following).where(tables.User.username==username)
        following=session.scalars(following).first()
        following=common.fromStringList(following)
        
        query=select(tables.Post.id).where((tables.Post.author.in_(following)) & (tables.Post.id < before) & (tables.Post.author.not_in(blocked))).limit(limit).order_by(desc(tables.Post.id))
        
        result["result"]=[]
        for row in session.scalars(query).all():
            result["result"].append(row)
        
        return result
        
            
@app.route("/users/<username>/trending")
def trending(username):
    result={}
    if not common.hasAccess(username):
        result["error"]="ACCESS_DENIED"
        return result
    
    limit=request.args.get("limit",50)
    before=request.args.get("before",float("inf"))
    
    with Session(common.database) as session:
        result["result"]=[]
        
        blocked=select(tables.User.blocked).where(tables.User.username==username)
        blocked=session.scalars(blocked).first()
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

#Have a function for making post, and fill with different types (type, data). Return json file with id
@app.route("/users/<username>/posts/create")
def post(username):
    result={}
    if not common.hasAccess(username):
        result["error"]="ACCESS_DENIED"
        return result
    
    data=request.args.get("data")
    data=base64.b64decode(data)
    data=json.decode(data)
    
    post=tables.Post()
   
    with Session(common.database) as session:
        lock.acquire()
        
        post.id=(session.scalars(select(tables.Post.id).order_by(desc(tables.Post.id)).limit(1)).first() or 0)+1 #Get next biggest id
        post.time_posted=int(time.time())
        
        for attr in ["author","keywords","text"]:
            setattr(post,attr,data[attr])
        
        post.parent_post=None
        post.post_type="POST"
        
        for attr in ["views","likes","dislikes"]:
            setattr(post,attr,0)
        
        for attr in ["has_picture","has_video"]:
            setattr(post,attr,False) #Need to find a way to parse markdown for links --- maybe use regex for ![alt-text](link)
        
        session.add(post)
        session.commit(post)
        lock.release()
    return result
    
    
    
    