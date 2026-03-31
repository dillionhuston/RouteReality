from typing import Optional, Tuple
from datetime import datetime, time, timezone, timedelta
from .data import get_recent_user_events, get_user_journeys
from .logic import predict_bus_time
from sqlalchemy.orm import Session
from app.models.StopArrivalAnchors import StopArrivalAnchors
from app.utils.logger.logger import get_logger

logger = get_logger(__name__)

def _prediction_source(journey_times, events, static_dt, anchor_exists: bool) -> str:
    if anchor_exists:
        return "live_scraped"      
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
    db: Session
) -> dict:
    
    now = datetime.now(timezone.utc)

   
    anchor = db.query(StopArrivalAnchors).filter(
        StopArrivalAnchors.stop_id == stop_id,
        StopArrivalAnchors.route_id == route_id
    ).order_by(StopArrivalAnchors.updated_at.desc()).first()

    use_anchor = anchor and (now - anchor.last_reported_at).total_seconds() < 3600  # valid < 1 hour

    if use_anchor:
        predicted_time = anchor.best_arrival_time
        confidence = anchor.confidence
        source = "live_scraped"
        logger.debug(f"Using scraped anchor for {route_id} @ {stop_id} → {predicted_time} (conf {confidence})")
    else:
      
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

        static_time = static_dt.time() if isinstance(static_dt, datetime) else static_dt

        try:
            predicted_time, confidence = predict_bus_time(
                static_time=static_time,
                user_events=recent_events,
                past_arrivals=past_arrivals,
                now=now
            )
        except Exception as e:
            logger.error(f"predict_bus_time failed: {e}", exc_info=True)
            predicted_time = static_dt or (now + timedelta(minutes=15))
            confidence = 0.15

        source = _prediction_source(past_arrivals, recent_events, static_dt, anchor_exists=False)

 
   
    delays = sum(1 for e in recent_events if e["type"] == "DELAYED")
    if delays >= 1:
        extra_min = 4 + delays * 3.5
        predicted_time += timedelta(minutes=extra_min)
        confidence = min(0.95, confidence + 0.15)

    # Safety net: never show past time
    if predicted_time < now:
        predicted_time = now + timedelta(minutes=3)
    
    return {
        "predicted_arrival": predicted_time.isoformat() if predicted_time else None,
        "confidence": round(confidence, 2),
        "source": source,
        "event_count": len(recent_events),
        "historical_count": len(past_arrivals),
    }