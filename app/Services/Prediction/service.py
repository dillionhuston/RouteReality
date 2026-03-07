from typing import Optional, Tuple
from datetime import datetime, time, timezone, timedelta
from .data import get_recent_user_events, get_user_journeys
from .logic import predict_bus_time
from sqlalchemy.orm import Session
from app.utils.logger.logger import get_logger

logger = get_logger(__name__)

def _prediction_source(journey_times, events, static_dt) -> str:
    if events:
        return "live"
    if journey_times:
        return "historical"
    if static_dt:
        return "timetable"
    return "fallback"


def get_prediction(
    route_id: str,
    stop_id: str,
    static_dt: Optional[datetime],
    db: Session) -> dict:
    
    now = datetime.now(timezone.utc)

    past_arrivals = get_user_journeys(
        db=db,
        route_id=route_id,
        stop_id=stop_id,
        limit=10
    )

    recent_events = get_recent_user_events(
        db=db,
        route_id=route_id,
        stop_id=stop_id
    )

    try:
        predicted_time, confidence = predict_bus_time(
            static_time=static_dt,
            user_events=recent_events,
            past_arrivals=past_arrivals,
            now=now
        )
    except Exception as e:
        logger.error(f"predict_bus_time failed: {e}", exc_info=True)
        predicted_time = static_dt or (now + timedelta(minutes=15))
        confidence = 0.15

    source = _prediction_source(past_arrivals, recent_events, static_dt)

    return {
        "predicted_arrival": predicted_time.isoformat() if predicted_time else None,
        "confidence": confidence,
        "source": source,
        "event_count": len(recent_events),
        "historical_count": len(past_arrivals),
    }