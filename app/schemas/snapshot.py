from pydantic import BaseModel
from datetime import datetime



class CreateSnapshot(BaseModel):

    journey_id: str
    service_id: str
    stop_id: str
    user_reported_arrival: datetime
    static_scheduled: datetime
    best_trusted_arrival: datetime
    predicted_arrival: datetime
    confidence: float