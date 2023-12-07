from utils import common, tables, users, jobs

from utils import posts

from utils.common import app

from flask import request, send_file
from sqlalchemy import select, desc, not_
from sqlalchemy.orm import Session

import base64, os, random, string
import multiprocessing
from pathlib import Path
import datetime from datetime


@app.route("/posts/reportpage", methods = ['POST'])
@common.authenticate
def reportpage():
    result={}
    limit=request.json.get("limit",50)
    before=request.json.get("before",float("inf"))
    
    uid=request.json["uid"]
    user=users.getUser(uid)
    with Session(common.database) as session:
        
        report_query = select(tables.Post.id).where(user.has_followed(tables.Post.author) & (tables.Post.id < before) & not_(user.has_blocked(tables.Post.author)) & (tables.Post.type == "REPORT")).limit(limit).order_by(desc(tables.Post.id))
        posts = session.scalars(report_query).all()  # Fetch report posts
        result["reports"]=session.scalars(posts).all()
        
        return result   


@app.route("/posts/reports", methods=['POST'])
@common.authenticate
def report_post():
    result = {}

    uid = request.json["uid"]
    target_user = request.json["target_user"]
    report_text = request.json["report_text"]
   
    with Session(common.database) as session:
        complainer = users.getUser(uid, session)        #user making report
        complainee = users.getUser(target_user, session)  # The user to be reported
        report_data = {
                "author": uid,
                "text": "Report by User (ID: {}) against(ID: {}) :\n{}".format(complainer.id,complainee.id, report_text), #report by complainer against complainee and then report text
                "type": "REPORT",  
            }
            
        # Clean the report data as we would for creating a regular post
        error, data = posts.cleanPostData(None, report_data, complainer)  #filter taboo
        if error!=None:
            result["error"]=error
            return
            
        # Create the report post
        result["id"] = posts.createPost(data)
            

@app.route("/posts/reports/dispute", methods=['POST'])
@common.authenticate        #this endpoint feels a little weird, i might have to work on it more
def dispute_report():
    result = {}
    
    uid = request.json["uid"] #the user id for complainee
    report_id = request.json["report_id"]  # ID of the report being disputed
    dispute_text = request.json["dispute_text"]  # The text the complainee adds to dispute the report
    
    with Session(common.database) as session:
        complainee = users.getUser(uid, session) 
        report = session.query(tables.Post).filter(tables.Post.id == report_id)

        # Ensure the report exists and the complainee is the one being reported
        if  report.author == complainee.id and report.type == "DISPUTE":
            # Update the report text with the dispute information
            report.text += "\n\nDispute by User (ID: {}):\n{}".format(complainee.id, dispute_text)
            session.commit()
            result["message"] = "Report dispute has been recorded."
        else:
            result["error"] = "Report not found or permission denied."
            
    
    return result


@app.route("/posts/reports/approve", methods=['POST'])
@common.authenticate
def approve_report():
    result = {}

    uid = request.json["uid"]  # The user ID of the SUPER user approving the report
    report_id = request.json["report_id"]  # ID of the report being approved
    target_user = request.json["target_user"]

    with Session(common.database) as session:
        super_user = users.getUser(uid, session)
        
        # Check if the user is a SUPER user
        if not super_user.hasType(User.SUPER):
            result["error"] = "INSUFFICIENT_PERMISSION"
            return result
        
        report = session.query(tables.Post).filter(tables.Post.id == report_id)

        # Verify the report exists and it's of type 'REPORT'
        if report and report.type == "REPORT":
            complainee = users.getUser(target_user, session)  # Get the user being reported
            complainee.warnings += 1  # Increment the warnings count
            complainee.time_of_last_warn = datetime.utcnow()  # add warning based on current time

            session.commit()
            result["message"] = "Report has been approved and warning issued."
        else:
            result["error"] = "Report not found." #can't find report

    return result

@app.route("/posts/reports/disapprove", methods=['POST'])
@common.authenticate
def disapprove_report():
    result = {}

    uid = request.json["uid"]  # The user ID of the SUPER user approving the report
    report_id = request.json["report_id"]  # ID of the report being approved
    target_user = request.json["target_user"]

    with Session(common.database) as session:
        super_user = users.getUser(uid, session)
        
        # Check if the user is a SUPER user
        if not super_user.hasType(User.SUPER):
            result["error"] = "INSUFFICIENT_PERMISSION"
            return result
        
        report = session.query(tables.Post).filter(tables.Post.id == report_id)
        # Verify the report exists and it's of type 'REPORT'
        if report and report.type == "REPORT":
