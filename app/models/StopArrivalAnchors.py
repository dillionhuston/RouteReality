import sqlalchemy as sa
from sqlalchemy import Column, String, ForeignKey, Integer, DateTime, Float, func
from app.models.Database import Base
from uuid import uuid4, UUID


class StopArrivalAnchors(Base):
    __tablename__ = "stoparrivalanchor"


    id = Column(String, nullable=False, primary_key=True)
    service_id = Column(String, nullable=True, index=True, unique=True)
    route_id = Column(String, nullable=True, index=True)
    stop_id = Column(String, nullable=True, index=True)
    source = Column(String, nullable=True)
    best_arrival_time = Column(DateTime(timezone=True), nullable=False)
    confidence = Column(Float, nullable= False)
    report_count = Column(Integer)
    last_reported_at = Column(DateTime, server_default=sa.func.now())
    updated_at = Column(DateTime, server_default=sa.func.now())

  