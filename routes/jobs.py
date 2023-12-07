#in search, allow for all job applications to show up.

from utils import common, tables
from utils.common import app
from utils import users, posts, jobs
from flask import request
from sqlalchemy import select, desc, not_, literal
from sqlalchemy.types import String
from sqlalchemy.orm import Session
import requests
import json, time

@app.route("/jobs/show")
@common.authenticate
def jobs_list():
    result={}
    
    uid=request.json["uid"]
    before=request.json["before"] or float("inf")
    limit=request.json.get("limit",20)
    with Session(common.database) as session:
        user=users.getUser(uid,session)
        query=select(tables.Post.id).where((tables.Post.type=="JOB") & not_(tables.Post.hidden) & (tables.Post.author!=user.id) & not_(literal(user.applied).contains(" "+tables.Post.id.cast(String)+"|")) & (tables.Post.id < before)).order_by(desc(tables.Post.id)).limit(limit) #You can't be shown jobs you applied before, no matter how recently
        
        result["posts"]=session.scalars(query).all()
        result["before"]=common.last(result["posts"]) #New pagination parameter
    
    return result

@app.route("/jobs/apply")
@common.authenticate
def jobs_apply():
    result={}
    
    
    uid=request.json["uid"]
    post_id=request.json["post_id"]
    
    with Session(common.database) as session:
        user=users.getUser(uid,session)
        post=posts.getPost(post_id,session)
        
        applied=common.fromStringList(user.applied)
        applied=[_.split("|") for _ in applied] #Of the form <id>|<last_applied_time>
        applied_idx=-1

        for i,e in enumerate(applied):
            if int(e[0])==user.id:
                applied_idx=i
                break
        
        if (applied_idx>=0) and (int(applied[applied_idx][1])>time.time()-(4*60)): #Appplied less than 4 minutes ago
            result["error"]="APPLIED_RECENTLY"
            return result
            
        if post.hidden: #Can't apply to a hidden post
            result["error"]="NOT_AVAILABLE"
            
        if not(user.hasType(user.ORDINARY)) or user.hasType(user.CORPORATE): #CUs and non-OUs should not be able to apply
            result["error"]="INSUFFICIENT_PERMISSION"
            return result
        
        info=json.loads(post.text)
        r=requests.post(info["endpoint"],data=request.json["questions"]) #Endpoint must accept POST requests
        
        if r.status_code!=200: #Endpoint must return 200 upon success
            result["error"]="SUBMISSION_ERROR"
            return result
        else:
            jobs.charge_for_post(post,session) #While we can't "reverse" a submission in case of a CU not being able to pay, we will hide the post for the next submission
            
            applied[applied_idx][1]=str(time.time())
            applied=["|".join(_) for _ in applied] #Go backwards and join up the list again
            user.applied=applied
            
            session.commit()
            return result
            
        