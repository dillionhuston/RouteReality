# app/routers/journey_status.py

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.models.Journey import Journey
from app.models.Route import Route, RouteStop
from app.models.Database import get_db

router = APIRouter(prefix="/journeys", tags=["Journeys"])

ACTIVE_STATUSES = ["on_route", "delayed", "departed", "in_progress", "en_route"]


def minutes_left(pred: Optional[str]) -> Optional[int]:
    if not pred:
        return None
    try:
        dt = datetime.fromisoformat(pred.replace("Z", "+00:00"))
        delta = dt - datetime.now(timezone.utc)
        mins = int(delta.total_seconds() // 60)
        return max(mins, 0) if mins > -60 else None  # don't show old arrivals
    except:
        return None


@router.get("/status/stop/{stop_id}")
def journeys_for_stop(
    stop_id: str,
    db: Session = Depends(get_db),
    hours: Optional[int] = Query(24, ge=1, le=168, description="look back hours")
):
    """How many trips/journeys passed through this stop recently + quick summary"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Total journeys that used this stop
    total = (
        db.query(func.count(func.distinct(Journey.id)))
        .join(RouteStop, Journey.route_id == RouteStop.route_id)
        .filter(RouteStop.stop_id == stop_id)
        .filter(Journey.created_at >= cutoff)
        .scalar() or 0
    )

    # Active ones (latest status is active)
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

# Single route quick check
@router.get("/status/{route_id}")
def single_route(route_id: str, db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(404, "Route not found")

    latest_j = (
        db.query(Journey)
        .filter(Journey.route_id == route_id)
        .order_by(desc(Journey.created_at))
        .first()
    )

    return {
        "route_id": route_id,
        "route_name": route.name or route_id,
        "current_status": latest_j.status if latest_j else None,
        "minutes_remaining": minutes_left(latest_j.predicted_arrival) if latest_j else None,
        "last_seen": latest_j.created_at.isoformat() if latest_j else None,
        "total_journeys_today": db.query(Journey)
            .filter(
                Journey.route_id == route_id,
                Journey.created_at >= datetime.now(timezone.utc).date()
            )
            .count()
    }