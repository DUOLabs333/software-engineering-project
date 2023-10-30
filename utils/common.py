#Should be imported by all relevant files

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from flask import Flask, request

database = create_engine("sqlite:///test_db.db")

app=Flask("backend_server")

def fromStringList(string):
    return string.split(" ")

def hasAccess(username):
    hash=request.get_data(as_text=True)
    with Session(common.database) as session:
        query=select(tables.Users.password_hash).where(tables.Users.username==username)
        return hash==session.scalars(query).first()