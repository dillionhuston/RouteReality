from pydantic import BaseModel, datetime_parse
from datetime import datetime



class JourneyEventType():
    # For when user selects their route and is added to database
    EVENT_TYPE_STARTED = "STARTED"

    # This is for when the user submits their bus has arrived. The journey is now active
    EVENT_TYPE_ARRIVED =  "ARRIVED"

    # Delayed event
    EVENT_TYPE_DELAYED = "DELAYED"

    # User Journey stops
    EVENT_TYPE_STOP_REACHED = "STOP_REACHED"
    


class StartJourney(BaseModel):

    route_id: str
    start_stop_id: str
    end_stop_id: str



class AddJourneyEvent(BaseModel):
    event: str



