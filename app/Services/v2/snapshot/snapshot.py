from uuid import uuid4
from app.models.PredictionSnapshot import PredictionSnapshot
from app.repositories.snapshot_repository import SnapshotRepository
from app.exceptions.exceptions import ServiceError, DatabaseError
from datetime import datetime, time, timezone


class SnapshotService:
    
    def __init__(self, snapshot_repo: SnapshotRepository):
        self.snapshot_repo = snapshot_repo

    async def create_snapshot(
            self,
            journey_id: str,
            service_id: str,
            stop_id: str,
            user_reported_arrival: datetime,
            static_scheduled: datetime,
            best_trusted_arrival: datetime,
            predicted_arrival: datetime,
            confidence: float
    ):
        snapshot = PredictionSnapshot(
            id=str(uuid4()),
            journey_id=journey_id,
            service_id=service_id,
            stop_id=stop_id,
            user_reported_arrival=user_reported_arrival,
            static_scheduled=static_scheduled,
            best_trusted_arrival=best_trusted_arrival,
            predicted_arrival=predicted_arrival,
            confidence=confidence
        )
        try:
            return await self.snapshot_repo.CreateSnapshot(snapshot)
        except Exception as e:
            raise DatabaseError(detail=f"Failed to create prediction snapshot: {str(e)}")