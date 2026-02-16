
from datetime import datetime, time, timezone
from .data import get_recent_user_events, get_user_journeys
from .logic import predict_bus_time
from sqlalchemy.orm import Session

def _prediction_source(journeys, events, static_time):
    if events:
        return "live"
    if journeys:
        return "historical"
    if static_time:
        return "fallback"
    

def get_prediction(
        route_id: str,
        stop_id: str,
        static_time: datetime, 
        db: Session)-> dict:
    
    now = datetime.now(timezone.utc)

    journey_times = get_user_journeys(
        db=db,
        route_id=route_id,
        stop_id=stop_id,
        limit=10)

    events = get_recent_user_events(
        db=db,
        route_id=route_id,
        stop_id=stop_id
    )

    predicted_time, confidence = predict_bus_time(

        static_time=static_time,
        user_events=events,
        past_arrivals=journey_times,
        now=now)
    
    return {
        "predicted_time": predicted_time,
        "confidence": confidence,
        "source": [_prediction_source(journey_times, events, static_time)]}

   


