from ..utils import common, tables
from common import app

from ..utils import users

from flask import request
from sqlalchemy import select
from sqlalchemy import Session

@app.route("/users/<username>/info")
def info(username):
    result={}
    if not common.hasAccess(username):
        result["error"]="ACCESS_DENIED"
        return result
    
    with Session(common.database) as session:
        query=select(tables.User).where(tables.User.username==username)
        user=session.scalars(query).first()
        
        if user is None:
            result["error"]="USERS_NOT_FOUND"
            return result
        
        result["result"]={}
        for col in user.__mapper__.attrs.keys():
            value=getattr(user,col)
            
            if col=="password_hash":
                continue
            elif col=="user_type":
                value=users.listTypes(value)
                
            result["result"][col]=value
        
        return result
            