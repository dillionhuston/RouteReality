from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy.orm import Session

from app.models.StopArrivalAnchors import StopArrivalAnchors


class BestArrivalAnchorService:

    def update_or_create_anchor(
        db: Session,
        service_id: str,
        stop_id: str,
        best_time: datetime,
        confidence: float,
        source: str) -> StopArrivalAnchors:

        # Find existing anchor
        anchor = db.query(StopArrivalAnchors).filter(
            StopArrivalAnchors.service_id == service_id,
            StopArrivalAnchors.stop_id == stop_id
        ).first()

        now = datetime.now(timezone.utc)

        if anchor:
            if anchor.updated_at.tzinfo is None:
                anchor.updated_at = anchor.updated_at.replace(tzinfo=timezone.utc)

            if now - anchor.updated_at < timedelta(minutes=120):

                # Fresh anchor,  overwrite with new report
                anchor.best_arrival_time = best_time
                anchor.confidence = confidence
                anchor.report_count += 1
            else:
                # Stale anchor,  only update if better confidence
                if confidence > anchor.confidence:
                    anchor.best_arrival_time = best_time
                    anchor.confidence = confidence
                anchor.report_count += 1

            anchor.last_reported_at = now
            anchor.updated_at = now

        else:
            # Create new anchor
            anchor = StopArrivalAnchors(
                id=str(uuid4()),
                service_id=service_id,
                stop_id=stop_id,
                best_arrival_time=best_time,
                source=source,
                confidence=confidence,
                report_count=1,
                last_reported_at=now,
                updated_at=now
            )
            db.add(anchor)

        db.commit()
        return anchor

    def get_latest_anchor(
        db: Session,
        route_id: str,
        stop_id: str) -> StopArrivalAnchors | None:

        anchor = (
            db.query(StopArrivalAnchors)
            .filter(
                StopArrivalAnchors.route_id == route_id,
                StopArrivalAnchors.stop_id == stop_id
            )
            .order_by(StopArrivalAnchors.updated_at.desc())
            .first()
        )

        if anchor:
            if anchor.updated_at.tzinfo is None:
                anchor.updated_at = anchor.updated_at.replace(tzinfo=timezone.utc)

            if (datetime.now(timezone.utc) - anchor.updated_at) < timedelta(minutes=120):
                return anchor

        return None