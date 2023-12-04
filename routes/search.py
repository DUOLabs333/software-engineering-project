from utils import common,users,tables
from utils.common import app
from flask import request
from sqlalchemy.orm import Session
from sqlalchemy.types import Integer
from sqlalchemy import select, or_
import functools, operator

@app.route("/search", methods=["POST"])
@common.authenticate
def search():
    result={}
    
    authors=request.json["authors"]
    if not isinstance(authors, list):
        authors=[authors]
    
    keywords=request.json["keywords"]
    if not isinstance(keywords, list):
        keywords=[keywords]
    
    likes=request.json["likes"]
    dislikes=request.json["dislikes"]
    types=request.json.get("types",["POST"])
    
    if not (all(type in tables.Post.public_post_types for type in types)):
        result["error"]="NON_PUBLIC_POST_TYPE"
        return

    for lst in [likes,dislikes]:
        lst[0]=(likes[0] or float("-inf")) #Lower bound: None means -Inf
        lst[1]=(likes[0] or float("inf")) #Upper bound: None means Inf
    
    uid=request.json["uid"]
    before=request.json["before"] or float("inf") #Pagination
    limit=request.json.get("limit",float("10"))
    with Session(common.database) as session:
        user=users.getUser(uid,session)
        
        if authors is None:
            authors=True
        else:
            query=select(tables.User.id).where(tables.User.username.in_(authors))
            authors=session.scalars(query).all()
            authors=tables.Post.author.in_(authors)
        
        #keywords=[tables.Post.text.regex_match(rf"\b{word}\b") for word in keywords] #May relax this to a simple "contains" if regex is too computationally expensive
        
        if keywords is None:  #If no keywords are given, implicitly allow everything
            keywords=[True]
        else:
            keywords=[tables.Post.keywords.contains(f" {word} ") for word in keywords]
        
        query=select(tables.Post.id).where(authors & or_(*keywords) & (tables.Post.likes >= likes[0]) & (tables.Post.likes <= likes[1]) & (tables.Post.dislikes >= dislikes[0]) & (tables.Post.dislikes <= dislikes[1]) & ~(user.has_blocked(tables.Post.author)) & tables.Post.id < before & tables.Post.is_viewable(user) & tables.Post.type.in_(types)).order_by(functools.reduce(operator.add, [p.cast(Integer) for p in keywords]).desc()).limit(limit) #Order by number of keywords satisfied
        
        result["posts"]=session.scalars(query).all()
        result["before"]=common.last(result["posts"]) #New pagination parameter
    return result