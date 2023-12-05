from utils import common, tables, balance
from utils.common import app, appendToStringList, removeFromStringList

from utils import users, posts

from flask import request

from sqlalchemy import select, desc, not_

from sqlalchemy.orm import Session
import multiprocessing
import random, string,time, heapq

lock=multiprocessing.Lock() #We lock not because of the IDs (autoincrement is enough), but because of the usernames

#Lock table when deleting, creating, and renaming
#To get followers, we must use table.User.following.contains(f" {user.id} ")

def checkIfUsernameExists(username): #You must have the USERS database locked, and you must not unlock it until you placed the (new) username into the database
    with Session(common.database) as session:
        return session.scalars(select(tables.User.id).where(tables.User.username==username)).first() is not None

#CRUD: Create, Read, Update, Delete

@app.route("/users/create", methods = ['POST'])
def create():
    result={}
    
    data=request.json
    anonymous=data.get("anonymous",False)
    
    lock.acquire()
    
    if anonymous:
        while True:
            data["username"]=f"anon_{random.randint(0,10000000)}"
            if not checkIfUsernameExists(data["username"]):
                break
        data["password_hash"]=''.join(random.choices(string.ascii_uppercase + string.digits, k=256))
    
    username=data["username"]
    
    if checkIfUsernameExists(username):
        lock.release()
        result["error"]="USERNAME_EXISTS"
        return result
        
    user=tables.User()
    
    for attr in ["username","password_hash"]:
        setattr(user,attr,data[attr])
    
    user.creation_time=int(time.time())
    
    type=data.get("type","SURFER")
    
    if type not in ["SURFER","ORDINARY","CORPORATE"]:
        result["error"]="INVALID_USER_TYPE"
        return result
    
    user.type=0
    user.addType(getattr(user,type))
    
    user.avatar=""
    
    with Session(common.database) as session:
        
        session.add(user)
        session.commit()
        
        user.inbox=posts.createPost({"author": user.id, "text":"This is your inbox.","keywords":[],"type":"INBOX"})
        user.profile=posts.createPost({"author": user.id, "text":"This is your profile.","keywords":[],"type":"PROFILE"})
        session.commit()
        
        lock.release()
        result["id"]=user.id
        if anonymous:
            result["password_hash"]=user.password_hash
    return result

@app.route("/users/info", methods = ['POST'])
@common.authenticate
def info():
    result={}
    
    uid=request.json["uid"]
    id=request.json.get("id",uid) #By default, use the current uid
    
    with Session(common.database) as session:
        user=users.getUser(id,session)
        if user is None:
            result["error"]="USER_NOT_FOUND"
            return result
        
        for col in user.__mapper__.attrs.keys():
            value=getattr(user,col)
            
            if col=="password_hash":
                continue
            elif col=="type":
                value=user.listTypes()
            elif col in ["following","liked_posts","disliked_posts","pictures","videos"]:
                value=common.fromStringList(value)
            elif col in ["inbox","blocked","id"] and id!=uid:
                continue
            result[col]=value
        
        return result
        
@app.route("/users/modify", methods = ['POST'])
@common.authenticate
def modify():
    result={}
    username=request.json.get("username",None)
    password=request.json.get("password_hash",None)
    uid=request.json["uid"]
    with Session(common.database) as session:
        lock.acquire()
        user=users.getUser(uid,session)
        
        if username is not None:
            if user.username==username:
                result["error"]="NAME_NOT_CHANGED"
                lock.release()
                return result
            elif session.scalars(select(tables.User.id).where(tables.User.username==username)).first() is not None:
                result["error"]="NAME_ALREADY_TAKEN"
                lock.release()
                return result
            else:
                user.username=username
                session.commit()
                lock.release()
        
        if password is not None:
            user.password_hash=password
            session.commit()
        return result

@app.route("/users/block", methods = ['POST'])
@common.authenticate
def block():
    result={}

    blocked_id=request.json["blocked_id"]
        
    uid=request.json["uid"]
    with Session(common.database) as session:
        user=users.getUser(uid,session)
        
        if user.has_blocked(blocked_id):
            result["error"]="ALREADY_BLOCKED"
            return
        user.blocked=appendToStringList(user.blocked,blocked_id)
        session.commit()
    return result

@app.route("/users/unblock", methods = ['POST'])
@common.authenticate
def unblock():
    result={}

    blocked_id=request.json["blocked_id"]
        
    uid=request.json["uid"]
    with Session(common.database) as session:
        user=users.getUser(uid,session)
        if not user.has_blocked(blocked_id):
            result["error"]="ALREADY_UNBLOCKED"
            return
        
        user.blocked=removeFromStringList(user.blocked,blocked_id)
        session.commit()
    return result
    
@app.route("/users/delete", methods = ['POST'])
@common.authenticate
def delete():
    result={}
    with Session(common.database) as session:
        lock.acquire()
        
        uid=request.json["uid"]
        id=request.json.get("id",uid)
        user=users.getUser(id,session)
        
        deleted_user=users.getUser(request.json["id"])
        
        if not(user.hasType(user.SUPER) or (deleted_user.id==user.id)):
            result["error"]="INSUFFICIENT_PERMISSION"
            return
            
        session.delete(deleted_user)
        session.commit()
        lock.release()
        return result

@app.route("/users/signin", methods = ['POST'])
def signin():
    result={}
    with Session(common.database) as session:
        username=request.json["username"]
        password=request.json["password_hash"]
            
        user=session.scalars(select(tables.User).where(tables.User.username==username)).first()
        
        if user is None:
            result["error"]="USER_NOT_FOUND"
            return result
        
        if password!=user.password_hash:
            result["error"]="PASSWORD_INCORRECT"
            return result
            
        result["uid"]=user.id
        return result                        

@app.route("/users/promote")
@common.authenticate
def change_type():
    result = {}
    
    target_type = request.json["target_type"]
    target_user=request.json["target_user"]
    operation=request.json.get("operation","ADD")
    uid=request.json["uid"]
    with Session(common.database) as session:
        user = users.getUser(target_user,session)
        
        if not( (user.hasType(user.SUPER) and target_user != uid) or (operation=="REMOVE")): #Users should be able to remove user types by themselves
            result["error"] = "INSUFFICIENT_PERMISSION"
            return result
        
        target_type = getattr(user, target_type)
        if operation=="ADD":
            user.addType(target_type)
        elif operation=="REMOVE":
            user.removeType(target_type)           

        session.commit()
    
    return result  

@app.route('/users/follow') #Despite the name, this does following and unfollowing together
@common.authenticate
def follow_user():
    result = {}
    
    target_user = request.json["target_user"]
    operation=request.json.get("operation","FOLLOW")
    
    uid=request.json["uid"]
    with Session(common.database) as session:
        # Retrieve the user who wants to follow
        user = users.getUser(uid,session)

        # Retrieve the target user
        target_user = users.getUser(target_user)
        if target_user is None:
            result["error"] = "TARGET_USER_NOT_FOUND"
            return result
        
        # Check if already following
        following_list = common.fromStringList(user.following)
        
        if operation=="FOLLOW":
            if str(target_user.id) in following_list:
                result["error"] = "ALREADY_FOLLOWED"
                return result
            else:
                following_list.append(str(target_user.id))  # Ensure it is stored as a string
                user.following = common.toStringList(following_list)
        elif operation=="UNFOLLOW":
            if str(target_user.id) not in following_list:
                result["error"] = "ALREADY_UNFOLLOWED"
                return result
            else:
               following_list.remove(str(target_user.id))
               user.following = common.toStringList(following_list) 

        
        # Commit the changes to the database
        session.commit()
        
        users.getUser(target_user.id).update_trendy_status() #Event handler
        session.commit()
        
        return result

@app.route("/users/tip")
@common.authenticate
def tip():
    result = {}
    
    uid=request.json["uid"]
    target_id=request.json["target_id"]
    amount=request.json.get("amount",1) #By default, tip $1
    
    if uid==target_id:
        result["error"]="SELF_TIP"
        return
    
    if amount < 0:
        result["error"]="NEGATIVE_TIP"
        return
    
    with Session(common.database) as session: #Check if uid has enough and that target has account
        user=users.getUser(uid,session)
        
        user_balance=balance.GetBalance(user.id)
        
        if user_balance is None:
            result["error"]="BALANCE_NOT_FOUND"
            return
        
        if balance.GetBalance(target_id) is None:
            result["error"]="TARGET_BALANCE_NOT_FOUND"
            return
        
        if balance.RemoveFromBalance(user.id,amount)==-1:
            result["error"]="BALANCE_TOO_SMALL"
            return
            
        balance.AddToBalance(target_id,amount)
        
        target_user=users.getUser(target_id,session)
        target_user.tips+=amount
        session.commit()
        
        target_user.update_trendy_status() #Event handler
        session.commit()       

@app.route("/users/top3posts")
@common.authenticate
def top3posts():
    result={}
    
    result["posts"]=[]
    
    user=users.getUser(request.json["uid"])
    query=select(tables.Post.id).where(tables.Post.is_trendy & not_(user.has_blocked(tables.Post.author))).order_by(desc(tables.Post.trendy_ranking)).limit(3)
    
    with Session(common.database) as session:
        result["posts"]=session.scalars(query).all()
    
    return result

@app.route("/users/top3users")
@common.authenticate
def top3users():
    result={}
    
    result["users"]=[]
    
    user=users.getUser(request.json["uid"])
    query=select(tables.User.id).where(tables.User.hasType(user.TRENDY) & not_(user.has_blocked(tables.Post.id))).order_by(desc(tables.User.trendy_ranking)).limit(3)
    
    with Session(common.database) as session:
        result["users"]=session.scalars(query).all()
    
    return result

#For suggest, just take the union of what the following follow. Sort by length of intersection between user following and they following. If space left over, add random users.

@app.route("/users/suggest")
@common.authenticate
def suggest():
    result={}
    
    uid=request.json["uid"]
    
    with Session(common.database) as session:
        user=users.getUser(uid,session)
        following=set(common.fromStringList(user.following))
        liked_posts=set(common.fromStringList(user.liked_posts))
        disliked_posts=set(common.fromStringList(user.disliked_posts))
        
        list_of_users=[]
        for row in session.scalars(select(tables.User.id,tables.User.following,tables.User.liked_posts,tables.User.disliked_posts).where(tables.User.id!=uid)).all(): #Based ranking on how common their interests are with yours. May be slow on large amount of users
            row[1]=set(common.fromStringList(row[1]))
            row[2]=set(common.fromStringList(row[2]))
            row[3]=set(common.fromStringList(row[3]))
            intersections=0
            intersections+=len(following.intersection(row[1]))
            intersections+=len(liked_posts.intersection(row[2]))
            intersections+=len(disliked_posts.intersection(row[3]))
            
            list_of_users.append([row[0],intersections])
    
    result["users"]=[_[0] for _ in heapq.nlargest(min(10,len(list_of_users)),list_of_users,key=lambda x: x[1])]
    
    return result



@app.route("/users/warn", methods=["POST"])
@common.authenticate
def assign_warning():
    result = {}

    uid = request.json["uid"]
    target_user = request.json["target_user"]
    
    with Session(common.database) as session:
        issuer = users.getUser(uid, session)  # The SUPER user issuing the warning
        recipient = users.getUser(target_user, session)  # The user to be warned

        # Check if issuer is SUPER and recipient is not SUPER
        if issuer.hasType(User.SUPER) and not recipient.hasType(User.SUPER):  #want to avoid a case where super user can just delete their own report against them by having super user not get reported
            recipient.warnings += 1  # Increment the warnings count
            recipient.time_of_last_warn = datetime.utcnow()  # Update the last warning time to now
        else:
            result["error"] = "INSUFFICIENT_PERMISSION_OR_INVALID_TARGET"
            return result

        session.commit()  

    result["message"] = "Warning assigned successfully"
    return result  

