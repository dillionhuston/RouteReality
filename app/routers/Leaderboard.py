from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from pydantic import BaseModel

from app.core.Database import get_db
from app.models.User import User
from app.models.UserStats import UserStats
from app.schemas.leaderboard import LeaderboardEntry

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])

@router.get("", response_model=List[LeaderboardEntry])
def get_leaderboard(
    period: str = Query("all", regex="^(all|week|month)$"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)):
    
    """Get leaderboard by points, showing latest points"""
    query = db.query(
        UserStats.user_id,
        User.username,
        UserStats.points,
        UserStats.total_reports,
        UserStats.accurate_reports
    ).join(User, User.id == UserStats.user_id)
    
    if period == "week":
        one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        query = query.filter(UserStats.updated_at >= one_week_ago)
    elif period == "month":
        one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        query = query.filter(UserStats.updated_at >= one_month_ago)
    
    query = query.filter(User.is_anonymous == False)
    
    # Order by points (descending)
    results = query.order_by(desc(UserStats.points)).limit(limit).all()
    
    leaderboard = []
    for rank, (user_id, username, points, total_reports, accurate_reports) in enumerate(results, 1):
        accuracy = (accurate_reports / total_reports * 100) if total_reports > 0 else 0
        
        leaderboard.append(LeaderboardEntry(
            rank=rank,
            user_id=user_id,
            username=username or "Unknown",
            points=points,
            total_reports=total_reports,
            accuracy=round(accuracy, 1)
        ))
    
    return leaderboard