from ..utils import common
from common import app
from ..utils import tables

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
        following=select(tables.User.following).where(tables.User.username==username)
        
        following=session.scalars(following).first()
        
        following=common.fromStringList(following)
        
        query=select(tables.Post.id).where((tables.Post.author.in_(following)) & (tables.Post.id < before)).limit(limit).order_by(desc(tables.Post.id))
        
        result["result"]=[]
        
        for row in session.scalars(query).all():
            result["result"].append(row)
        
        return result
            
