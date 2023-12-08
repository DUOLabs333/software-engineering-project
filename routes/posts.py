from utils import common, tables, users, jobs

from utils import posts

from utils.common import app

from flask import request, send_file
from sqlalchemy import select, desc, not_

from sqlalchemy.orm import Session

import base64, os, random, string
import multiprocessing, json
from pathlib import Path

from flask import request, send_file, current_app, url_for, jsonify
from werkzeug.utils import secure_filename

@app.route("/posts/homepage")
@common.authenticate
def homepage():
    result={}
    limit=request.json.get("limit",50) or 50
    before=request.json.get("before",0) or 0
    
    uid=request.json["uid"]
    user=users.getUser(uid)
    with Session(common.database) as session:
                
        query=select(tables.Post.id).where(user.has_followed(tables.Post.author) & not_(user.has_blocked(tables.Post.author)) & (tables.Post.type=="POST")).order_by(tables.Post.time_posted.desc()).offset(before).limit(limit) #Sort chronologically, not algorithmically --- one of the biggest problems with other social media sites
        
        result["posts"]=session.scalars(query).all()
        result["before"]=before+len(result["posts"])
        
        return result
        
            
@app.route("/posts/trending")
@common.authenticate
def trending():
    result={}
    
    limit=request.json.get("limit",50)
    before=request.json.get("before",0)
    
    uid=request.json["uid"]
    with Session(common.database) as session:
        result["posts"]=[]
        
        user=users.getUser(uid)
        
        query=select(tables.Post.id).where(not_(user.has_blocked(tables.Post.author)) & (tables.Post.is_trendy==True) ).order_by(desc(tables.Post.trendy_ranking)).offset(before).limit(limit)
        
        result["posts"]=session.scalars(query).all()
        result["before"]=before+len(result["posts"])
        
        return result


@app.route("/posts/create")
@common.authenticate
def create_post():
    result={}
    
    uid=request.json["uid"]
    user=users.getUser(uid)
    if not user.hasType(user.ANON):
        print(user.listTypes())
        result["error"]="INSUFFICIENT_PERMISSION" #If not OU, can't post, dislike, like, etc.
        return result
    
    data=request.json
    
    #Get which words were added to title,post. create will delete post, edit will revert post (make rollback object)
    
    cost, error, data = posts.cleanPostData(None,data,user)
    
    if error!=None:
        result["error"]=error
        return result
        
    result["id"]=posts.createPost(data)
    result["cost"]=cost
    
    return result

@app.route("/posts/info")
@common.authenticate
def post_info():
    result={}
    
    uid=request.json["uid"]
    user=users.getUser(uid)
    with Session(common.database) as session:
        post=posts.getPost(request.json.get("id"),session=session)
        
        if not post.is_viewable(user):
            result["error"]="INSUFFICIENT_PERMISSION"
            return result
                
        post.views+=1 #Someone looked at it
        
        if post.type=="JOB":
            return_value=jobs.charge_for_post(post,session)
            if return_value==-1: #Out of money
                result["error"]="APPLICATION_NOT_AVAILABLE"
                post.views-=1
                session.commit()
                return result
        session.commit()
        users.getUser(post.author).update_trendy_status() #Event handler
        session.commit()
        
        if post is None:
            result["error"]="POST_NOT_FOUND"
            return result
            
        for col in post.__mapper__.attrs.keys():
            value=getattr(post,col)
            
            if col in ["keywords","videos","images"]:
                value=common.fromStringList(value)
                
            result[col]=value
        
        #Maybe add number of reports later?
        
    return result

@app.route("/posts/edit")
@common.authenticate
def post_edit():
    result={}
    
    uid=request.json["uid"]
    user=users.getUser(uid)
    if not user.hasType(user.ANON):
        result["error"]="INSUFFICIENT_PERMISSION"
        return result
    
        
    with Session(common.database) as session:
        post=posts.getPost(request.json["id"],session)
        if post is None:
            result["error"]="POST_DOES_NOT_EXIST"
            return 
        
        data=request.json
        cost, error, data=posts.cleanPostData(data["id"],data,user)
        
        if error!=None:
            result["error"]=error
            return result
                
        for field in post.editable_fields:
            value=data.get(field,getattr(post,field)) #Get new value, otherwise, just get what was there before
            if isinstance(value, list):
                value=common.toStringList(value)
                
            setattr(post,field,value)
            
        session.commit(post)
    
    result["cost"]=cost        
    return result
    
@app.route("/posts/delete")
@common.authenticate
def post_delete():
    result={}
    
    post_id=request.json.get("id",type=int)
    
    with Session(common.database) as session:
        post=posts.getPost(post_id)
        can_delete=False
        
        uid=request.json["uid"]
        user=users.getUser(uid)
        
        if post.type=="INBOX":
            can_delete=False
        elif post.type=="COMMENT":
            parent_post=posts.getPost(post.parent)
            if parent_post.author==uid:
                can_delete=True
            
        if post.author==uid:
            can_delete=True
            
        if user.hasType(user.SUPER):
            can_delete=True
        
        if not can_delete:
            result["error"]="INSUFFICIENT_PERMISSION"
            return result
        else:
            session.delete(post)
            session.commit()
            return result
            
@app.route("/posts/like")
@common.authenticate
def like_post():
    result = {}
    
    uid=request.json["uid"]
    post_id=request.json["post_id"]
    user = users.getUser(uid)
    if not user.hasType(user.ORDINARY):
        result["error"] = "INSUFFICIENT_PERMISSION"
        return result

    with Session(common.database) as session:
        post = posts.getPost(post_id,session)
        if not post:
            result["error"] = "POST_NOT_FOUND"
            return result

        user = users.getUser(uid,session)
        liked_posts = common.fromStringList(user.liked_posts)
        disliked_posts = common.fromStringList(user.disliked_posts)
        
        # If post is already disliked, remove the dislike first
        if str(post_id) in disliked_posts:
            post.dislikes -= 1
            disliked_posts.remove(str(post_id))
            user.disliked_posts = common.toStringList(disliked_posts)

        # Proceed to like the post if not already liked
        if str(post_id) not in liked_posts:
            post.likes += 1
            liked_posts.append(str(post_id))
            user.liked_posts = common.toStringList(liked_posts)
        else:
            liked_posts.remove(str(post_id)) #Reverses like. Prevents duplication for /unlike
            user.liked_posts = common.toStringList(liked_posts)
            post.likes -= 1
            
        session.commit()
        users.getUser(post.author).update_trendy_status() #Event handler
        session.commit()

    return result

@app.route("/posts/dislike")
@common.authenticate
def dislike_post():
    result = {}
    
    uid=request.json["uid"]
    post_id=request.json["post_id"]
    user = users.getUser(uid)
    if not user.hasType(user.ORDINARY):
        result["error"] = "NOT_ORDINARY_USER"
        return result

    with Session(common.database) as session:
        post = posts.getPost(post_id,session)
        if not post:
            result["error"] = "POST_NOT_FOUND"
            return result

        user = users.getUser(uid,session)
        liked_posts = common.fromStringList(user.liked_posts)
        disliked_posts = common.fromStringList(user.disliked_posts)
        
        # If post is already liked, remove the like first
        if str(post_id) in liked_posts:
            post.likes -= 1
            liked_posts.remove(str(post_id))
            user.liked_posts = common.toStringList(liked_posts)

        # Proceed to dislike the post if not already disliked
        if str(post_id) not in disliked_posts:
            post.dislikes += 1
            disliked_posts.append(str(post_id))
            user.disliked_posts = common.toStringList(disliked_posts)
        else:
            disliked_posts.remove(str(post_id))
            user.disliked_posts = common.toStringList(disliked_posts)
            post.dislikes -= 1
        
        session.commit()
        users.getUser(post.author).update_trendy_status() #Event handler
        session.commit()

    return result


random_string = lambda N: ''.join(random.choices(string.ascii_uppercase + string.digits, k=N))

upload_lock=multiprocessing.Lock()

@app.route("/users/upload")
@common.authenticate
def image_upload():
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
            upload.path="/".join(["images",random_string(10)])
            if session.scalars(select(tables.Upload.id).where(tables.Upload.path==upload.path)).first() is None:
                break
            
            
        upload.type=type
        
        session.add(upload)
        session.commit()
        
        upload_lock.release()
        
        Path("images").mkdir(parents=True, exist_ok=True)
        
        with open(upload.path.replace("/",os.path.sep),"wb+") as f: #Windows. That is all I'll say.
            f.write(base64.b64decode(data))
            
        result["id"]=upload.id
        return result
        
@app.route("/posts/top3posts")
@common.authenticate
def top3posts():
    result={}
    
    result["posts"]=[]
    
    user=users.getUser(request.json["uid"])
    
    query=select(tables.Post.id).where(tables.Post.is_trendy & not_( user.has_blocked(tables.Post.author))).order_by(desc(tables.Post.trendy_ranking)).limit(3)
    
    with Session(common.database) as session:
        result["posts"]=session.scalars(query).all()
    
    return result
    
@app.route("/media")
def image():
    
    id=request.json["id"]
    with Session(common.database) as session:
        path, type =session.execute(select(tables.Upload.path, tables.Upload.type).where(tables.Upload.id==id)).first()
        path=path.replace("/",os.path.sep)
        
        return send_file(path, mimetype=type)
        
@app.route("/posts/report")
@common.authenticate
def report_post():
    result = {}

    uid = request.json["uid"]
    target = request.json["target"] #Target post, not user
    reason = request.json["reason"]
   
    with Session(common.database) as session:
        user = users.getUser(uid, session) #user making report
        if not user.hasType(user.ANON):
            result["error"]="INSUFFICIENT_PERMISSION"
            return result
            
        text={
        "target": target,
        "reason": reason
        }
        
        data = {
        "author": uid,
        "text": json.dumps(text), #report by complainer against complainee and then report text
        "type": "REPORT",
        "keywords": ["OPEN"]
        }
            
            
        # Create the report post
        result["id"] = posts.createPost(data)
        return result
        
@app.route("/upload_image")
def image1():
    upload_folder = os.path.join(current_app.root_path,"static","images")
    
    Path(upload_folder).mkdir(parents=True,exist_ok=True)
        
    uploaded_img = request.files.get('image')  # Get the image that has been uploaded
    img_name = secure_filename(uploaded_img.filename).lower()  # Get the name of the iamge
    uploaded_img.save(os.path.join(upload_folder, img_name))  # Save that image to the appropriate directory
    location = url_for('static', filename='images/' + img_name)
    print("LOCATION: ", location)
    return jsonify({'location': location})