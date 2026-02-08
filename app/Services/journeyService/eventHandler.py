#TODO Separate into own folder with one main service handler, and separate files for each event type

from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.utils.logger import logger
from app.models.Journey import Journey
from app.schemas.journey import JourneyEventType

from app.Services.Prediction.service import predict_bus_time

logger = logger.get_logger()


class JourneyEventHandler:
    @staticmethod
    def arrived(journey_id: UUID, db: Session) -> Journey:
        """Set user active journey status to arrived"""
        allowed = {"STARTED", "DELAYED"}
        journey = db.get(Journey, str(journey_id))

        if not journey:
            logger.warning(f"Journey not found: {journey_id}")
            raise HTTPException(404, f"Journey {journey_id} not found")

        if journey.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot mark as ARRIVED from status: {journey.status}"
            )
        
        journey.start_time = datetime.now(timezone.utc)
        journey.status = JourneyEventType.EVENT_TYPE_ARRIVED
        db.commit()
        db.refresh(journey)
        return journey
    

    @staticmethod
    def delayed(journey_id: UUID, db: Session) -> Journey:
        """Set user active journey status to DELAYED"""
        allowed = {JourneyEventType.EVENT_TYPE_STARTED}
        journey = db.get(Journey, str(journey_id))
        
        if not journey:
            raise HTTPException(404, f"Journey {journey_id} not found")

        if journey.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot mark as DELAYED from status: {journey.status}"
            )

        journey.status = JourneyEventType.EVENT_TYPE_DELAYED
       
        db.commit()
        db.refresh(journey)
        return journey
    

    @staticmethod
    def stop_reached(journey_id: UUID, db: Session) -> Journey:
        allowed = {JourneyEventType.EVENT_TYPE_STARTED, JourneyEventType.EVENT_TYPE_DELAYED, JourneyEventType.EVENT_TYPE_ARRIVED}
        journey = db.get(Journey, str(journey_id))

        if not journey:
            raise HTTPException(404, f"Journey {journey_id} not found")

        if journey.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot mark stop reached, journey is already finished ({journey.status})"
            )

        journey.status = JourneyEventType.EVENT_TYPE_STOP_REACHED
        journey.end_time = datetime.now(timezone.utc)
        db.commit()
        db.refresh(journey)
        return journey
 
    @staticmethod
    def add_event(
        journey_id: UUID,event_type: JourneyEventType, db: Session) -> Journey:

        handlers = {
            JourneyEventType.EVENT_TYPE_ARRIVED: JourneyEventHandler.arrived,
            JourneyEventType.EVENT_TYPE_DELAYED: JourneyEventHandler.delayed,
            JourneyEventType.EVENT_TYPE_STOP_REACHED: JourneyEventHandler.stop_reached,
        }
        handler = handlers.get(event_type)

        if handler is None:
            logger.warning(f"Unsupported event type received: {event_type}")
            raise HTTPException(400, f"Unsupported event type: {event_type}")
        return handler(journey_id, db)