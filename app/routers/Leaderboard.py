from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.Database import get_db
from app.repositories.leaderboard_repository import LeaderboardRepository
from app.dependencies.dependency import get_leaderboard_repository
from app.schemas.leaderboard import LeaderboardEntry

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


@router.get("", response_model=List[LeaderboardEntry])
async def get_leaderboard(
    period: str = Query("all", pattern="^(all|week|month)$"),
    limit: int = Query(20, ge=1, le=100),
    repo: LeaderboardRepository = Depends(get_leaderboard_repository)):
    
    results = await repo.GetLeaderboard(period, limit)

    leaderboard = []
    for rank, (user_id, username, points, total_reports, accurate_reports) in enumerate(results, 1):
        accuracy = (accurate_reports / total_reports * 100) if total_reports > 0 else 0
        leaderboard.append(LeaderboardEntry(
            rank=rank,
            user_id=user_id,
            username=username or "Unknown",
            points=points,
            total_reports=total_reports,
            accuracy=round(accuracy, 1),
        ))

    return leaderboard