import utils.common as common
from utils import balance
import utils.tables as tables
from sqlalchemy import select
from sqlalchemy import desc
from sqlalchemy.orm import Session
import re, time
from routes.posts import lock

def getPost(post_id,session=None):
    session_exists=True
    if session is None:
        session_exists=False #Have to make one
        session=Session(common.database,expire_on_commit=False) #Can be used outside session
        
    query=select(tables.Post).where(tables.Post.id==post_id)
    result=session.scalars(query).one_or_none()
    
    if session_exists:
        session.close() 
    return result

def createPost(data):
    post=tables.Post()
   
    with Session(common.database) as session:
        lock.acquire()
        
        post.id=(session.scalars(select(tables.Post.id).order_by(desc(tables.Post.id)).limit(1)).first() or 0)+1 #Get next biggest id
        post.time_posted=int(time.time())
        
        for attr in ["author","text"]:
            setattr(post,attr,data[attr])
        
        post.keywords=common.toStringList(data.get("keywords",[]))
        
        post.parent_post=data.get("parent_post",None)
        post.type=data.get("post_type","POST")
        
        for attr in ["views","likes","dislikes"]:
            setattr(post,attr,0)
        
        for attr in ["has_picture","has_video"]:
            setattr(post,attr,data.get(attr,False)) #Need to find a way to parse markdown for links --- maybe use regex for ![alt-text](link)
        
        session.add(post)
        session.commit()
        lock.release()
        return post.id
   
def cleanPostData(id,data,user):
    editable_fields=tables.Post.editable_fields
    
    word_match_regex = lambda word: rf"(?!'.*')\b[{word}']+\b"
    word_match = lambda string, word=r"\w": re.findall(word_match_regex(word),string)
    
    error=None
    data=data
    
    post=getPost(id)
    
    editable_fields=list(set(data.keys()).intersection(set(editable_fields)))
    
    if post is None: #Doesn't exist yet
        post=tables.User()
        for attr in editable_fields:
            setattr(post,attr,"")
    
    #Only charge for net added words --- you should pay for deleting words
    
    num_of_words = lambda string: len(word_match(string))
    
    words_in_post=0
    words_in_data=0
    for attr in editable_fields:
        words_in_post+=num_of_words(getattr(post,attr))
        words_in_data+=num_of_words(data[attr])
    
    limit=20
    extra_words_in_post=max(len(words_in_post)-limit,0)
    extra_words_in_data=max(len(words_in_data)-limit,0)
    
    #Charging logic
    if extra_words_in_data>0:
        if extra_words_in_post==0:  #TI you're originally below, and now you're over, ...
            extra_words=extra_words_in_data #... charge for the words that got you over
        else: #If you're originally above,...
            extra_words=max(words_in_data-words_in_post,0) #... charge for all net added words

    cost=0
    if user.hasType(user.CORPORATE):
        extra_words=max(words_in_data-words_in_post,0)
        cost=1*extra_words #$1 for every word
    elif user.hasType(user.ORDINARY) or user.hasType(user.TRENDY):
        cost=0.1*extra_words #$0.10 for every word over 20 words (Also need to check for images)
    else:
        error="INSUFFICIENT_PERMISSION" #Can't post without being at least OU
        return error, data
    
    cost+=0.1*len(data.get("pictures",[])) #0.10 for every picture      
    cost+=0.15*len(data.get("videos",[])) #0.15 for every video
    
    taboo_word_count=0
    taboo_list="taboo_list.txt"
    open(taboo_list,"a+") #Create file if doesn't exist
    taboo_list=open(taboo_list,"r").read().splitlines()
    taboo_list=[word.strip() for word in taboo_list]
    taboo_list=set(taboo_list)
    
    for attr in editable_fields:
        value=data[attr]
        for word in set(word_match(value)):
            if word in taboo_list:
                taboo_word_count+=len(word_match(value,word))
                value=re.sub(word_match_regex(re.escape(word)) ,"****",data[attr])
                data[attr]=value
                
            if taboo_word_count>2:
                #Warn --- set that up
                error="TOO_MANY_TABOOS"
                return error, data
    
    if len(data["keywords"])>3:
        error="TOO_MANY_KEYWORDS"
        return error, data
    
    if (data["type"] in ["AD","JOB"]) and (not user.hasType(user.CORPORATE)): #Non-CUs can not post ads.
        error="NOT_CORPORATE_USER"
        return error, data
    
    if cost>0:
        return_val=balance.RemoveFromBalance(user.id,cost)
        if return_val==-1: #If you can't pay
            error="NOT_ENOUGH_MONEY"
            return error, data
    return error, data