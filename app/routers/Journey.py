from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session

from app.models.Route import Route
from app.models.Database import get_db
from app.schemas.journey import StartJourney, JourneyEventType


from app.Services.journeyService.journey_service import JourneyService
from app.Services.journeyService.eventHandler import JourneyEventHandler


router = APIRouter(prefix="/journeys", tags=['Journeys'])


@router.post("/start")
def startJourney(
    journey: StartJourney,
    db: Session = Depends(get_db)):

    newJourney = JourneyService.start_journey(db=db, data=journey)
    return{"journey-id": str(newJourney.id), "status": journey.status} # example dummy data, function need to return status, id 
        
    
#This would be for exmaple arrived, delayed, stop reached. Rather than having stop, start delayed we can use a handler
@router.post("/{journey_id}/event")
def journeyEvent(
    event: JourneyEventType,
    db: Session = Depends(get_db)):
    #TODO
    event = JourneyEventHandler.addEvent(event, db)
      


    
    
    
    
