from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.PushSubscription import PushSubscription

class PushSubscriptionRepository(BaseRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def GetSubscriptionsByService(self, service_id: str):
        stmt = select(PushSubscription).where(PushSubscription.service_id == service_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def DeleteSubscription(self, subscription: PushSubscription):
        await self.db.delete(subscription)
        await self.db.commit()

    async def DeleteSubscriptions(self, subscriptions: list[PushSubscription]):
        for sub in subscriptions:
            await self.db.delete(sub)
        await self.db.commit()