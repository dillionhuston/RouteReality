from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.Journey import Journey
from app.schemas.journey import StartJourney

from datetime import datetime
from uuid import UUID
class JourneyService():
    def __init__(self):
        return
    
    def start_journey(data: StartJourney, db: Session):

        journey = Journey(
            route_id=data.route_id,
            start_stop_id=data.start_stop_id,
            end_stop_id = data.end_stop_id,
            start_time = datetime.now(tz=datetime.timezone.now),
            status="ACTIVE"
        )
        db.add(journey)
        db.commit()
        db.refresh()
        return journey
        

   
    
    def get_active_journey(db: Session, journey_id: UUID) -> Journey:

        journey = (
            db.query(Journey)
            .filter(
                Journey.id == journey.id,
                Journey.status == "ACTIVE",
                Journey.end_time.is_(None)
            )
            .one_or_none
        )

        if journey is None:
            raise HTTPException(
                status_code=404,
                detail = f"Active journey not found {journey.id}"
            )