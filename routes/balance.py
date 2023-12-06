#Have import and export

from utils import common, balance, tables
from sqlalchemy.orm import Session
from utils.common import app
from flask import request

@app.route("/balance/init")
@common.authenticate
def init():
    result={}
    
    with Session(common.database) as session:
        bal=tables.Balance()
        
        if balance.GetBalance(request.json["uid"]) is not None:
            result["error"]="BALANCE_ALREADY_EXISTS"
            return result
        
        bal.id=request.json["uid"] #Every user can have at most one balance anyways, so why have an extra set of ids?
        session.add(bal)
        session.commit()
        
    return result

@app.route("/balance/view")
@common.authenticate
def view():
    result={}
    
    bal=balance.GetBalance(request.json["uid"])
    if bal is None:
        result["error"]="BALANCE_DOES_NOT_EXIST"
        return result
    else:
        result["balance"]=bal
    
    return result

@app.route("/balance/import")
@common.authenticate
def _import():
    result={}
    
    bal=balance.GetBalance(request.json["uid"])
    if bal is None:
        result["error"]="BALANCE_DOES_NOT_EXIST"
        return result
    else:
        error=balance.import_from_CC(request.json)
        if error==-1:
            result["error"]="UNKNOWN_ERROR"
            return result
    
    return result

@app.route("/balance/export") #We don't want to trap people's money! (Maybe add a threshold to prevent paying CC fees for non-substantial exports
@common.authenticate
def export():
    result={}
    
    bal=balance.GetBalance(request.json["uid"])
    if bal is None:
        result["error"]="BALANCE_DOES_NOT_EXIST"
        return result
    else:
        error=balance.export_to_CC(request.json)
    if error==-1:
        result["error"]="NOT_ENOUGH_MONEY"
        return result
    elif error==-2:
        result["error"]="UNKNOWN_ERROR"
        return result
        
    
    return result


