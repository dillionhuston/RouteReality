from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.Journey import Journey


class JourneyRepository(BaseRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def AddJourney(self, journey: Journey):
        self.db.add(journey)
        await self.db.commit()
        await self.db.refresh(journey)
        return journey

    async def GetActiveJourney(self, journey_id: str) -> Journey | None:
        stmt = (
            select(Journey)
            .where(
                Journey.id == journey_id,
                Journey.ended_at.is_(None),
                Journey.status.in_(["STARTED", "ARRIVED", "DELAYED"])
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def UpdateJourneyStatus(self, journey: Journey, status: str, ended_at: Optional[datetime] = None):
        """Update the status of a journey and optionally set ended_at."""
        journey.status = status
        journey.updated_at = datetime.now(timezone.utc)
        if ended_at:
            journey.ended_at = ended_at
        await self.db.commit()
        await self.db.refresh(journey)
        return journey

    async def AddDelay(self, journey: Journey, minutes: int = 10):
        """Add delay to a journey's predicted arrival."""
        if journey.predicted_arrival:
            journey.predicted_arrival += timedelta(minutes=minutes)
        journey.status = "DELAYED"
        journey.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(journey)
        return journey

    async def GetRecentArrivedJourneys(
        self,
        route_id: str,
        stop_id: str,
        limit: int = 10,
        now: Optional[datetime] = None):

        if now is None:
            now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=40)
        stmt = (
            select(Journey)
            .join(Journey.route_stops) 
            .where(
                Journey.route_id == route_id,
                Journey.start_stop_id == stop_id,
                Journey.created_at >= cutoff,
                Journey.status == "ARRIVED"
            )
            .order_by(desc(Journey.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()