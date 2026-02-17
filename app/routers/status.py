from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.models.Journey import Journey
from app.models.Route import Route, RouteStop
from app.models.Database import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/journeys", tags=["Journeys"])

ACTIVE_STATUSES = ["on_route", "delayed", "departed", "in_progress", "en_route"]


def minutes_left(pred: Optional[str]) -> Optional[int]:
    """Return minutes remaining until predicted arrival, or None if invalid or too old."""
    if not pred:
        return None
    try:
        dt = datetime.fromisoformat(pred.replace("Z", "+00:00"))
        delta = dt - datetime.now(timezone.utc)
        mins = int(delta.total_seconds() // 60)
        # Only show future arrivals or up to 1 hour in the past
        return max(mins, 0) if mins > -60 else None
    except Exception:
        return None


@router.get("/status/stop/{stop_id}")
def journeys_for_stop(
    stop_id: str,
    db: Session = Depends(get_db),
    hours: int = Query(24, ge=1, le=168, description="Look back hours")
):
    """Return trips that passed through a stop recently + quick summary."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Total journeys that used this stop in timeframe
    total = (
        db.query(func.count(func.distinct(Journey.id)))
        .join(RouteStop, Journey.route_id == RouteStop.route_id)
        .filter(RouteStop.stop_id == stop_id)
        .filter(Journey.created_at >= cutoff)
        .scalar() or 0
    )

    # Active journeys (latest status is in ACTIVE_STATUSES)
    active = (
        db.query(func.count(func.distinct(Journey.id)))
        .join(RouteStop, Journey.route_id == RouteStop.route_id)
        .filter(RouteStop.stop_id == stop_id)
        .filter(Journey.created_at >= cutoff)
        .filter(Journey.status.in_(ACTIVE_STATUSES))
        .scalar() or 0
    )

    return {
        "stop_id": stop_id,
        "hours_back": hours,
        "total_trips": total,
        "active_trips": active,
        "message": f"{total} trips used this stop in last {hours}h ({active} active)"
    }


@router.get("/status/{route_id}")
def single_route(route_id: str, db: Session = Depends(get_db)):
    """Quick status for a single route."""
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(404, f"Route '{route_id}' not found")

    latest_j = (
        db.query(Journey)
        .filter(Journey.route_id == route_id)
        .order_by(desc(Journey.created_at))
        .first()
    )

    # Count journeys today
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total_today = db.query(Journey).filter(
        Journey.route_id == route_id,
        Journey.created_at >= start_of_day
    ).count()

    return {
        "route_id": route_id,
        "route_name": route.name or route_id,
        "current_status": latest_j.status if latest_j else None,
        "minutes_remaining": minutes_left(latest_j.predicted_arrival) if latest_j else None,
        "last_seen": latest_j.created_at.isoformat() if latest_j else None,
        "total_journeys_today": total_today
    }
