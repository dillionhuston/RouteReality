from datetime import datetime, timezone, timedelta
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.Route import Route, Stop
from app.models.Journey import Journey
from app.schemas.journey import StartJourney, JourneyEventType
from app.utils.fetch_time import get_closest_scheduled_time_to_now
from app.Services.v2.prediction.prediction_service import PredictionService
from app.Services.v2.snapshot.snapshot import SnapshotService
from app.utils.logger.logger import get_logger
from app.routers.Broadcast import broadcast_service_update

logger = get_logger()

class JourneyService:
    """Service for creating and querying journeys."""

    @staticmethod
    async def start_journey(data: StartJourney, db: Session) -> dict:
        route = db.query(Route).filter(Route.id == data.route_id).first()
        if not route:
            raise HTTPException(404, f"Route {data.route_id} not found")

        start_stop = db.query(Stop).filter(Stop.id == data.start_stop_id).first()
        if not start_stop:
            raise HTTPException(404, f"Start stop {data.start_stop_id} not found")

        end_stop = None
        if data.end_stop_id:
            end_stop = db.query(Stop).filter(Stop.id == data.end_stop_id).first()
            if not end_stop:
                raise HTTPException(404, f"End stop {data.end_stop_id} not found")

        planned = data.planned_start_time or datetime.now(timezone.utc)
        if planned.tzinfo is None:
            planned = planned.replace(tzinfo=timezone.utc)

        official_start_str = planned

        result = get_closest_scheduled_time_to_now(
            route_id=data.route_id,
            stop_id=data.start_stop_id,
            reference_time=planned,
        )
        scheduled_time = None
        if result:
            scheduled_time, _, _ = result
            if scheduled_time:
                sched_dt = datetime.combine(planned.date(), scheduled_time, tzinfo=timezone.utc)
                if sched_dt > planned:
                    planned = sched_dt
                    official_start_str = planned.isoformat()
        else:
            logger.warning("No scheduled time found, using planned time")

        pred_svc = PredictionService()
        eta = None
        confidence = 0.3
        try:
            eta, confidence = pred_svc.get_prediction(
                db=db,
                route_id=data.route_id,
                target_stop_id=data.start_stop_id,
                planned_start_time=planned
            )
        except Exception as e:
            logger.error(f"Initial prediction failed: {e}")

        # Fallback if prediction is None
        if eta is None:
            default_duration = timedelta(minutes=20)   
            eta = planned + default_duration
            confidence = 0.1
            logger.info(f"Using fallback ETA: {eta}")

        journey_id = str(uuid4())
        journey = Journey(
            id=journey_id,
            service_id=f"{data.route_id}_{datetime.now().strftime('%Y%m%d_%H%M')}",
            route_id=data.route_id,
            start_stop_id=data.start_stop_id,
            end_stop_id=data.end_stop_id,
            planned_start_time=planned,
            status="STARTED",
            created_at=datetime.now(timezone.utc),
            official_start_time=official_start_str,
            predicted_arrival=eta,
            confidence=confidence
        )
        db.add(journey)
        db.commit()
        db.refresh(journey)

        # Snapshot
        try:
            SnapshotService.create_snapshot(
                db=db,
                journey_id=journey.id,
                service_id=journey.service_id,
                stop_id=data.start_stop_id,
                user_reported_arrival=None,
                static_scheduled=planned,
                best_trusted_arrival=eta or planned,
                predicted_arrival=eta,
                confidence=confidence
            )
            db.commit()
        except Exception as e:
            logger.error(f"Initial snapshot failed: {e}")
            db.rollback()

        
        try:
            minutes_remaining = int((eta - datetime.now(timezone.utc)).total_seconds() / 60) if eta else None
            await broadcast_service_update(
                journey.service_id,
                {
                    "current_status": "STARTED",
                    "predicted_arrival": eta.isoformat() if eta else None,
                    "minutes_remaining": minutes_remaining,
                    "message": "Journey started"
                }
            )
        except Exception as e:
            logger.error(f"Broadcast failed on start: {e}")

        logger.info(f"Start success - journey_id: {journey_id}, status: STARTED")

        return {
            "journey_id": journey_id,
            "service_id": journey.service_id,
            "status": "STARTED",
            "planned_start_time": planned.isoformat(),
            "predicted_arrival": eta.isoformat() if eta else None,
            "confidence": confidence
        }

    @staticmethod
    def get_active_journey(journey_id: str, db: Session) -> Journey:
        """Find a journey that's still going (no end time)."""
        journey = db.query(Journey).filter(
            Journey.id == journey_id,
            Journey.ended_at.is_(None),
            Journey.status.in_([
                JourneyEventType.STARTED.value,
                JourneyEventType.ARRIVED.value,
                JourneyEventType.DELAYED.value,
            ])
        ).first()

        if journey is None:
            raise HTTPException(
                status_code=404,
                detail=f"No active journey found for {journey_id}"
            )

        return journey