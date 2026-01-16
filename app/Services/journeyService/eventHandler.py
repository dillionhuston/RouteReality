#TODO Seperate into own folder with one main service handler, and seperate files for each event type


from datetime import  datetime, timezone
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.utils.logger import logger
from app.models.Journey import Journey
from app.schemas.journey import JourneyEventType
#from app.Services.journeyService.journey_service import get_active_journey

logger = logger.get_logger(__name__)


class JourneyEventHandler:
    @staticmethod
    def arrived(journey_id: UUID, db: Session) -> Journey:
        """ Set user active journey status to arrived"""

        # Only allow the user to set their journey as arrived if the journey has started
        # Also allow to set as arrived if the bus has been delayed beforehand

        allowed = {"STARTED", "DELAYED"}
        journey = db.get(Journey, journey_id)

        if not journey:
            logger.error(f"Journey not found: {journey_id}")
            raise HTTPException(404, f"Journey {journey_id} not found")

        if journey.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot mark as ARRIVED from status: {journey.status}"
            )
        
        journey.status = "ARRIVED"
        journey.start_time = datetime.now(timezone.utc)  
        db.commit()
        db.refresh(journey)
        return journey


    @staticmethod
    def delayed(journey_id: UUID, db: Session) -> Journey:
        """Set user active journey status to DELAYED"""

        allowed = {"STARTED"}  
        journey = db.get(Journey, journey_id)
        if not journey:
            raise HTTPException(404, f"Journey {journey_id} not found")

        if journey.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot mark as DELAYED from status: {journey.status}"
            )

        journey.status = "DELAYED"

        #TODO Add notified time
        db.commit()
        db.refresh(journey)
        return journey

    @staticmethod
    def stop_reached(journey_id: UUID, db: Session) -> Journey:
        allowed = {"ARRIVED"}  
        journey = db.get(Journey, journey_id)

        if not journey:
            raise HTTPException(404, f"Journey {journey_id} not found")

        if journey.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot mark stop reached journey is already finished ({journey.status})"
            )

        journey.status = "STOP_REACHED"
        journey.end_time = datetime.now(timezone.utc)
        db.commit()
        db.refresh(journey)
        return journey
 
    @staticmethod
    def add_event(
        journey_id: UUID,
        event_type: JourneyEventType,
        db: Session
    ) -> Journey:
        handlers = {
            JourneyEventType.EVENT_TYPE_ARRIVED: JourneyEventHandler.arrived,
            JourneyEventType.EVENT_TYPE_DELAYED: JourneyEventHandler.delayed,
            JourneyEventType.EVENT_TYPE_STOP_REACHED: JourneyEventHandler.stop_reached,
        }

        handler = handlers.get(event_type)

        if handler is None:
            logger.warning(f"Unsupported event type received: {event_type}")
            raise HTTPException(400, f"Unsupported event type: {event_type.value}")

        
        return handler(journey_id, db)