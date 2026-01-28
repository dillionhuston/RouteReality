from uuid import UUID
from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session

from datetime import datetime, timezone

from app.models.Route import Route
from app.models.Route import Stop          
from app.models.Database import get_db
from app.schemas.journey import StartJourney, JourneyEventType, AddJourneyEvent

from app.Services.journeyService.journey_service import JourneyService
from app.Services.journeyService.eventHandler import JourneyEventHandler


router = APIRouter(prefix="/journeys", tags=['Journeys'])

# Rate limiting variables. V2 will have a more robust retry logic 
last_request_time = {}
COOLDOWN_SECONDS = 180


@router.post("/start")
def start_journey(
    journey: StartJourney,
    db: Session = Depends(get_db)
    ):
    """
    User starts their journey by submitting route and start/end stops.
    Frontend sends plain string IDs (public_id values).
    """

    
    if not journey.start_stop_id:
        raise HTTPException(
            status_code=400,
            detail="Start stop is required"
        )

    if journey.end_stop_id is None:
        raise HTTPException(
            status=400,
            detail = "End stop is required"
        )
    


    new_journey = JourneyService.start_journey(db=db, data=journey)

    return {
        "journey_id": new_journey.id,  
        "route_id": new_journey.route_id,
        "start_stop_id": new_journey.start_stop_id,
        "predicted_status": new_journey.predicted_status,
        "predicted_arrival": new_journey.predicted_arrival,
        "status": new_journey.status
    }


@router.post("/{journey_id}/event")
def add_journey_event(
    journey_id: UUID,      
    event: AddJourneyEvent,
    db: Session = Depends(get_db)
):
    """
    User submits a journey event (Arrived, Delayed, StopReached, etc.)
    journey_id is the internal UUID returned from /start
    """

    now = datetime.now(timezone.utc)
    last_time = last_request_time.get(journey_id)

    if last_time:
        delta = (now - last_time).total_seconds()
        if delta < COOLDOWN_SECONDS:
            raise HTTPException(
                status = 429,
                detail =f"Too many requests for this journey. Try again in {int(COOLDOWN_SECONDS - delta)}s"
            )

    if not event.event:
        raise HTTPException(
            status_code=400,
            detail="Event type is required (e.g. Arrived, Delayed, StopReached)"
        )

    updated_journey = JourneyEventHandler.add_event(
        event_type=event.event,
        db=db,
        journey_id=journey_id  
    )

    if not updated_journey:
        raise HTTPException(
            status_code=404,
            detail=f"Journey {journey_id} not found or not active"
        )

    return {
        "journey_id": str(updated_journey.id),     
        "status": updated_journey.status,
        "predicted_arrival": updated_journey.predicted_arrival,
        "updated_at": updated_journey.created_at.isoformat() if updated_journey.created_at else None
    }