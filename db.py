import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

#engine = create_engine('sqlite:///:memory:', echo=True)
engine = create_engine('sqlite:///hello', echo=True)
Base = declarative_base()
Session = sessionmaker(bind=engine)

session = None
def get_session():
  global session
  if session is None:
    Base.metadata.create_all(engine)
    session = Session()
  return session
