# services/prediction/data.py
# pulls user events, past arrivals and scheduled time
# feeds into the prediction logic

from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.models.Journey import Journey
from app.utils.fetch_time import fetch_scheduled_time  # CIF fallback



def get_db_session() -> Session:
    """Quick session helper - replace with proper FastAPI Depends in API"""
    return Session()


def get_recent_user_events(
    route_id: str,
    stop_id: str,
    last_minutes: int = 15,
    db: Session = None) -> List[Dict]: 
    """
    Grab recent user events (ARRIVED/DELAYED) for the last N minutes.
    Also tacks on the scheduled time if we can find it.
    """
    if db is None:
        db = get_db_session()

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=last_minutes)

    stmt = (
        select(Journey)
        .where(
            Journey.route_id == route_id,
            Journey.end_stop_id == stop_id,
            Journey.created_at >= cutoff
        )
        .order_by(desc(Journey.created_at))
        .limit(5)
    )

    journeys = db.execute(stmt).scalars().all()

    events = []

    for journey in journeys:
        if journey.status == "ARRIVED":
            events.append({
                "type": "ARRIVED",
                "time": journey.start_time or journey.created_at,
            })
        elif journey.status == "DELAYED":
            events.append({
                "type": "DELAYED",
                "time": journey.created_at,
            })

    # Try to add scheduled time (from CIF)
    scheduled = fetch_scheduled_time(route_id, stop_id)
    if scheduled:
        events.append({
            "type": "SCHEDULED",
            "time": scheduled.strftime("%H:%M"),
            "source": "official_timetable"
        })
    else:
        events.append({
            "type": "SCHEDULED",
            "time": None,
            "source": "no_timetable"
        })

    # print(f"Found {len(events)} events for {route_id} at {stop_id}")
    return events


def get_user_journeys(
    route_id: str,
    stop_id: str,
    limit: int = 10,
    db: Session = None) -> List[datetime]:
    """
    Get arrival times from recent completed user journeys.
    Used for crowd-based average ETA.
    """
    if db is None:
        db = get_db_session()

    now = datetime.now(timezone.utc)

    stmt = (
        select(Journey)
        .where(
            Journey.route_id == route_id,
            Journey.end_stop_id == stop_id,
            Journey.status == "ARRIVED",
            Journey.created_at <= now
        )
        .order_by(desc(Journey.created_at))
        .limit(limit)
    )

    journeys = db.execute(stmt).scalars().all()

    arrivals = []
    for j in journeys:
        arrival = j.start_time or j.created_at
        if arrival:  # just in case
            arrivals.append(arrival)

    # print(f"Found {len(arrivals)} past arrivals for {route_id}/{stop_id}")
    return arrivals