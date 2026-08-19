from datetime import datetime, timedelta, timezone
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.User import User
from app.models.UserStats import UserStats


class LeaderboardRepository(BaseRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def GetLeaderboard(
        self,
        period: str = "all",
        limit: int = 20,
    ) -> list[tuple]:
        """Get leaderboard entries with user stats."""
        query = (
            select(
                UserStats.user_id,
                User.username,
                UserStats.points,
                UserStats.total_reports,
                UserStats.accurate_reports,
            )
            .join(User, User.id == UserStats.user_id)
            .where(User.is_anonymous == False)
        )

        if period == "week":
            one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            query = query.where(UserStats.updated_at >= one_week_ago)
        elif period == "month":
            one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
            query = query.where(UserStats.updated_at >= one_month_ago)

        query = query.order_by(desc(UserStats.points)).limit(limit)
        result = await self.db.execute(query)
        return result.all()