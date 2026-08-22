from fastapi import APIRouter, Depends
from datetime import datetime

from app.core.Database import get_db
from app.models.User import User
from app.dependencies.get_current_user import get_current_user
from app.dependencies.dependency import get_user_stats_repository
from app.repositories.user_stats_repository import UserStatsRepository
from app.schemas.user import UserProfileResponse, UserStatsResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user)):
    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at if hasattr(current_user, 'created_at') else datetime.now(),
        is_guest=getattr(current_user, 'is_anonymous', False)
    )


@router.get("/me/stats", response_model=UserStatsResponse)
async def get_my_stats(
    current_user: User = Depends(get_current_user),  # <-- This should be using get_current_user
    stats_repo: UserStatsRepository = Depends(get_user_stats_repository)):
    
    stats = await stats_repo.GetOrCreateUserStats(current_user.id)
    
    accuracy = (stats.accurate_reports / stats.total_reports * 100) if stats.total_reports > 0 else 0
    badges = stats.earned_badges.split(',') if stats.earned_badges else []
    
    return UserStatsResponse(
        points=stats.points,
        streak_current=stats.streak_current,
        streak_best=stats.streak_best,
        total_reports=stats.total_reports,
        accurate_reports=stats.accurate_reports,
        accuracy_percentage=round(accuracy, 1),
        last_report_date=stats.last_report_date,
        badges=badges
    )