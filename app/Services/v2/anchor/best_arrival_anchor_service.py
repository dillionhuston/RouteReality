from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.StopArrivalAnchors import StopArrivalAnchors
from app.repositories.prediction_repository import PredictionRepository


class BestArrivalAnchorService:
    def __init__(self, prediction_repo: PredictionRepository):
        self.prediction_repo = prediction_repo

    async def update_or_create_anchor(
        self,
        service_id: str,
        stop_id: str,
        best_time: datetime,
        confidence: float,
        source: str):
        return await self.prediction_repo.UpsertAnchor(
            service_id, stop_id, best_time, confidence, source
        )

    async def get_latest_anchor(
        self,
        route_id: str,
        stop_id: str):

        anchor = await self.prediction_repo.GetLatestAnchor(route_id, stop_id)
        if anchor:
            if anchor.updated_at.tzinfo is None:
                anchor.updated_at = anchor.updated_at.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - anchor.updated_at) < timedelta(minutes=120):
                return anchor
        return None