from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.UserStats import UserStats

class UserStatsRepository(BaseRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def GetUserStats(self, user_id: str) -> UserStats | None:
        result = await self.db.execute(select(UserStats).where(UserStats.user_id == user_id))
        return result.scalar_one_or_none()

    async def CreateUserStats(self, stats: UserStats):
        self.db.add(stats)
        await self.db.commit()
        await self.db.refresh(stats)
        return stats

    async def UpdateUserStats(self, stats: UserStats):
        await self.db.commit()
        await self.db.refresh(stats)
        return stats