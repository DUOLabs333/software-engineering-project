from ..utils import common, tables, posts

from common import app

from flask import request
from sqlalchemy import select
from sqlalchemy import Session
from sqlalchemy import desc

def hasAccess(username):
    hash=request.get_data(as_text=True)
    with Session(common.database) as session:
        query=select(tables.Users.password_hash).where(tables.Users.username==username)
        return hash==session.scalars(query).first()
        
@app.route("/user/<username>/homepage")
def homepage(username):
    result={}
    if not hasAccess(username):
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
        
            
@app.route("/user/<username>/trending")
def trending(username):
    result={}
    if not hasAccess(username):
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
            if count==0:
                break
        
        return result