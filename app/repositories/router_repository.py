from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.repositories.base import BaseRepository
from app.models.Route import Route, RouteStop, Stop

class RouteRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db)

    async def GetRouteID(self, route_id: str):
        result = await self.db.execute(select(Route).where(Route.id == route_id))
        return result.scalar_one_or_none()

    async def GetStartStopID(self, stop_id: str):
        result = await self.db.execute(select(Stop).where(Stop.id == stop_id))
        return result.scalar_one_or_none()

    async def GetEndStopID(self, end_stop: str):
        result = await self.db.execute(select(Stop).where(Stop.id == end_stop))
        return result.scalar_one_or_none()

    async def GetRoutesWithStops(self):
        stmt = select(Route).options(
        joinedload(Route.route_stops).joinedload(RouteStop.stop)).order_by(Route.name)
        result = await self.db.execute(stmt)
        return result.unique().scalars().all()  

    async def GetStopsByRoute(self, route_id: str):
        stmt = select(RouteStop).options(
        joinedload(RouteStop.stop)).where(RouteStop.route_id == route_id).order_by(RouteStop.sequence)
        result = await self.db.execute(stmt)
        return result.scalars().all() 

    async def GetRouteStopsForStop(self, stop_id: str):
        
        stmt = select(RouteStop).where(RouteStop.stop_id == stop_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def GetRouteStopsInOrder(self, route_id: str):

        stmt = (
            select(RouteStop)
            .where(RouteStop.route_id == route_id)
            .order_by(RouteStop.sequence)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def GetStopById(self, stop_id: str):

        stmt = select(Stop).where(Stop.id == stop_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()