from sqlalchemy import Column, String
from .db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String(128), primary_key=True)  # 구글 sub
    email = Column(String(256), unique=True, index=True)