import asyncio
from datetime import datetime, timezone, timedelta
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.routers.Broadcast import broadcast_service_update
from app.utils.logger import logger
from app.models.Journey import Journey
from app.schemas.journey import JourneyEventType
from app.Services.Prediction.service import get_prediction
from app.Services.push_service.push_service import send_notifications_to_service

from app.models.Database import SessionLocal
from app.models.PushSubscription import PushSubscription

logger = logger.get_logger()

_main_loop: asyncio.AbstractEventLoop | None = None

def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop

    
def _fire_broadcast(service_id: str, payload: dict) -> None:
    if _main_loop is None:
        logger.warning("Broadcast skipped: main loop not set")
        return
    try:
        asyncio.run_coroutine_threadsafe(
            broadcast_service_update(service_id, payload),
            _main_loop
        )
    except Exception as e:
        logger.warning(f"Broadcast failed (non-critical): {e}")

class JourneyEventHandler:

    @staticmethod
    def update_prediction(journey: Journey, db: Session) -> None:
        if not journey.end_stop_id and not journey.start_stop_id:
            logger.warning(f"No stop to predict for journey {journey.id}")
            return

        stop_id = journey.end_stop_id or journey.start_stop_id

        try:
            predicted_iso = get_prediction(
                route_id=journey.route_id,
                stop_id=stop_id,
                static_dt=datetime.now(timezone.utc),
                db=db
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

        _fire_broadcast(journey.service_id, {
            "type": "BUS_ARRIVED",
            "message": "Bus has arrived at this stop",
            "route_id": journey.route_id,
            "stop_id": journey.start_stop_id,
        })
        try:
            db_session = SessionLocal()
            send_notifications_to_service(
                db=db_session,
                service_id=journey.service_id,
                title=f"Bus {journey.route_id} arrived",
                body=f"The bus has arrived at stop {journey.start_stop_id}.",
                url=f"/tracking?service={journey.service_id}"
            )
            db_session.close()
        except Exception as e:
            logger.warning(f"Push notification sending failed: {e}")

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
                predicted = journey.predicted_arrival
                if isinstance(predicted, datetime):
                    dt = predicted
                else:
                    dt = datetime.fromisoformat(str(predicted).replace("Z", "+00:00"))
                journey.predicted_arrival = (dt + timedelta(minutes=10)).isoformat()
            except Exception as e:
                logger.warning(f"Could not adjust existing prediction: {e}")
                JourneyEventHandler.update_prediction(journey, db)
        else:
            JourneyEventHandler.update_prediction(journey, db)

        db.commit()
        db.refresh(journey)

        _fire_broadcast(journey.service_id, {
            "type": "BUS_DELAYED",
            "message": "Delay reported on this route",
            "route_id": journey.route_id,
            "stop_id": journey.start_stop_id,
        })

        try:
            db_session = SessionLocal()
            send_notifications_to_service(
                db=db_session,
                service_id=journey.service_id,
                title=f"Bus {journey.route_id} delayed",
                body=f"The bus has been delayed at stop {journey.start_stop_id}.",
                url=f"/tracking?service={journey.service_id}"
            )
            db_session.close()
        except Exception as e:
            logger.warning(f"Push notification sending failed: {e}")
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

        JourneyEventHandler.update_prediction(journey, db)

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