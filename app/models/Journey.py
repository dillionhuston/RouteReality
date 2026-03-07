from sqlalchemy import Column, String, ForeignKey, DateTime, Float, func
from app.models.Database import Base
from uuid import uuid4

class Journey(Base):
    __tablename__ = "journeys"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    service_id    = Column(String, index=True, nullable=False)
    route_id      = Column(String, ForeignKey("routes.id"), nullable=False)
    start_stop_id = Column(String, ForeignKey("stops.id"), nullable=False)
    end_stop_id   = Column(String, ForeignKey("stops.id"), nullable=True)
    user_id       = Column(String, ForeignKey("users.id"), nullable=True)

    status = Column(String, nullable=False, index=True)  

    planned_start_time  = Column(DateTime(timezone=False), nullable=False)
    official_start_time = Column(DateTime(timezone=False), nullable=True)
    reported_arrival          = Column(DateTime(timezone=False), nullable=True)
    ended_at            = Column(DateTime(timezone=False), nullable=True)

    predicted_arrival   = Column(DateTime(timezone=False), nullable=True)
    confidence          = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())