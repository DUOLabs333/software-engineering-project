from utils import balance

def charge_for_post(post,session):
    if balance.RemoveFromBalance(post.author,0.1)==-1:
        post.hidden=True
        session.commit()
        return -1