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