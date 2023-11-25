from utils import common, tables, users

from utils import posts

from utils.common import app

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
        
@app.route("/users/<int:uid>/posts/<int:pid>/like")
def like_post(uid, pid):
    result = {}
    if not common.hasAccess(uid):
        result["error"] = "ACCESS_DENIED"
        return result

    user = users.getUser(uid)
    if not user or not users.hasType(user.user_type, users.ORDINARY):
        result["error"] = "ACCESS_DENIED_OR_NOT_ORDINARY_USER"
        return result

    with Session(common.database) as session:
        post = posts.getPost(pid)
        if not post:
            result["error"] = "POST_NOT_FOUND"
            return result

        user = users.getUser(uid)
        liked_posts = common.fromStringList(user.liked_posts)
        disliked_posts = common.fromStringList(user.disliked_posts)  # Assuming this method exists
        
        # If post is already disliked, remove the dislike first
        if str(pid) in disliked_posts:
            post.dislikes -= 1
            disliked_posts.remove(str(pid))
            user.disliked_posts = common.toStringList(disliked_posts)

        # Proceed to like the post if not already liked
        if str(pid) not in liked_posts:
            post.likes += 1
            liked_posts.append(str(pid))
            user.liked_posts = common.toStringList(liked_posts)
        
        session.commit()

    return result

@app.route("/users/<int:uid>/posts/<int:pid>/dislike")
def dislike_post(uid, pid):
    result = {}
    if not common.hasAccess(uid):
        result["error"] = "ACCESS_DENIED"
        return result

    user = users.getUser(uid)
    if not user or not users.hasType(user.user_type, users.ORDINARY):
        result["error"] = "ACCESS_DENIED_OR_NOT_ORDINARY_USER"
        return result

    with Session(common.database) as session:
        post = posts.getPost(pid)
        if not post:
            result["error"] = "POST_NOT_FOUND"
            return result

        user = users.getUser(uid)
        liked_posts = common.fromStringList(user.liked_posts)
        disliked_posts = common.fromStringList(user.disliked_posts)  # Assuming this method exists
        
        # If post is already liked, remove the like first
        if str(pid) in liked_posts:
            post.likes -= 1
            liked_posts.remove(str(pid))
            user.liked_posts = common.toStringList(liked_posts)

        # Proceed to dislike the post if not already disliked
        if str(pid) not in disliked_posts:
            post.dislikes += 1
            disliked_posts.append(str(pid))
            user.disliked_posts = common.toStringList(disliked_posts)
        
        session.commit()

    return result

    
    
    