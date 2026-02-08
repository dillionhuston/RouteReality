# services/journey_service.py
# Handles starting journeys and finding active ones
# Still a bit scrappy but works in prod

from uuid import uuid4, UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from pathlib import Path

from app.models.Route import Route, Stop
from app.models.Journey import Journey
from app.schemas.journey import StartJourney, JourneyEventType

# Grab the timetable helper we actually have
from app.utils.fetch_time import get_closest_scheduled_time_to_now

from app.Services.Prediction.service import get_prediction


class JourneyService:
    """Service for creating and querying journeys."""

    @staticmethod
    def start_journey(data: StartJourney, db: Session) -> Journey:
        """Start off a new journey, try to get real timetable time, predict arrival based on recent journey data and events."""
        # fetch route
        route = db.query(Route).filter(Route.id == data.route_id).first()
        if not route:
            raise HTTPException(404, detail=f"Route {data.route_id} not found")

        # start stop
        start_stop = db.query(Stop).filter(Stop.id == data.start_stop_id).first()
        if not start_stop:
            raise HTTPException(404, detail=f"Start stop {data.start_stop_id} not found")

        # end stop (optional)
        end_stop = None
        if data.end_stop_id:
            end_stop = db.query(Stop).filter(Stop.id == data.end_stop_id).first()
            if not end_stop:
                raise HTTPException(404, detail=f"End stop {data.end_stop_id} not found")

        # starting point time. User input or now
        planned = data.planned_start_time or datetime.now(timezone.utc)
        if planned.tzinfo is None:
            planned = planned.replace(tzinfo=timezone.utc)

        official_start_str = planned.isoformat()

        # Try to get actual next bus time from CIF
        scheduled_time = None
        is_tomorrow = False
        minutes_until = None

        cif_path = Path("app/data/MPH_Metro_5_Jan_2026.cif")
        if cif_path.exists():
            # print("Found CIF - checking scheduled time...")
            scheduled_time, minutes_until, is_tomorrow = get_closest_scheduled_time_to_now(
                route_id=data.route_id,
                stop_id=data.start_stop_id,
                reference_time=planned,
            )

            if scheduled_time:
                sched_dt = datetime.combine(planned.date(), scheduled_time, tzinfo=timezone.utc)
                if is_tomorrow:
                    sched_dt += timedelta(days=1)

                if sched_dt > planned:
                    planned = sched_dt
                    official_start_str = planned.isoformat()
                    # print(f"Used timetable time instead: {planned.strftime('%H:%M')}")
                # else:
                #     print("Timetable time already passed, keeping user time")

        # Get prediction, pass what we have
        predicted_arrival, confidence = get_prediction(
            db=db,
            route_id=data.route_id,
            stop_id=data.end_stop_id,
            static_time=scheduled_time )

        # Add the journey
        journey = Journey(
            id=str(uuid4()),
            route_id=data.route_id,
            start_stop_id=data.start_stop_id,
            end_stop_id=data.end_stop_id,
            planned_start_time=planned,
            start_time=None,
            status=JourneyEventType.EVENT_TYPE_STARTED,
            created_at=datetime.now(timezone.utc),
            predicted_status="PENDING",  # will get updated later hopefully
            predicted_arrival=predicted_arrival,
            official_start_time=official_start_str,
            official_end_time=(
                route.official_timetable.get("end_time")
                if hasattr(route, "official_timetable") and route.official_timetable
                else None
            ),
        )

        db.add(journey)
        db.commit()
        db.refresh(journey)

        # print(f"New journey {journey.id} started - predicted at {predicted_arrival}")
        return journey

    @staticmethod
    def get_active_journey(journey_id: UUID, db: Session) -> Journey:
        """Find a journey that's still going (no end time)."""
        journey = (
            db.query(Journey)
            .filter(
                Journey.id == journey_id,
                Journey.status.in_([
                    JourneyEventType.EVENT_TYPE_STARTED,
                    JourneyEventType.EVENT_TYPE_DELAYED,
                    JourneyEventType.EVENT_TYPE_ARRIVED,
                ]),
                Journey.end_time.is_(None),
            )
            .one_or_none()
        )

        if journey is None:
            raise HTTPException(404, detail=f"No active journey found for {journey_id}")

        return journey