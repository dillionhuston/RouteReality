from uuid import UUID, uuid4
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.Route import Route
from app.models.Route import Stop 
from app.models.Journey import Journey
from app.schemas.journey import StartJourney, JourneyEventType

from app.Services.Prediction.prediction import PredictionService
#from app.utils.fetch_timetable_cif import get_official_timetable_for_route


class JourneyService:

    @staticmethod
    def start_journey(data: StartJourney, db: Session) -> Journey:
        route = db.query(Route).filter(Route.id == data.route_id).first()
        if not route:
            raise HTTPException(404, f"Route '{data.route_id}' not found")

        start_stop = db.query(Stop).filter(Stop.id == data.start_stop_id).first()
        if not start_stop:
            raise HTTPException(404, f"Start stop '{data.start_stop_id}' not found")

        end_stop = None
        if data.end_stop_id:
            end_stop = db.query(Stop).filter(Stop.id == data.end_stop_id).first()
            if not end_stop:
                raise HTTPException(404, f"End stop '{data.end_stop_id}' not found")

        planned = data.planned_start_time or datetime.now(timezone.utc)

        # Get official times. Fallback to empty string if None 
        official_start = route.official_timetable.get('start_time') if route.official_timetable else ""
        official_end   = route.official_timetable.get('end_time')   if route.official_timetable else ""

        predicted_arrival, predicted_status = PredictionService.predict_journey(
            db=db,
            route_id=data.route_id,
            start_time=datetime.now(timezone.utc)
        )

        journey = Journey(
            id=str(uuid4()),
            route_id=data.route_id,
            start_stop_id=data.start_stop_id,
            end_stop_id=data.end_stop_id,
            planned_start_time=planned,
            start_time=None,
            status=JourneyEventType.EVENT_TYPE_STARTED,
            created_at=datetime.now(timezone.utc),
            predicted_status=predicted_status,
            predicted_arrival=predicted_arrival.strftime("%Y-%m-%d %H:%M:%S") if predicted_arrival else "",
            official_start_time=official_start,   
            official_end_time=official_end,       
        )

        db.add(journey)
        db.commit()
        return journey

    @staticmethod
    def get_active_journey(journey_id: UUID, db: Session) -> Journey:
        """Retrieve an active (ongoing) journey by its internal UUID."""
        journey = (
            db.query(Journey)
            .filter(
                Journey.id == journey_id,           
                Journey.status.in_([
                    JourneyEventType.EVENT_TYPE_STARTED,
                    JourneyEventType.EVENT_TYPE_DELAYED,
                    JourneyEventType.EVENT_TYPE_ARRIVED
                ]),
                Journey.end_time.is_(None)
            )
            .one_or_none()
        )

        if journey is None:
            raise HTTPException(
                status_code=404,
                detail=f"Active journey not found for ID: {journey_id}"
            )

        return journey