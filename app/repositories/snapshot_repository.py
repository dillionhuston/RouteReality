import uuid
from app.repositories.base import BaseRepository
from app.models.PredictionSnapshot import PredictionSnapshot
from app.schemas.snapshot import CreateSnapshot


class SnapshotRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db)

    async def CreateSnapshot(self, snapshot: CreateSnapshot):
            self.db.add(snapshot)
            await self.db.commit()
            await self.db.refresh(snapshot)
            return snapshot



