from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.Journey import Journey
from app.models.Route import RouteStop


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

    async def GetJourneyById(self, journey_id: str):

        stmt = select(Journey).where(Journey.id == journey_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def GetJourneysForStop(self,stop_id: str,limit: int = 100,hours: int = 24):

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        stmt = (
            select(Journey)
            .join(RouteStop, Journey.route_id == RouteStop.route_id)
            .where(RouteStop.stop_id == stop_id)
            .where(Journey.created_at >= cutoff)
            .order_by(desc(Journey.created_at), Journey.id)
            .distinct(Journey.created_at, Journey.id)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        journeys = result.scalars().all()

        # Total count
        count_stmt = (
            select(func.count(func.distinct(Journey.id)))
            .join(RouteStop, Journey.route_id == RouteStop.route_id)
            .where(RouteStop.stop_id == stop_id)
            .where(Journey.created_at >= cutoff)
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Active count
        active_statuses = ["on_route", "delayed", "departed", "in_progress", "en_route", "STARTED", "ARRIVED"]
        active_stmt = count_stmt.where(Journey.status.in_(active_statuses))
        active = (await self.db.execute(active_stmt)).scalar() or 0

        return journeys, total, active

    async def GetLatestJourneyByRoute(self, route_id: str) -> Journey | None:
        stmt = (
            select(Journey)
            .where(Journey.route_id == route_id)
            .order_by(desc(Journey.created_at))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def GetRouteJourneyCountToday(self, route_id: str) -> int:
        start_of_day = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        stmt = (
            select(func.count())
            .select_from(Journey)
            .where(
                Journey.route_id == route_id,
                Journey.created_at >= start_of_day,
            )
        )
        return (await self.db.execute(stmt)).scalar() or 0

    async def GetRecentJourneysByRoute(
        self,
        route_id: str,
        limit: int = 50):
        stmt = (
            select(Journey)
            .where(Journey.route_id == route_id)
            .order_by(desc(Journey.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def GetActiveJourneys(
        self,
        limit: int = 20):   
        active_statuses = ["STARTED", "ON_BUS", "ARRIVED", "DELAYED", "en_route", "on_route"]
        stmt = (
            select(Journey)
            .where(
                Journey.status.in_(active_statuses),
                Journey.ended_at.is_(None),
            )
            .order_by(desc(Journey.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()