import uuid
from sqlalchemy import Column, String, Integer, DateTime, Date, ForeignKey, func
from app.models.Database import Base

class UserStats(Base):
    __tablename__ = "user_stats"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # Points and streaks
    points = Column(Integer, default=0, nullable=False)
    streak_current = Column(Integer, default=0, nullable=False)
    streak_best = Column(Integer, default=0, nullable=False)
    
    # Report tracking
    total_reports = Column(Integer, default=0, nullable=False)
    accurate_reports = Column(Integer, default=0, nullable=False)
    last_report_date = Column(Date, nullable=True)
    
    # Badge tracking
    earned_badges = Column(String, nullable=True)  # Comma-separated badge IDs
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())