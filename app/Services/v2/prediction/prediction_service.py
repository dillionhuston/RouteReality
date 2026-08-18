from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.prediction_repository import PredictionRepository
from app.repositories.event_repository import EventRepository
from app.repositories.journey_repository import JourneyRepository
from app.Services.Prediction.logic import predict_bus_time  # adjust import
from app.utils.logger.logger import get_logger


class PredictionService:

    def __init__(
        self,
        prediction_repo: PredictionRepository,
        event_repo: EventRepository,
        journey_repo: JourneyRepository,  
    ):
        self.prediction_repo = prediction_repo
        self.event_repo = event_repo
        self.journey_repo = journey_repo
        self.logger = get_logger(__name__)

    @staticmethod
    def toutc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    async def get_recent_user_events(
        self,
        route_id: str,
        stop_id: str,
        limit: int = 10,
        cutoff_minutes: int = 40):
        """
        Fetch recent user events (ARRIVED/DELAYED) via EventRepository.
        """
        events = await self.event_repo.GetRecentEventsByRouteAndStop(
            route_id=route_id,
            stop_id=stop_id,
            limit=limit,
            cutoff_minutes=cutoff_minutes,
        )

        result = []
        for ev in events:
            arrival_time = self.toutc(ev.reported_time or ev.created_at)
            result.append({"type": ev.type, "time": arrival_time})


        return result

    async def get_prediction(
        self,
        route_id: str,
        target_stop_id: str,
        planned_start_time: datetime,
        now: Optional[datetime] = None,) -> tuple[Optional[datetime], float]:
        """
        Predict arrival time + confidence.
        Priority: fresh anchor historical hour, delay, user events and timetable.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # 1. Fresh anchor (from prediction_repo)
        anchor = await self.prediction_repo.GetLatestAnchor(route_id, target_stop_id)
        used_anchor = False
        used_historical = False
        base_time = planned_start_time

        if anchor and (now - anchor.updated_at < timedelta(minutes=60)):
            base_time = anchor.best_arrival_time
            used_anchor = True
            confidence = anchor.confidence or 0.80
            # We can return early with high confidence
            return base_time, min(0.98, confidence)

        # 2. Historical fallback 
        hist_delay = await self.prediction_repo.GetHistoricalDelay(
            route_id, target_stop_id, base_time
        )
        if hist_delay is not None:
            base_time += timedelta(minutes=hist_delay)
            used_historical = True

        # 3. Get recent user events 
        recent_events = await self.get_recent_user_events(
            route_id=route_id,
            stop_id=target_stop_id,
            limit=10,
        )

        # 4. Get past arrivals
        past_arrivals = await self.journey_repo.GetRecentArrivedJourneys(
            route_id=route_id,
            stop_id=target_stop_id,
            limit=10,
            now=now
        )

        # 5. Use the core prediction 
        static_time = base_time.time() if isinstance(base_time, datetime) else base_time
        try:
            predicted_time, confidence = predict_bus_time(
                static_time=static_time,
                user_events=recent_events,
                past_arrivals=past_arrivals,
                now=now,
            )
        except Exception as e:
            self.logger.error(f"predict_bus_time failed: {e}", exc_info=True)
            predicted_time = base_time or (now + timedelta(minutes=15))
            confidence = 0.15

        # 6. Adjust for recent delays
        delays = sum(1 for e in recent_events if e["type"] == "DELAYED")
        if delays >= 1:
            extra_min = 4 + delays * 3.5
            predicted_time += timedelta(minutes=extra_min)
            confidence = min(0.95, confidence + 0.15)

        # 7. Boost confidence if we used anchor/historical
        if used_anchor:
            confidence = min(1.0, confidence + 0.15)
        elif used_historical:
            confidence = min(0.85, confidence + 0.05)

        confidence = max(0.25, min(0.98, confidence))

        #never predict past
        if predicted_time < now:
            predicted_time = now + timedelta(minutes=3)

        return predicted_time, round(confidence, 2)