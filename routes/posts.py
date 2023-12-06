from utils import common, tables, users, jobs

from utils import posts

from utils.common import app

from flask import request, send_file
from sqlalchemy import select, desc, not_
from sqlalchemy.orm import Session

import base64, os, random, string
import multiprocessing
from pathlib import Path
<<<<<<< HEAD
import datetime from datetime
lock=multiprocessing.Lock() #Not enough to use autoincrement ---- autoincrement doesn't neccessarily create monotonically increasing IDs, only unique ones. However, we need it in a specific order.


@app.route("/posts/homepage", methods = ['POST'])
=======

@app.route("/posts/homepage")
>>>>>>> af6812bd927ecb1fd0abefb2917f6fc7e9f479dc
@common.authenticate
def homepage():
    result={}
    limit=request.json.get("limit",50)
    before=request.json.get("before",0)
    
    uid=request.json["uid"]
    user=users.getUser(uid)
    with Session(common.database) as session:
        
<<<<<<< HEAD
        post_query=select(tables.Post.id).where(user.has_followed(tables.Post.author) & (tables.Post.id < before) & not_(user.has_blocked(tables.Post.author)) & (tables.Post.type=="POST") ).limit(limit).order_by(desc(tables.Post.id)) #Sort chronologically, not algorithmically --- one of the biggest problems with other social media sites
       
        posts = session.scalars(post_query).all()  # Fetch regular posts
        result["posts"]=session.scalars(posts).all()
=======
        query=select(tables.Post.id).where(user.has_followed(tables.Post.author) & not_(user.has_blocked(tables.Post.author)) & (tables.Post.type=="POST") ).order_by(tables.Post.time_posted.desc()).offset(before).limit(limit) #Sort chronologically, not algorithmically --- one of the biggest problems with other social media sites
        
        result["posts"]=session.scalars(query).all()
        result["before"]=before+len(result["posts"])
>>>>>>> af6812bd927ecb1fd0abefb2917f6fc7e9f479dc
        
        return result
    

@app.route("/posts/reportpage", methods = ['POST'])
@common.authenticate
def reportpage():
    result={}
    limit=request.json.get("limit",50)
    before=request.json.get("before",float("inf"))
    
    uid=request.json["uid"]
    user=users.getUser(uid)
    with Session(common.database) as session:
        
        report_query = select(tables.Post.id).where(user.has_followed(tables.Post.author) & (tables.Post.id < before) & not_(user.has_blocked(tables.Post.author)) & (tables.Post.type == "REPORT")).limit(limit).order_by(desc(tables.Post.id))
        posts = session.scalars(report_query).all()  # Fetch report posts
        result["reports"]=session.scalars(posts).all()
        
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
        result["error"]="INSUFFICIENT_PERMISSION" #If not OU, can't post, dislike, like, etc.
        return result
    
    data=request.json
    
    #Get which words were added to title,post. create will delete post, edit will revert post (make rollback object)
    
    error, data = posts.cleanPostData(None,data,user)
    
    if error!=None:
        result["error"]=error
        return
        
    result["id"]=posts.createPost(data)
    
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
            return
                
        post.views+=1 #Someone looked at it
        
        if post.type=="JOB":
            return_value=jobs.charge_for_post(post,session)
            if return_value==-1: #Out of money
                result["error"]="APPLICATION_NOT_AVAILABLE"
                post.views-=1
                session.commit()
                return
        session.commit()
        users.getUser(post.author).update_trendy_status() #Event handler
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

@app.route("/posts/edit")
@common.authenticate
def post_edit():
    result={}
    
    uid=request.json["uid"]
    user=users.getUser(uid)
    if not user.hasType(user.ANON):
        result["error"]="INSUFFICIENT_PERMISSION" #If not OU, can't post, dislike, like, etc.
        return result
    
        
    with Session(common.database) as session:
        post=posts.getPost(request.json["id"],session)
        if post is None:
            result["error"]="POST_DOES_NOT_EXIST"
            return 
        
        data=request.json
        error, data=posts.cleanPostData(data["id"],data,user)
        
        if error!=None:
            result["error"]=error
            return
                
        for field in post.editable_fields:
            value=data.get(field,getattr(post,field)) #Get new value, otherwise, just get what was there before
            if isinstance(value, list):
                value=common.toStringList(value)
                
            setattr(post,field,value)
            
        session.commit(post)
            
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
            parent_post=posts.getPost(post.parent_id)
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

@app.route("/media")
def image():
    
    id=request.json["id"]
    with Session(common.database) as session:
        path, type =session.execute(select(tables.Upload.path, tables.Upload.type).where(tables.Upload.id==id)).first()
        path=path.replace("/",os.path.sep)
        
        return send_file(path, mimetype=type)
        
    
@app.route("/posts/reports", methods=['POST'])
@common.authenticate
def report_post():
    result = {}

    uid = request.json["uid"]
    target_user = request.json["target_user"]
    report_text = request.json["report_text"]
   
    with Session(common.database) as session:
        complainer = users.getUser(uid, session)        #user making report
        complainee = users.getUser(target_user, session)  # The user to be reported
        report_data = {
                "author": uid,
                "text": "Report by User (ID: {}) against(ID: {}) :\n{}".format(complainer.id,complainee.id, report_text), #report by complainer against complainee and then report text
                "type": "REPORT",  
            }
            
        # Clean the report data as we would for creating a regular post
        error, data = posts.cleanPostData(None, report_data, complainer)  #filter taboo
        if error!=None:
            result["error"]=error
            return
            
        # Create the report post
        result["id"] = posts.createPost(data)
            

@app.route("/posts/reports/dispute", methods=['POST'])
@common.authenticate        #this endpoint feels a little weird, i might have to work on it more
def dispute_report():
    result = {}
    
    uid = request.json["uid"] #the user id for complainee
    report_id = request.json["report_id"]  # ID of the report being disputed
    dispute_text = request.json["dispute_text"]  # The text the complainee adds to dispute the report
    
    with Session(common.database) as session:
        complainee = users.getUser(uid, session) 
        report = session.query(tables.Post).filter(tables.Post.id == report_id)

        # Ensure the report exists and the complainee is the one being reported
        if  report.author == complainee.id and report.type == "DISPUTE":
            # Update the report text with the dispute information
            report.text += "\n\nDispute by User (ID: {}):\n{}".format(complainee.id, dispute_text)
            session.commit()
            result["message"] = "Report dispute has been recorded."
        else:
            result["error"] = "Report not found or permission denied."
            
    
    return result


@app.route("/posts/reports/approve", methods=['POST'])
@common.authenticate
def approve_report():
    result = {}

    uid = request.json["uid"]  # The user ID of the SUPER user approving the report
    report_id = request.json["report_id"]  # ID of the report being approved
    target_user = request.json["target_user"]

    with Session(common.database) as session:
        super_user = users.getUser(uid, session)
        
        # Check if the user is a SUPER user
        if not super_user.hasType(User.SUPER):
            result["error"] = "INSUFFICIENT_PERMISSION"
            return result
        
        report = session.query(tables.Post).filter(tables.Post.id == report_id)

        # Verify the report exists and it's of type 'REPORT'
        if report and report.type == "REPORT":
            complainee = users.getUser(target_user, session)  # Get the user being reported
            complainee.warnings += 1  # Increment the warnings count
            complainee.time_of_last_warn = datetime.utcnow()  # add warning based on current time

            session.commit()
            result["message"] = "Report has been approved and warning issued."
        else:
            result["error"] = "Report not found." #can't find report

    return result

@app.route("/posts/reports/disapprove", methods=['POST'])
@common.authenticate
def disapprove_report():
    result = {}

    uid = request.json["uid"]  # The user ID of the SUPER user approving the report
    report_id = request.json["report_id"]  # ID of the report being approved
    target_user = request.json["target_user"]

    with Session(common.database) as session:
        super_user = users.getUser(uid, session)
        
        # Check if the user is a SUPER user
        if not super_user.hasType(User.SUPER):
            result["error"] = "INSUFFICIENT_PERMISSION"
            return result
        
        report = session.query(tables.Post).filter(tables.Post.id == report_id)
        # Verify the report exists and it's of type 'REPORT'
        if report and report.type == "REPORT":


@app.route("/posts/reports/disapprove", methods=['POST'])    #mostly a copy of /posts/delete
@common.authenticate
def disapprove_report():
    result = {}

    lock.acquire()          #honestly no clue was lock does, just took it from delete endpoint

    report_id = request.json.get("report_id", type=int)

    with Session(common.database) as session:
        report = posts.getPost(report_id)
        uid = request.json["uid"]
        user = users.getUser(uid)

        
        if report and report.type == "REPORT":  #check if report
            if user.hasType(User.SUPER):        #check if super user
                session.delete(report)    #delete
                session.commit()    #save changes
            else:
                result["error"] = "INSUFFICIENT_PERMISSION"   #can't delete cause not super user
                lock.release()               

    lock.release()
    result["message"] = "Report has been disapproved and deleted."   #deletion good
    return result