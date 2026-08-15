import uuid
from sqlalchemy import String, Integer, Boolean, Column, DateTime, func
from app.core.Database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    username = Column(String(60), unique=True, index=True, nullable=True)
    email = Column(String(60), unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    is_anonymous = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())