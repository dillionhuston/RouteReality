
import sqlalchemy as sa
from sqlalchemy import Column, String, ForeignKey, DateTime, Float, func
from app.models.Database import Base
from uuid import uuid4, UUID


class PredictionSnapshot(Base):
    __tablename__ = "predictionsnapshot"

    id = Column(String, nullable=False, primary_key=True)
    journey_id = Column(String, ForeignKey("journeys.id"))
    service_id = Column(String, nullable=True, index=True)
    stop_id = Column(String, nullable=True, index=True)
    static_scheduled = Column(DateTime(timezone=True), nullable=False)
    predicted_arrival = Column(DateTime(timezone=True), nullable=False)
    user_reported_arrival = Column(DateTime(timezone=True), nullable=False)
    best_trusted_arrival = Column(DateTime(timezone=True), nullable=False)
    confidence = Column(Float, nullable= False)
    source_summary = Column(String, nullable=True)
    calculated_at = Column(DateTime, server_default=sa.func.now())

  