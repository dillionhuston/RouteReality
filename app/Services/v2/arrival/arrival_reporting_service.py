from datetime import datetime, timezone, time
from typing import Tuple

from sqlalchemy.orm import Session

from app.models.Journey import Journey
from app.utils.fetch_time import get_closest_scheduled_time_to_now
from app.Services.v2.anchor.best_arrival_anchor_service import BestArrivalAnchorService
from app.Services.v2.snapshot.snapshot import SnapshotService
from app.routers.Broadcast import broadcast_service_update
from app.repositories.journey_repository import JourneyRepository
from app.repositories.snapshot_repository import SnapshotRepository
from app.exceptions.exceptions import (
    JourneyNotFoundError,
    ServiceError,
    DatabaseError,
    AnchorUpdateError,
)


class ArrivalReportingService:
    """
    Handles user-reported arrivals:
    - Decides best arrival time (report vs timetable)
    - Updates shared anchor
    - Saves prediction snapshot
    - Writes predicted_arrival + confidence back to journey
    - Broadcasts update to connected clients

    status transitions are the sole responsible in JourneyEventHandler.
    """

    def __init__(self, journey_repo: JourneyRepository, snapshot_repo: SnapshotRepository):
        self.journey_repo = journey_repo
        self.snapshot_repo = snapshot_repo
        self.snapshot_service = SnapshotService(snapshot_repo)

    @staticmethod
    def _decide_best_time(
        reported_time: datetime,
        static_datetime: datetime | None,
    ) -> Tuple[datetime, float, str]:

        if static_datetime is None:
            return reported_time, 0.70, "No static timetable data"

        delay_minutes = (reported_time - static_datetime).total_seconds() / 60.0

        if abs(delay_minutes) <= 12:
            return reported_time, 0.85, "Within 12 min tolerance"

        if abs(delay_minutes) <= 25:
            return reported_time, 0.65, "Moderate deviation (13-25 min)"

        return static_datetime, 0.40, "Large deviation — using timetable"

    async def handle_arrival_report(
        self,
        db: Session,
        journey_id: str,
        stop_id: str,
        reported_time: datetime,
    ) -> Journey:

        """
        Main entry point for arrival reporting.
        Records anchor + snapshot, writes prediction back to journey, broadcasts.
        Does not change journey.status.
        """
        # 1. Get journey via repository
        try:
            journey = await self.journey_repo.GetJourneyById(journey_id)
        except Exception as e:
            raise DatabaseError(detail=f"Failed to retrieve journey: {str(e)}")
        if not journey:
            raise JourneyNotFoundError(detail=f"Journey {journey_id} not found")

        # 2. Get closest scheduled time
        try:
            result = get_closest_scheduled_time_to_now(
                route_id=journey.route_id,
                stop_id=stop_id,
                reference_time=reported_time,
            )
        except Exception as e:
            raise ServiceError(detail=f"Failed to get scheduled time: {str(e)}")
        static_timetable = result[0] if result else None

        # 3. Convert timetable time 
        static_datetime = None
        if static_timetable:
            static_datetime = datetime.combine(
                reported_time.date(),
                static_timetable,
                tzinfo=timezone.utc,
            )

        # 4. Decide best time
        best_time, confidence, reason = self._decide_best_time(
            reported_time=reported_time,
            static_datetime=static_datetime,
        )

        # 5. Make datetime
        if isinstance(best_time, time):
            best_datetime = datetime.combine(
                reported_time.date(),
                best_time,
                tzinfo=timezone.utc,
            )
        else:
            best_datetime = best_time

        # 6. Update/create shared anchor
        anchor_service = BestArrivalAnchorService()
        try:
            anchor = await anchor_service.update_or_create_anchor(
                service_id=journey.service_id,
                stop_id=stop_id,
                best_time=best_datetime,
                confidence=confidence,
                source="user_report",
            )
        except Exception as e:
            raise AnchorUpdateError(detail=f"Failed to update arrival anchor: {str(e)}")

        # 7. Save prediction snapshot via service
        try:
            await self.snapshot_service.create_snapshot(
                journey_id=journey.id,
                service_id=journey.service_id,
                stop_id=stop_id,
                user_reported_arrival=reported_time,
                static_scheduled=static_datetime,
                best_trusted_arrival=best_datetime,
                predicted_arrival=best_datetime,
                confidence=confidence,
            )
        except Exception as e:
            raise DatabaseError(detail=f"Failed to save prediction snapshot: {str(e)}")

        # 8. Update journey via repository
        journey.predicted_arrival = best_datetime
        journey.confidence = confidence
        try:
            await self.journey_repo.UpdateJourney(journey)
        except Exception as e:
            raise DatabaseError(detail=f"Failed to update journey with new prediction: {str(e)}")

        # 9. Broadcast update
        try:
            await broadcast_service_update(
                journey.service_id,
                {
                    "type":              "arrival_update",
                    "journey_id":        journey.id,
                    "stop_id":           stop_id,
                    "predicted_arrival": best_datetime.isoformat(),
                    "confidence":        confidence,
                    "report_count":      anchor.report_count,
                    "timestamp":         datetime.now(timezone.utc).isoformat(),
                    "status":            journey.status,
                },
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Broadcast failed: {e}")

        return journey