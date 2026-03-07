from app.models.Database import Base
from sqlalchemy import Column, String, ForeignKey, Integer, Float, DateTime, Boolean

from enum import Enum



class JourneyEventType(str, Enum):


    EVENT_TYPE_ARRIVED =  "ARRIVED"
    EVENT_TYPE_DELAYED = "DELAYED"
    EVENT_TYPE_JOURNEY_ENDED = "JOURNEY_ENDED"
    
class Event(Base):
    __tablename__ = "journey_events"

    id = Column(String, nullable=False, primary_key=True)
    journey_id = Column(String, ForeignKey("journeys.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    stop_id = Column(String, ForeignKey("stops.id"))

    type = Column(String, nullable=False, index=True)
    reported_time= Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), index=True, nullable=False)