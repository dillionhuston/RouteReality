from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.Database import SessionLocal, engine, get_db  

from app.schemas.journey import StartJourney, AddJourneyEvent
from app.Services.journeyService.journey_service import JourneyService
from app.Services.journeyService.eventHandler import JourneyEventHandler
from app.utils.logger.logger import get_logger

from datetime import datetime


logger = get_logger(__name__) # give name  

COOLDOWN_SECONDS = 180  # 3 min cooldown. dont want people spamming events and ruin database. We have security on prod 

"""
    last_request_time need removed by v2.
    It resets on restart, will break with multiple workers and will mem leak in the future
    We also cant scale this either
    Replace with redis based cooldown or db?
    TEMPPP
"""
last_request_time: dict[UUID, datetime] = {}

router = APIRouter(prefix="/journeys", tags=["Journey"])



@router.post("/start")
def start_journey(journey: StartJourney, db: Session = Depends(get_db))-> dict:
    if not journey.start_stop_id or not journey.end_stop_id:
        raise HTTPException(
            status_code=400,
             detail= "Need both start and end stop to begin journey"
        )
    
    # Start a new journey
    try:
        new_j = JourneyService.start_journey(db=db, data=journey)
        if new_j is None:
             raise  ValueError("JourneyService returned None")
        logger.info(f"New journey started: {new_j.id} route={journey.route_id}")

    except ValueError as ve:
        logger.error(f"Failed to start journey: {ve}")
        raise HTTPException(status_code=500, detail=str(ve))
    
    except Exception as e:
        logger.error(f"Unexpected error starting journey: {e}")
        raise HTTPException(status_code=500, detail="Could not start journey due to server error")

    return {
        "journey_id": new_j.id,
        "route_id": new_j.route_id,
        "start_stop_id": new_j.start_stop_id,
        "end_stop_id": new_j.end_stop_id,
        "predicted_status": new_j.predicted_status,
        "predicted_arrival": new_j.predicted_arrival,  
        "current_status": new_j.status,
        "official_start_time": new_j.official_start_time,
        "created_at":  new_j.created_at
    }


@router.post("/{journey_id}/event")
def add_journey_event(journey_id: UUID, event: AddJourneyEvent, db: Session = Depends(get_db))-> dict:
    """Add event for journey. ARRIVED, DELAYED, STOP_REACHED"""
    now = datetime.now(timezone.utc)
    last_request_time[journey_id] = now

    updated = JourneyEventHandler.add_event(
            event_type=event.event.value,
            db=db,
            journey_id=journey_id
    )

    if not updated:
            logger.warning(f"Couldn't find active journey for {journey_id}")
            raise HTTPException(
                status_code=404,
                detail="Journey not found or already finished"
         )

    logger.info(f"Added {event.event} to journey {journey_id}")

    return {
            "journey_id": str(updated.id),
            "current_status": updated.status,
            "predicted_arrival": updated.predicted_arrival,
            "last_event": event.event.value,
            "updated_at": updated.created_at,
            "message": f"Got it - recorded {event.event}"
        }


