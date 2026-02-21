# services/prediction/data.py
# pulls user events, past arrivals and scheduled time
# feeds into the prediction logic

from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta, time

from fastapi import Depends

from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.models.Journey import Journey
from app.utils.fetch_time import fetch_scheduled_time  # CIF fallback

#Checks timestamp  making sure it UTC 
def _to_utc(dt:datetime) -> datetime:
    if dt.tzinfo is None:
        #treat naice datetime as utc
        return dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(timezone.utc)


def get_recent_user_events(
    db: Session,
    route_id: str,
    stop_id: str,
    last_minutes: int = 15) -> List[Dict]: 
    """
    Grab recent user events (ARRIVED/DELAYED) for the last N minutes.
    Also tacks on the scheduled time if we can find it.
    """

    cutoff = datetime.now(tz=timezone.utc) - timedelta(minutes=last_minutes)

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
        if journey.start_time is None and journey.created_at is None:
            raise ValueError(f"Journey {journey.id} has no timestamp")

        arrival_time = _to_utc(journey.start_time or journey.created_at)

        if journey.status == "ARRIVED":
            events.append({
                "type": "ARRIVED",
                "time": arrival_time,
            })

        elif journey.status == "DELAYED":
            events.append({
                "type": "DELAYED",
                "time": arrival_time,
            })

    scheduled = fetch_scheduled_time(route_id, stop_id)

    if scheduled:
    # scheduled can be datetime (normalize to UTC) or time (used directly in adjust_timetable_time)
        if isinstance(scheduled, datetime):
            scheduled_utc = _to_utc(scheduled)
        elif isinstance(scheduled, time):
            scheduled_utc = scheduled
        else:
            scheduled_utc = None

        events.append({
            "type": "SCHEDULED",
            "time": scheduled_utc,
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
    db: Session,
    route_id: str,
    stop_id: str,
    limit: int = 10,) -> List[datetime]:
    """
    Get arrival times from recent completed user journeys.
    Used for crowd-based average ETA.
    """

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
        if j.start_time is None and j.created_at is None:
            continue # skips corrupted rows

        arrival_time = _to_utc(j.start_time or j.created_at)
        arrivals.append(arrival_time)

    # print(f"Found {len(arrivals)} past arrivals for {route_id}/{stop_id}")
    return arrivals