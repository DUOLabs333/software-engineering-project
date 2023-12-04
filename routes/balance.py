#Have import and export

from utils import common, balance, tables
from sqlalchemy.orm import Session
from utils.common import app
from flask import request

@app.route("/balance/init", methods=["POST"])
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

@app.route("/balance/view",methods=["POST"])
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

@app.route("/balance/import", methods=["POST"])
@common.authenticate
def _import():
    result={}
    
    bal=balance.GetBalance(request.json["uid"])
    if bal is None:
        result["error"]="BALANCE_DOES_NOT_EXIST"
        return result
    else:
        balance.import_from_CC(request.json)
    
    return result

@app.route("/balance/export", methods=["POST"]) #We don't want to trap people's money! (Maybe add a threshold to prevent paying CC fees for non-substantial exports
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
        return
        
    
    return result


