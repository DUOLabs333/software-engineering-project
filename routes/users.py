from utils import common, tables
from utils.common import app

from utils import users, posts

from flask import request

from sqlalchemy import select
from sqlalchemy import desc

from sqlalchemy.orm import Session
import multiprocessing
import base64, json, time

import random
import string 

lock=multiprocessing.Lock() #We lock not because of the IDs (autoincrement is enough), but because of the usernames

#Lock table when deleting, creating, and renaming
#To get followers, we must use table.User.following.contains(f" {user.id} ")

def checkIfUsernameExists(username): #You must have the USERS database locked, and you must not unlock it until you placed the (new) username into the database
    with Session(common.database) as session:
        return session.scalars(select(tables.User.id).where(tables.User.username==username)).first() is not None

#CRUD: Create, Read, Update, Delete

@app.route("/users/create")
def create():
    result={}
    data=json.loads(base64.b64decode(request.get_data()).decode())
    
    anonymous=data.get("anonymous",False)
    
    lock.acquire()
    
    if anonymous:
        while True:
            data["username"]="anon_"+random.randint(0,10000000)
            if not checkIfUsernameExists(data["user"]):
                break
        data["password"]=''.join(random.choices(string.ascii_uppercase + string.digits, k=256))

    if data["username"] is not None:
        if checkIfUsernameExists(data["username"]):
            lock.release()
            result["error"]="USERNAME_EXISTS"
            return result         
    else:
        if not anonymous:
            result["error"]="USERNAME_NOT_GIVEN"
            lock.release()
            return result
        
        
    user=tables.User()
    
    for attr in ["username","password_hash"]:
        setattr(user,attr,data[attr])
    
    user.creation_time=int(time.time())
    
    user_type=data.get("user_type","SURFER")
    
    if user_type not in ["SURFER","ORDINARY","CORPORATE"]:
        result["error"]="INVALID_USER_TYPE"
        return result
        
    user.user_type=users.addType(0, getattr(users,user_type))
    
    for attr in ["following","blocked","liked_posts","disliked_posts"]:
        setattr(user,attr,common.toStringList([]))
    
    for attr in ["tips"]:
        setattr(user,attr,0)
    
    user.avatar=""
    
    with Session(common.database) as session:
        user.inbox=0
        user.profile=0
        
        session.add(user)
        session.commit()
        
        user.inbox=posts.createPost("INBOX",{"author": user.id, "text":"This is your inbox.","keywords":[]})
        user.profile=posts.createPost("PROFILE",{"author": user.id, "text":"This is your profile.","keywords":[]})
        session.commit()
        
        lock.release()
        result["id"]=user.id
        if anonymous:
            result["password_hash"]=user.password_hash
    return result

@app.route("/users/<int:uid>/info")
def info(uid):
    result={}
    if not common.hasAccess(uid):
        result["error"]="ACCESS_DENIED"
        return result
    
    id=request.args.get("id",uid) #By default, use the current uid
    
    with Session(common.database) as session:
        
        user=users.getUser(id)
        if user is None:
            result["error"]="USER_NOT_FOUND"
            return result
        
        result["result"]={}
        for col in user.__mapper__.attrs.keys():
            value=getattr(user,col)
            
            if col=="password_hash":
                continue
            elif col=="user_type":
                value=users.listTypes(value)
            elif col=="following":
                value=common.fromStringList(value)
            elif col in ["inbox","blocked","id"] and id!=uid:
                continue
            result["result"][col]=value
        
        return result
        
@app.route("/users/<int:uid>/rename")
def rename(uid):
    result={}
    if not common.hasAccess(uid):
        result["error"]="ACCESS_DENIED"
        return result
    
    new_name=request.args.get("new_name")
    
    with Session(common.database) as session:
        lock.acquire()
        user=users.getUser(uid)
        if user.username==new_name:
            result["error"]="NAME_NOT_CHANGED"
            lock.release()
            return result
        elif session.scalars(select(tables.User.id).where(tables.User.username==new_name)).first() is not None:
            result["error"]="NAME_ALREADY_TAKEN"
            lock.release()
            return result
        else:
            user.username=new_name
            session.commit()
            lock.release()
            return result
            
@app.route("/users/<int:uid>/delete")
def delete(uid):
    result={}
    if not common.hasAccess(uid):
        result["error"]="ACCESS_DENIED"
        return result
    
    with Session(common.database) as session:
        lock.acquire()
        
        user=users.getUser(uid)
        
        session.delete(user)
        session.commit()
        lock.release()
        return result

@app.route("/users/signin")
def signin():
    result={}
    data=json.loads(base64.b64decode(request.get_data()).decode())
    
    with Session(common.database) as session:
        if "username" not in data:
            result["error"]="USERNAME_NOT_GIVEN"
            return result
            
        user=session.scalars(select(tables.User).where(tables.User.username==data["username"])).first()
        
        if user is None:
            result["error"]="USER_NOT_FOUND"
            return result
        
        if "password" not in data:
            result["error"]="PASSWORD_NOT_GIVEN"
            return result
        
        if data["password"]!=user.password_hash:
            result["error"]="PASSWORD_INCORRECT"
            return result
        result["uid"]=user.id
        return result                        

@app.route('/users/<int:uid>/follow/<int:target_user_id>')
def follow_user(uid, target_user_id):
    result = {}
    with Session(common.database) as session:
        # Retrieve the user who wants to follow
        user = users.getUser(uid)
        if user is None:
            result["error"] = "USER_NOT_FOUND"
            return result

        # Retrieve the target user
        target_user = users.getUser(target_user_id)
        if target_user is None:
            result["error"] = "TARGET_USER_NOT_FOUND"
            return result

        # Check if already following
        following_list = common.fromStringList(user.following)
        if str(target_user_id) in following_list:
            result["message"] = "ALREADY_FOLLOWING"
            return result

        # Update the following list
        following_list.append(str(target_user_id))  # Ensure it is stored as a string
        user.following = common.toStringList(following_list)
        
        # Commit the changes to the database
        session.commit()

        result["message"] = f"Successfully followed user {target_user_id}"
        return result

@app.route('/users/<int:uid>/unfollow/<int:target_user_id>')
def unfollow_user(uid, target_user_id):
    result = {}
    with Session(common.database) as session:
        # Retrieve the user who wants to unfollow
        user = users.getUser(uid)
        if user is None:
            result["error"] = "USER_NOT_FOUND"
            return result

        # Check if the user is currently following the target user
        following_list = common.fromStringList(user.following)
        if str(target_user_id) not in following_list:
            result["message"] = "NOT_FOLLOWING_USER"
            return result

        # Remove the target user from the following list
        following_list.remove(str(target_user_id))
        user.following = common.toStringList(following_list)

        # Commit the changes to the database
        session.commit()

        result["message"] = f"Successfully unfollowed user {target_user_id}"
        return result

@app.route('/users/<int:uid>/suggest')
def suggest_users(uid):
    result = {}
    with Session(common.database) as session:
        # Retrieve the following list of the  current user
        current_user = users.getUser(uid)
        if current_user is None:
            result["error"] = "USER_NOT_FOUND"
            return result

        already_following = set(common.fromStringList(current_user.following))

        # all users' following lists
        all_users = session.query(tables.User.id, tables.User.following).all()
        
        recommended_counts = {}

        for user in all_users:
            if user.id == uid or user.id in already_following:
                continue  # Skip the current user and already followed users

            #users that the current user's followings are following
            followed_by_followings = set(common.fromStringList(user.following))

            # Count number of followings in common
            common_followings = followed_by_followings.intersection(already_following)

            if common_followings:
                # The more people in common, the higher the user will be recommended
                recommended_counts[user.id] = len(common_followings)

        sorted_recommendations = sorted(recommended_counts, key=recommended_counts.get, reverse=True)

        # Limit the number of suggestions (ex, top 10)
        top_suggestions = sorted_recommendations[:10]

        result["suggestions"] = top_suggestions
        return result
