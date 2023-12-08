from utils import common, users, posts
from utils.common import app
from flask import request
from sqlalchemy.orm import Session
import json

@app.route("/reports/approve")
@common.authenticate
def approve_report():
    result = {}

    uid = request.json["uid"]  # The user ID of the SUPER user approving the report
    target = request.json["target"]  # ID of the report being approved
    approve=request.json.get("approve",True)
    
    with Session(common.database) as session:
        user = users.getUser(uid, session)
        
        # Check if the user is a SUPER user
        if not user.hasType(user.SUPER):
            result["error"] = "INSUFFICIENT_PERMISSION"
            return result
        
        report = posts.getPost(target,session)

        # Verify the report exists and it's of type 'REPORT'
        if not(report and report.type == "REPORT" and " OPEN " in report.keywords):
            result["error"]="INVALID_REPORT"
            return result
            
        complainee=posts.getPost(json.loads(report.text)["target"]).author
        complainee = users.getUser(complainee)  # Get the user being reported
        
        if approve==True:
            data={
            "author":uid,
            "text": json.loads(report.text)["reason"],
            "parent": complainee.inbox,
            "type": "WARNING"
            }
            posts.createPost(data)
            
            report.keywords=report.keywords.replace("OPEN","APPROVED")
        else:
            session.delete(report)
        
        session.commit()

    return result

@app.route("/disputes/approve")
@common.authenticate
def approve_dispute():
    result = {}

    uid = request.json["uid"]  # The user ID of the SUPER user approving the report
    target = request.json["target"]  # ID of the dispute being approved
    approve=request.json.get("approve",True)
    
    with Session(common.database) as session:
        user = users.getUser(uid, session)
        
        # Check if the user is a SUPER user
        if not user.hasType(user.SUPER):
            result["error"] = "INSUFFICIENT_PERMISSION"
            return result
        
        dispute = posts.getPost(target,session)

        # Verify the report exists and it's of type 'REPORT'
        if not(dispute and dispute.type == "DISPUTE"):
            result["error"]="INVALID_DISPUTE"
            return result
        
        report=posts.getPost(json.loads(dispute.text)["target"],session)
        complainer=report.author
        complainer = users.getUser(complainer)  # Get the user being reported
        
        if approve==True:
            data={
            "author":uid,
            "text": "Frivolous report",
            "parent": complainer.inbox,
            "type": "WARNING"
            }
            posts.createPost(data)
            
            report.keywords=report.keywords.replace("OPEN","CLOSED")
            
            inbox=posts.getPost(users.getUser(dispute.author).inbox,session)
            
            inbox.likes+=3 #Reward/consolation prize to complainee
        
        session.delete(dispute)
        
        session.commit()

    return result