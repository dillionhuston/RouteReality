from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.Services.v2.anchor.best_arrival_anchor_service import BestArrivalAnchorService
from app.Services.Prediction.service import get_prediction 
from app.utils.historical import get_historical_delay


class PredictionService:
    def get_prediction(
        self, 
        db: Session,
        route_id: str,
        target_stop_id: str,
        planned_start_time: datetime,
        now: datetime = None) -> tuple[datetime | None, float]:
        """
        Predict arrival time + confidence.
        Priority: fresh anchor → historical hour delay → timetable.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # 1. Fresh anchor
        anchor = BestArrivalAnchorService.get_latest_anchor(
            db=db,
            route_id=route_id,
            stop_id=target_stop_id
        )

        used_anchor = False
        used_historical = False
        base_time = planned_start_time

        if anchor and (now - anchor.updated_at < timedelta(minutes=60)):
            base_time = anchor.best_arrival_time
            used_anchor = True

        else:
            # 2. Historical fallback
            hist_delay = get_historical_delay(
                db=db,
                route_id=route_id,
                stop_id=target_stop_id,
                dt=now
            )
            if hist_delay is not None:
                base_time += timedelta(minutes=hist_delay)
                used_historical = True

        # 3. Old prediction logic
        result = get_prediction(
            db=db,
            route_id=route_id,
            stop_id=target_stop_id,
        static_dt=base_time.time() if isinstance(base_time, datetime) else base_time,    )

        eta_str = result.get("predicted_arrival")
        eta = datetime.fromisoformat(eta_str) if eta_str else None
        confidence = result.get("confidence", 0.40)

        # Boost confidence
        if used_anchor:
            confidence = min(1.0, confidence + 0.15)
        elif used_historical:
            confidence = min(0.85, confidence + 0.05)

        confidence = max(0.25, min(0.98, confidence))

        return eta, confidence