from datetime import datetime, timezone, timedelta
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.utils.logger import logger
from app.models.Journey import Journey
from app.schemas.journey import JourneyEventType
from app.Services.Prediction.service import get_prediction

logger = logger.get_logger()


class JourneyEventHandler:

    @staticmethod
    def update_prediction(journey: Journey) -> None:
        if not journey.end_stop_id and not journey.start_stop_id:
            logger.warning(f"No stop to predict for journey {journey.id}")
            return

        stop_id = journey.end_stop_id or journey.start_stop_id

        try:
            predicted_iso = get_prediction(
                route_id=journey.route_id,
                stop_id=stop_id,
                static_dt=datetime.now(timezone.utc)
            )
            if predicted_iso:
                journey.predicted_arrival = predicted_iso  

        except Exception as e:
            logger.exception(f"Prediction failed for journey {journey.id}: {e}")

    @staticmethod
    def arrived(journey_id: UUID, db: Session) -> Journey:
        allowed = {JourneyEventType.EVENT_TYPE_STARTED, JourneyEventType.EVENT_TYPE_DELAYED}
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

        if journey.predicted_arrival:
            try:
                dt_str = journey.predicted_arrival.replace("Z", "+00:00")
                dt = datetime.fromisoformat(dt_str)
                journey.predicted_arrival = (dt + timedelta(minutes=10)).isoformat()
            except Exception as e:
                logger.warning(f"Could not adjust existing prediction: {e}")
                JourneyEventHandler.update_prediction(journey)
        else:
            JourneyEventHandler.update_prediction(journey)

        db.commit()
        db.refresh(journey)
        return journey

    @staticmethod
    def stop_reached(journey_id: UUID, db: Session) -> Journey:
        allowed = {JourneyEventType.EVENT_TYPE_ARRIVED, JourneyEventType.EVENT_TYPE_DELAYED}
        journey = db.get(Journey, str(journey_id))

        if not journey:
            raise HTTPException(404, f"Journey {journey_id} not found")

        if journey.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot mark stop reached from status: {journey.status}"
            )

        journey.status = JourneyEventType.EVENT_TYPE_STOP_REACHED
        journey.end_time = datetime.now(timezone.utc)

        # After reaching a stop,  predict next / final
        JourneyEventHandler.update_prediction(journey)

        db.commit()
        db.refresh(journey)
        return journey

    @staticmethod
    def add_event(
        journey_id: UUID,
        event_type: JourneyEventType,
        db: Session) -> Journey:

        handlers = {
            JourneyEventType.EVENT_TYPE_ARRIVED: JourneyEventHandler.arrived,
            JourneyEventType.EVENT_TYPE_DELAYED: JourneyEventHandler.delayed,
            JourneyEventType.EVENT_TYPE_STOP_REACHED: JourneyEventHandler.stop_reached,
        }

        handler = handlers.get(event_type)
        if handler is None:
            logger.warning(f"Unsupported event type: {event_type}")
            raise HTTPException(400, f"Unsupported event type: {event_type}")

        return handler(journey_id, db)