import uuid
from sqlalchemy import String, Integer, Boolean, Column
from app.models.Database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    username = Column(String(60),unique=True, index=True)
    email = Column(String(60),unique=True, index=True)
    hashed_password = Column(String)
    is_anonymous = Column(Boolean)