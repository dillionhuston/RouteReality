from sqlalchemy import Column, String, JSON, DateTime, Index
from sqlalchemy.sql import func
from app.core.Database import Base

class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(String, primary_key=True, index=True)  
    service_id = Column(String, nullable=False, index=True)  
    user_id = Column(String, nullable=True)   
    endpoint = Column(String, unique=True, nullable=False)
    keys = Column(JSON, nullable=False)  
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_push_subscriptions_service_id", "service_id"),
    )