from typing import List, Dict
from datetime import datetime, timezone, timedelta, time

from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.models.Journey import Journey
from app.models.Route import RouteStop
from app.utils.fetch_time import fetch_scheduled_time
from app.utils.logger.logger import get_logger

logger = get_logger(__name__)


def _to_utc(dt: datetime) -> datetime:
    """Ensure timestamp is UTC-aware"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_recent_user_events(
    db: Session,
    route_id: str,
    stop_id: str,
    limit: int = 10,) -> List[Dict]:
    """
    Grab recent user events (ARRIVED/DELAYED) for the last N minutes.
    Also tacks on the scheduled time if we can find it.
    """
    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(minutes=40)

    stmt = (
        select(Journey)
        .join(RouteStop, Journey.route_id == RouteStop.route_id)
        .where(
            Journey.route_id == route_id,
            RouteStop.stop_id == stop_id,
            Journey.created_at >= cutoff,
        )
        .order_by(desc(Journey.created_at))
        .limit(limit)
    )

    journeys = db.execute(stmt).scalars().all()
    events = []

    for journey in journeys:
        if journey.planned_start_time is None and journey.created_at is None:
            continue

        arrival_time = _to_utc(journey.planned_start_time or journey.created_at)

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

    # Add scheduled time fallback
    scheduled = fetch_scheduled_time(route_id, stop_id)
    if scheduled:
        if isinstance(scheduled, datetime):
            scheduled_utc = _to_utc(scheduled)
        elif isinstance(scheduled, time):
            scheduled_utc = scheduled  # time-of-day — caller can handle date
        else:
            scheduled_utc = None

        events.append({
            "type": "SCHEDULED",
            "time": scheduled_utc,
            "source": "official_timetable",
        })
    else:
        events.append({
            "type": "SCHEDULED",
            "time": None,
            "source": "no_timetable",
        })

    return events


def get_user_journeys(
    db: Session,
    route_id: str,
    stop_id: str,
    limit: int = 10,) -> List[datetime]:
    """
    Get arrival times from recent completed user journeys at this stop.
    """
    now = datetime.now(timezone.utc)

    stmt = (
        select(Journey)
        .join(RouteStop, Journey.route_id == RouteStop.route_id)
        .where(
            Journey.route_id == route_id,
            RouteStop.stop_id == stop_id,
            Journey.status == "ARRIVED",
            Journey.created_at <= now,
        )
        .order_by(desc(Journey.created_at))
        .limit(limit)
    )

    journeys = db.execute(stmt).scalars().all()
    arrivals = []

    for j in journeys:
        if j.planned_start_time is None and j.created_at is None:
            continue

        arrival_time = _to_utc(j.planned_start_time or j.created_at)
        arrivals.append(arrival_time)

    return arrivals