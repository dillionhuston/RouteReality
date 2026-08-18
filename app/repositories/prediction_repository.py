from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.StopArrivalAnchors import StopArrivalAnchors
from app.models.HistoricalDelay import HistoricalDelay

class PredictionRepository(BaseRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def GetLatestAnchor(self, route_id: str, stop_id: str):
        stmt = (
            select(StopArrivalAnchors)
            .where(
                StopArrivalAnchors.route_id == route_id,
                StopArrivalAnchors.stop_id == stop_id
            )
            .order_by(desc(StopArrivalAnchors.updated_at))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def GetHistoricalDelay(self, route_id: str, stop_id: str, dt: datetime) -> float | None:
        hour = dt.hour
        stmt = (
            select(HistoricalDelay)
            .where(
                HistoricalDelay.route_id == route_id,
                HistoricalDelay.stop_id == stop_id,
                HistoricalDelay.hour == hour,
                HistoricalDelay.sample_count >= 5
            )
            .order_by(desc(HistoricalDelay.last_updated))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()
        return record.avg_delay_min if record else None

    async def GetAnchorByServiceAndStop(self, service_id: str, stop_id: str) -> StopArrivalAnchors | None:
        stmt = (
            select(StopArrivalAnchors)
            .where(
                StopArrivalAnchors.service_id == service_id,
                StopArrivalAnchors.stop_id == stop_id
            )
            .order_by(desc(StopArrivalAnchors.updated_at))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def UpdateAnchor(self, anchor: StopArrivalAnchors):
        await self.db.commit()
        await self.db.refresh(anchor)

    async def CreateAnchor(self, anchor: StopArrivalAnchors):
        self.db.add(anchor)
        await self.db.commit()
        await self.db.refresh(anchor)



    async def UpsertAnchor(
    self,
    service_id: str,
    stop_id: str,
    best_time: datetime,
    confidence: float,
    source: str):
        
        existing = await self.GetAnchorByServiceAndStop(service_id, stop_id)
        now = datetime.now(timezone.utc)

        if existing:
            if now - existing.updated_at < timedelta(minutes=120):
                existing.best_arrival_time = best_time
                existing.confidence = confidence
                existing.report_count += 1
            else:
                if confidence > existing.confidence:
                    existing.best_arrival_time = best_time
                    existing.confidence = confidence
                existing.report_count += 1
            existing.last_reported_at = now
            existing.updated_at = now
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        else:
            new_anchor = StopArrivalAnchors(
                id=str(uuid4()),
                service_id=service_id,
                stop_id=stop_id,
                best_arrival_time=best_time,
                source=source,
                confidence=confidence,
                report_count=1,
                last_reported_at=now,
                updated_at=now
            )
            self.db.add(new_anchor)
            await self.db.commit()
            await self.db.refresh(new_anchor)
            return new_anchor