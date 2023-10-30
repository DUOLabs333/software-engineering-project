#Should be imported by all relevant files

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

database = create_engine("sqlite:///test_db.db")

def createSession():
    return Session(database)