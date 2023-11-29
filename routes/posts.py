from utils import common, tables, users, balance

from utils import posts

from utils.common import app

from flask import request, send_file
from sqlalchemy import select
from sqlalchemy.orm import Session

import base64, json, time, os, random, re
import multiprocessing
from pathlib import Path

lock=multiprocessing.Lock() #Not enough to use autoincrement ---- autoincrement doesn't neccessarily create monotonically increasing IDs, only unique ones. However, we need it in a specific order.


@app.route("/users/homepage", methods = ['POST'])
@common.authenticate
def homepage():
    result={}
    limit=request.json.get("limit",50)
    before=request.json.get("before",float("inf"))
    
    uid=request.json["uid"]
    user=users.getUser(uid)
    with Session(common.database) as session:
        
        query=select(tables.Post.id).where(user.has_followed(tables.Post.author) & (tables.Post.id < before) & ~(user.has_blocked(tables.Post.author)) & (tables.Post.type=="POST") ).limit(limit).order_by(desc(tables.Post.id))
        
        result["posts"]=[]
        for row in session.scalars(query).all():
            result["posts"].append(row)
        
        return result
        
            
@app.route("/users/trending", methods = ['POST'])
@common.authenticate
def trending():
    result={}
    
    limit=request.json.get("limit",50)
    before=request.json.get("before",float("inf"))
    
    uid=request.json["uid"]
    with Session(common.database) as session:
        result["posts"]=[]
        
        blocked=users.getUser(uid).blocked
        blocked=common.fromStringList(blocked)
        
        while len(result["posts"])<50:
            query=select(tables.Post.id).where((tables.Post.id < before) & ~(user.has_blocked(tables.Post.author)) & (tables.Post.is_trendy==True) ).limit(limit-len(result["posts"])).order_by(desc(tables.Post.trendy_ranking))
            
            count=0
            for row in session.scalars(query).all():
                count+=1
                result["posts"].append(row)
            
            if count==0: #No more posts left to iterate through
                break
        
        return result


@app.route("/users/posts/create", methods = ['POST'])
@common.authenticate
def post():
    result={}
    
    uid=request.json["uid"]
    user=users.getUser(uid)
    if not user.hasType(user.ORDINARY):
        result["error"]="INSUFFICIENT_PERMISSION" #If not OU, can't post, dislike, like, etc.
        return result
    
    #Check for taboo and replace with asterisks --- use regex, with \b for word boundary. case insensitive.
    #Makr /top3posts and /top3users --- both unauthenticated.
    #If word count is over, make post then bill, before returning
    #Load list first into set
    
    data=request.json
    
    taboo_word_count=0
    words_in_post=re.findall(r"(?!'.*')\b[\w']+\b",data["text"])
    extra_words=max(len(words_in_post)-20,0)
    
    cost=0
    
    if user.hasType(user.CORPORATE):
        cost=1*words_in_post #$1 for every word
    elif user.hasType(user.ORDINARY) or user.hasType(user.TRENDY):
        cost=0.1*extra_words #$0.10 for every word over 20 words. Also need to check for images.
    else:
        result["error"]="INSUFFICIENT_PERMISSION" #Can't post without being at least OU
        return result
         
    taboo_list=open("taboo_list.txt","r+").read().splitlines()
    taboo_list=[word.strip() for word in taboo_list]
    taboo_list=set(taboo_list)
    
    for word in words_in_post:
        if word in taboo_list:
            data["text"]=re.sub(rf"(?!'.*')\b[{re.escape(word)}']+\b","****",data["text"],1) #Only replace the instance that we care about
            taboo_word_count+=1
        if taboo_word_count>2:
            #Warn --- set that up
            result["error"]="TOO_MANY_TABOOS"
            return
    
    if len(data["keywords"])>3:
        result["error"]="TOO_MANY_KEYWORDS"
        return
        
    result["id"]=posts.createPost("POST", data)
    
    if cost>0: #If you can't pay, posts get deleted
        balance=balance.RemoveFromBalance(uid,cost)
        if balance==-1:
            result["error"]="NOT_ENOUGH_MONEY"
            with Session(common.database) as session:
                post=posts.getPost(result["id"],session)
                session.delete(post)
                session.commit()
            return
    return result

@app.route("/users/posts/info", methods = ['POST'])
@common.authenticate
def post_info():
    result={}
    
    with Session(common.database) as session:
        post=posts.getPost(request.json.get("id"),session=session)
        posts.views+=1 #Someone looked at it
        session.commit()
        
        if post is None:
            result["error"]="POST_NOT_FOUND"
            return result
            
        for col in post.__mapper__.attrs.keys():
            value=getattr(post,col)
            
            if col=="keywords":
                value=common.fromStringList(value)
                
            result[col]=value
        
    return result

@app.route("/users/posts/edit", methods = ['POST'])
@common.authenticate
def post_edit():
    result={}
    
    uid=request.json["uid"]
    user=users.getUser(uid)
    if not user.hasType(user.ORDINARY):
        result["error"]="INSUFFICIENT_PERMISSION" #If not OU, can't post, dislike, like, etc.
        return result
        
    with Session(common.database) as session:
        post=posts.getPost(request.json["id"])
        for key in request.json:
            value=request.json[key]
            
            if (not hasattr(post, key)) or key=="id":
                continue
            elif key=="keywords":
                if len(value)>3:
                    result["error"]="TOO_MANY_KEYWORDS"
                    return
                value=common.toStringList(value)
                
            setattr(post,key,value)
            
    return result
    
@app.route("/users/posts/delete", methods = ['POST'])
@common.authenticate
def post_delete():
    result={}
    
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
        elif user.hasType(user.SUPER):
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
@common.authenticate
def upload():
    result={}
    uid=request.json["uid"]
    user=users.getUser(uid)
    if not user.hasType(user.ORDINARY):
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
        path, type =session.execute(select(tables.Upload.path, tables.Upload.type).where(tables.Upload.id==id)).first()
        path=path.replace("/",os.path.sep)
        
        return send_file(path, mimetype=type)
        
    
    
    
    