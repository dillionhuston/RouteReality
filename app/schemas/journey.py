from pydantic import BaseModel, datetime_parse, Field
from datetime import datetime
from enum import Enum



class JourneyEventType(str, Enum):
    # For when user selects their route and is added to database
    EVENT_TYPE_STARTED = "STARTED"

    EVENT_TYPE_PENDING = "PENDING"

    # This is for when the user submits their bus has arrived. The journey is now active
    EVENT_TYPE_ARRIVED =  "ARRIVED"

    # Delayed event
    EVENT_TYPE_DELAYED = "DELAYED"

    # User Journey stops
    EVENT_TYPE_STOP_REACHED = "STOP_REACHED"
    



class StartJourney(BaseModel):
    route_id: str = Field(..., description="Public route identifier (e.g. '16', '2a')")
    start_stop_id: str = Field(..., description="Public stop identifier (ATCO code)")
    end_stop_id: str | None = None
    planned_start_time: datetime | None = None



class AddJourneyEvent(BaseModel):
    event: JourneyEventType



