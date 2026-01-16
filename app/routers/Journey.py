from uuid import UUID
from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.models.BusRoute import Route
from app.models.Database import get_db
from app.schemas.journey import StartJourney, JourneyEventType, AddJourneyEvent

from app.Services.journeyService.journey_service import JourneyService
from app.Services.journeyService.eventHandler import JourneyEventHandler


router = APIRouter(prefix="/journeys", tags=['Journeys'])

@router.post("/start")
def startJourney(
    journey: StartJourney,
    db: Session = Depends(get_db)):
    """ User starts their journey y submitting their route and start/end stops """


    # (Dillon) - Frontend dev has got to implement field check to see if route has been selected
    Journey = StartJourney
    if not Journey.start_stop_id or not Journey.end_stop_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid start or end stop. Can not create journey "
        )
    
    newJourney = JourneyService.start_journey(db=db, data=journey)

    return{       
         "id": newJourney.id,
         "predicted_status": newJourney.predicted_status,
         "predicted_arrival": newJourney.predicted_arrival
    }
        
    
  
@router.post("/{journey_id}/event")
def add_journey_event(
    event: AddJourneyEvent,
    journey_id: UUID,
    db: Session = Depends(get_db)):
    """User submits an event. Bus arrived, delayed, stop reached"""


    updated_journey = JourneyEventHandler.add_event(
        event_type=event,
        db=db,
        journey_id=journey_id
    )

    if not AddJourneyEvent:
        raise HTTPException(
            status_code="405",
            detail="You must provide a valid event. Arrived, Delayed, StopReached"
        )
    
    return {
        "journey_id": str(updated_journey.id),
        "status": updated_journey.status
    }
      


    
    
    
    
