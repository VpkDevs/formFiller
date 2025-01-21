from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    username = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

class Database:
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)
        self.Session = sessionmaker(bind=self.engine)
    
    @contextmanager
    def session(self):
        session = self.Session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

def get_user_by_email(session, email: str):
    return session.query(User).filter(User.email == email).first()

def save_user_to_db(session, username: str, email: str, password: str):
    new_user = User(username=username, email=email, password=password)
    session.add(new_user)
