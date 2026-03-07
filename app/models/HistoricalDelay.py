from sqlalchemy import Column, String, Float, Integer, DateTime, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from app.models.Database import Base

class HistoricalDelay(Base):
    __tablename__ = "historical_delays"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    route_id = Column(String, nullable=False, index=True)
    stop_id = Column(String, nullable=False, index=True)
    hour = Column(Integer, nullable=False)           # 0–23
    avg_delay_min = Column(Float, nullable=False)
    sample_count = Column(Integer, nullable=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('route_id', 'stop_id', 'hour', name='unique_route_stop_hour'),
    )