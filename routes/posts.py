# type: ignore
from utils import common, tables, users

from utils import posts

from utils.common import app
import requests
from flask import request
from sqlalchemy import select
from sqlalchemy.orm import Session
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

def createPost(type,data):
    post=tables.Post()
   
    with Session(common.database) as session:
        lock.acquire()
        
        post.id=(session.scalars(select(tables.Post.id).order_by(desc(tables.Post.id)).limit(1)).first() or 0)+1 #Get next biggest id
        post.time_posted=int(time.time())
        
        for attr in ["author","keywords","text"]:
            setattr(post,attr,data[attr])
        
        post.parent_post=data.get(attr,None)
        post.post_type=data.get(attr,"POST")
        
        for attr in ["views","likes","dislikes"]:
            setattr(post,attr,0)
        
        for attr in ["has_picture","has_video"]:
            setattr(post,attr,data.get(attr,False)) #Need to find a way to parse markdown for links --- maybe use regex for ![alt-text](link)
        
        session.add(post)
        session.commit(post)
        lock.release()
    return post.id


def createJobApplication(type,data):
    jobApplication = JobApplication()

    with Session(common.database) as session:
        lock.acquire()

        # Get next biggest id
        jobApplication.id = (session.scalars(select(JobApplication.id).order_by(desc(JobApplication.id)).limit(1)).first() or 0) + 1
        jobApplication.time_posted = int(time.time())

        # Set required attributes
        for attr in ["author", "questions"]:
            setattr(jobApplication, attr, data[attr])

        # Handle due_date (optional)
        jobApplication.due_date = data.get("due_date", None)

        session.add(jobApplication)
        session.commit()
        lock.release()

    return jobApplication.id

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

    
    
@app.route("/users/<int:uid>/posts/jobs/create")
def createJob(uid):
    result={}
    if not common.hasAccess(uid):
        result["error"]="ACCESS_DENIED"
        return result
    
    data=request.args.get("data")
    data=base64.b64decode(data)
    data=json.decode(data)
    
    result["id"]=createJobApplication("JOB", data)
    
    return result  