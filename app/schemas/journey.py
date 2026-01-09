from pydantic import BaseModel, datetime_parse
from datetime import datetime


class StartJourney(BaseModel):

    route_id: str
    start_stop_id: str
    end_stop_id: str


class JourneyEventType():

    EVENT_TYPE_ARRIVED =  "ARRIVED"
    EVENT_TYPE_STOP_REACHED = "STOP_REACHED"
    EVENT_TYPE_DELAYED = "DELAYED"

