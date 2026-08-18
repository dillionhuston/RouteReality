from app.repositories.base import BaseRepository
from sqlalchemy import select, desc
from app.models.Journey import Journey
from app.models.Route import RouteStop
from app.models.Event import Event   # your Event model
from datetime import datetime, timezone, timedelta
from typing import List


class EventRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db)

    async def GetRecentJourneysByRouteAndStop(
            self,route_id: str,
            stop_id: str, 
            limit: int = 10, 
            cutoff_minutes: int = 40, 
            now = datetime.now(timezone.utc)):
        
        cutoff = now - timedelta(minutes=cutoff_minutes)
        stmt = (
            select(Journey)
            .join(RouteStop, Journey.route_id == RouteStop.route_id)
            .where(
                Journey.route_id == route_id,
                RouteStop.stop_id == stop_id,
                Journey.created_at >= cutoff,
            )
            .order_by(desc(Journey.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def GetRecentEventsByRouteAndStop(
        self,
        route_id: str,
        stop_id: str,
        limit: int = 10,
        cutoff_minutes: int = 40):

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=cutoff_minutes)
        stmt = (
            select(Event)
            .join(Journey, Event.journey_id == Journey.id)
            .where(
                Journey.route_id == route_id,
                Event.stop_id == stop_id,
                Event.type.in_(["ARRIVED", "DELAYED"]),
                Event.created_at >= cutoff,
            )
            .order_by(desc(Event.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def CreateEvent(self, event: Event):
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event