from sqlalchemy import Column, String, ForeignKey, Integer, Float, DateTime
from app.models.base import Base



class Journey(Base):

    __tablename__ = "journeys"

    id = Column(String, primary_key=True, index=True)
    route_id = Column(String, ForeignKey("routes.id"), nullable=False)
    start_stop_id = Column(String, ForeignKey("stops.id"),nullable=False)
    end_stop_id = Column(String, ForeignKey("stops.id"))
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, nullable=True) #completed, delayed etc
    created_at = Column(DateTime, nullable=False)

    predicted_status = Column(DateTime, nullable=False)
    predicted_arrival = Column(DateTime, nullable=False)

