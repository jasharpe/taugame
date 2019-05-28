import os
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

if 'db' in os.environ and os.environ['db'] == 'mysql':
    password = os.environ['mysql_password']
    addr = os.environ['mysql_addr']
    db_name = os.environ['db_name']
    engine = create_engine('mysql+pymysql://root:%s@%s/%s' % (password, addr, db_name), echo=False)
else:
    engine = create_engine('sqlite:///sqlite_db', echo=False)
    #engine = create_engine('sqlite:///:memory:', echo=True)
Base = declarative_base()
Session = sessionmaker(bind=engine)

session = None
def get_session():
  global session
  if session is None:
    Base.metadata.create_all(engine)
    session = Session()
  session.rollback()
  return session
