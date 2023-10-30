#Should be imported by all relevant files

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from flask import Flask

database = create_engine("sqlite:///test_db.db")

app=Flask("backend_server")

def fromStringList(string):
    return string.split(" ")