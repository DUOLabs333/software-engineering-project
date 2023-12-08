import utils.common as common
from utils import balance
import utils.tables as tables
from sqlalchemy.orm import Session
import re, time

def getPost(post_id,session=None):
    return common.getItem(tables.Post,post_id,session)

def createPost(data):
    post=tables.Post()
   
    with Session(common.database) as session:
        
        post.time_posted=int(time.time())
        
        for attr in ["author","text"]:
            setattr(post,attr,data[attr])
        
        for attr in ["keywords","images","videos"]:
            setattr(post,attr, common.toStringList(data.get(attr,[])))
        
        post.parent=data.get("parent",None)
        post.type=data.get("type","POST")
        
        for attr in ["views","likes","dislikes"]:
            setattr(post,attr,0)
        
        session.add(post)
        session.commit()
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
        post=tables.Post()
        for attr in editable_fields+["images","videos"]:
            setattr(post,attr,"")
    else:
        if post.author!=user.id:
            error="INSUFFICIENT_PERMISSION"
            return 0, error, data
    
    #Only charge for net added words --- you should pay for deleting words
    
    num_of_words = lambda string: len(word_match(string))
    
    words_in_post=0
    words_in_data=0
    for attr in editable_fields:
        words_in_post+=num_of_words(getattr(post,attr))
        words_in_data+=num_of_words(str(data[attr]))
    
    words_in_post+=(10*len(common.fromStringList(getattr(post,"images")))+ 15*len(common.fromStringList(getattr(post,"videos")))) #A picture is really worth 1000 words, or in this case, 10
    words_in_data+=(10*len(data.get("images",[]))+15*len(data.get("videos",[])))
    
    limit=20
    extra_words_in_post=max(words_in_post-limit,0)
    extra_words_in_data=max(words_in_data-limit,0)
    
    #Charging logic
    if extra_words_in_data>0:
        if extra_words_in_post==0:  #TI you're originally below, and now you're over, ...
            extra_words=extra_words_in_data #... charge for the words that got you over
        else: #If you're originally above,...
            extra_words=max(words_in_data-words_in_post,0) #... charge for all net added words
    else:
        extra_words=0

    cost=0
    if user.hasType(user.CORPORATE):
        extra_words=max(words_in_data-words_in_post,0)
        cost=1*extra_words #$1 for every word
    elif user.hasType(user.ANON):
        cost=0.1*extra_words #$0.10 for every word over 20 words (Also need to check for images)
    else:
        error="INSUFFICIENT_PERMISSION" #Can't post without being at least OU
        return cost, error, data
    
    taboo_word_count=0
    taboo_list="taboo_list.txt"
    open(taboo_list,"a+") #Create file if doesn't exist
    taboo_list=open(taboo_list,"r").read().splitlines()
    taboo_list=[word.strip() for word in taboo_list]
    taboo_list=set(taboo_list)
    
    for attr in editable_fields:
        value=data[attr]
        was_list=False
        if isinstance(value,list):
            value=common.toStringList(value)
            was_list=True
            
        for word in set(word_match(value)):
            if word in taboo_list:
                taboo_word_count+=len(word_match(value,word))
                value=re.sub(word_match_regex(re.escape(word)) ,"****",data[attr])
                    
            if taboo_word_count>2:
                #Warn --- set that up
                error="TOO_MANY_TABOOS"
                return cost, error, data
        
        if was_list:
            value=common.fromStringList(value)
        data[attr]=value
    if len(data["keywords"])>3:
        error="TOO_MANY_KEYWORDS"
        return cost, error, data
    
    if (data["type"] in ["AD","JOB"]) and (not user.hasType(user.CORPORATE)): #Non-CUs can not post ads.
        error="NOT_CORPORATE_USER"
        return cost, error, data
    
    if cost>0:
        return_val=balance.RemoveFromBalance(user.id,cost)
        if return_val==-1: #If you can't pay
            error="NOT_ENOUGH_MONEY"
            return cost, error, data
    
    return cost, error, data