from uuid import UUID
from fastapi import Depends, APIRouter
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

    newJourney = JourneyService.start_journey(db=db, data=journey)
    return[
        {
            "id": newJourney.id,
            "predicted_status": newJourney.predicted_status,
            "predicted_arrival": newJourney.predicted_arrival

        }
    ]
  
    
#This would be for exmaple arrived, delayed, stop reached. Rather than having stop, start delayed we can use a handler
# Triggered with user press
@router.post("/{journey_id}/event")
def add_journey_event(
    event: AddJourneyEvent,
    journey_id: UUID,
    db: Session = Depends(get_db)):

    updated_journey = JourneyEventHandler.add_event(
        event_type=event,
        db=db,
        journey_id=journey_id
    )
    
    return {
        "journey_id": str(updated_journey.id),
        "status": updated_journey.status
    }
      


    
    
    
    
