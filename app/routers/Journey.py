from typing import List
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload
from app.models.Database import SessionLocal, engine, get_db  
from app.models.Route import Route, Stop, RouteStop
from app.schemas.route import StopsPerRoute, RouteOut
from app.schemas.journey import StartJourney, AddJourneyEvent
from app.Services.journeyService.journey_service import JourneyService
from app.Services.journeyService.eventHandler import JourneyEventHandler
from app.utils.logger.logger import get_logger

logger = get_logger(__name__) # give name  

COOLDOWN_SECONDS = 180  # 3 min cooldown. dont want people spamming events and ruin database. We have security on prod 

# yeah this is not thread safe at all. Works for now, fix with redis or thread when it starts to hurt
last_request_time: dict[UUID, datetime] = {}

router = APIRouter(prefix="/journeys", tags=["Route"])

@router.post("/start")
def start_journey(journey: StartJourney, db: Session = Depends(get_db)):
    if not journey.start_stop_id or not journey.end_stop_id:
        raise HTTPException(400, "Need both start and end stop to begin journey")

    # business logic in service
    new_j = JourneyService.start_journey(db=db, data=journey)

    logger.info(f"New journey started: {new_j.id} route={journey.route_id}")

    return {
        "journey_id": new_j.id,
        "route_id": new_j.route_id,
        "start_stop_id": new_j.start_stop_id,
        "end_stop_id": new_j.end_stop_id,
        "predicted_status": new_j.predicted_status,
        "predicted_arrival": new_j.predicted_arrival,  
        "current_status": new_j.status,
        "official_start_time": new_j.official_start_time,
        "created_at": new_j.created_at
    }


@router.post("/{journey_id}/event")
def add_journey_event(journey_id: UUID, event: AddJourneyEvent, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)

    # super basic anti-spam, we have security in prod
    if journey_id in last_request_time:
        diff = (now - last_request_time[journey_id]).total_seconds()
        if diff < COOLDOWN_SECONDS:
            secs_left = int(COOLDOWN_SECONDS - diff)
            raise HTTPException(429, f"Chill for {secs_left} seconds please")

    if not event.event:
        raise HTTPException(400, "What event? Need to tell me what happened")

    last_request_time[journey_id] = now

    updated = JourneyEventHandler.add_event(
        event_type=event.event,
        db=db,
        journey_id=journey_id
    )

    if not updated:
        logger.warning(f"Couldn't find active journey {journey_id}")
        raise HTTPException(404, "Journey not found or already finished")

    logger.info(f"Added {event.event} to journey {journey_id}")

    return {
        "journey_id": str(updated.id),
        "current_status": updated.status,
        "predicted_arrival": updated.predicted_arrival,
        "last_event": event.event,
        "updated_at": updated.created_at.isoformat() if updated.created_at else None,
        "message": f"Got it - recorded {event.event}"
    }


__all__ = ["route_router", "journey_router"]