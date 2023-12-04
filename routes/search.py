from utils import common,users,tables
from utils.common import app
from flask import request
from sqlalchemy.orm import Session
from sqlalchemy.types import Integer
from sqlalchemy import select, or_, not_, func, true
from sqlalchemy.sql.functions import register_function
import functools, operator

@app.route("/search", methods=["POST"])
@common.authenticate
def search():
    result={}
    
    authors=request.json["authors"]
    keywords=request.json["keywords"]
    likes=request.json["likes"]
    dislikes=request.json["dislikes"]
    types=request.json["types"] or ["POST"]
    sort=request.json["sort"] or "NEWEST"
    
    if not (all(type in tables.Post.public_post_types for type in types)):
        result["error"]="NON_PUBLIC_POST_TYPE"
        return

    for lst in [likes,dislikes]:
        lst[0]=(lst[0] or float("-inf")) #Lower bound: None means -Inf
        lst[1]=(lst[1] or float("inf")) #Upper bound: None means Inf
        
    uid=request.json["uid"]
    before=request.json["before"] or float("inf") #Pagination
    limit=request.json.get("limit",10)
    with Session(common.database) as session:
        user=users.getUser(uid,session)
        
        if authors is None:
            authors=true()
        else:
            query=select(tables.User.id).where(tables.User.username.in_(authors))
            authors=session.scalars(query).all()
            authors=tables.Post.author.in_(authors)
        
        #keywords=[tables.Post.text.regex_match(rf"\b{word}\b") for word in keywords] #May relax this to a simple "contains" if regex is too computationally expensive
        #Replace ~ with not_
        if keywords is None:  #If no keywords are given, implicitly allow everything
            keywords=[true()]
        else:
            keywords=[tables.Post.keywords.contains(f" {word} ") for word in keywords]
        
        if sort=="NEWEST":
            sort=tables.Post.id
        elif sort=="BEST":
            sort=functools.reduce(operator.add, [p.cast(Integer) for p in keywords])
        
        register_function("has_blocked",user.has_blocked)
        
        query=select(tables.Post.id).where(authors & or_(*keywords) & (tables.Post.likes >= likes[0]) & (tables.Post.likes <= likes[1]) & (tables.Post.dislikes >= dislikes[0]) & (tables.Post.dislikes <= dislikes[1]) & not_(func.has_blocked(tables.Post.author)) & tables.Post.is_viewable(user) & tables.Post.type.in_(types)).order_by(sort.desc()).where(tables.Post.id < before).limit(limit) #Order by number of keywords satisfied
        
        result["posts"]=session.scalars(query).all()
        result["before"]=common.last(result["posts"]) #New pagination parameter
    return result