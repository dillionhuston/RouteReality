from datetime import datetime, timezone, timedelta, UTC
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.Route import Route, Stop
from app.models.PredictionSnapshot import PredictionSnapshot
from app.models.Journey import Journey
from app.schemas.journey import StartJourney, JourneyEventType
from app.utils.fetch_time import get_closest_scheduled_time_to_now
from app.Services.v2.prediction.prediction_service import PredictionService
from app.utils.logger.logger import get_logger
from app.routers.Broadcast import broadcast_service_update

from app.repositories.router_repository import RouteRepository
from app.repositories.journey_repository import JourneyRepository
from app.repositories.snapshot_repository import SnapshotRepository

logger = get_logger(__name__)

class JourneyService:
    def __init__(
        self,
        route_repo: RouteRepository,
        prediction_service: PredictionService,
        journey_repo: JourneyRepository,
        snapshot_repo: SnapshotRepository,
    ):
        self.route_repo = route_repo
        self.pred_svc = prediction_service
        self.journey_repo = journey_repo
        self.snapshot_repo = snapshot_repo

    async def start_journey(self, data: StartJourney):

        route = await self.route_repo.GetRouteID(data.route_id)
        if not route:
            raise ValueError(f"Route {data.route_id} not found")

        start_stop = await self.route_repo.GetStartStopID(data.start_stop_id)
        if not start_stop:
            raise ValueError(f"Start stop {data.start_stop_id} not found")

        end_stop = None
        if data.end_stop_id:
            end_stop = await self.route_repo.GetEndStopID(data.end_stop_id)
            if not end_stop:
                raise ValueError(f"End stop {data.end_stop_id} not found")

        planned = data.planned_start_time or datetime.now(timezone.utc)
        if planned.tzinfo is None:
            planned = planned.replace(tzinfo=timezone.utc)

        # Get scheduled time
        result = get_closest_scheduled_time_to_now(
            route_id=data.route_id,
            stop_id=data.start_stop_id,
            reference_time=planned,
        )
        if result:
            scheduled_time, _, _ = result
            if scheduled_time:
                sched_dt = datetime.combine(planned.date(), scheduled_time, tzinfo=timezone.utc)
                if sched_dt > planned:
                    planned = sched_dt

        # Get prediction
        eta = None
        confidence = 0.3
        try:
            eta, confidence = await self.pred_svc.get_prediction(
                route_id=data.route_id,
                target_stop_id=data.start_stop_id,
                planned_start_time=planned,
                now=datetime.now(UTC)
            )
        except Exception as e:
            logger.error(f"Initial prediction failed: {e}")

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
            official_start_time=planned,
            predicted_arrival=eta,
            confidence=confidence
        )
       
        await self.journey_repo.AddJourney(journey)

        try:
            snapshot = PredictionSnapshot(
                id=str(uuid4()),
                journey_id=journey_id,
                service_id=journey.service_id,
                stop_id=data.start_stop_id,
                user_reported_arrival=datetime.now(timezone.utc),
                static_scheduled=planned,
                best_trusted_arrival=eta or planned,
                predicted_arrival=journey.predicted_arrival,
                confidence=confidence
            )
            await self.snapshot_repo.CreateSnapshot(snapshot)
        except Exception as e:
            logger.error(f"Initial snapshot failed: {e}")

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