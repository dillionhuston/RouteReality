from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.models.Journey import Journey
from app.models.Route import Route, RouteStop, Stop
from app.core.Database import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/journeys", tags=["Journeys"])


ACTIVE_STATUSES = ["on_route", "delayed", "departed", "in_progress", "en_route"] #todo make schema for this


def minutes_left(pred: Optional[str]) -> Optional[int]:
    """Return minutes remaining until predicted arrival, or None if invalid or too old."""
    if not pred:
        return None
    try:
        dt = datetime.fromisoformat(pred.replace("Z", "+00:00"))
        delta = dt - datetime.now(timezone.utc)
        mins = int(delta.total_seconds() // 60)
        return max(mins, 0) if mins > -60 else None
    except Exception:
        return None

@router.get("/status/journey/{journey_id}")
def journey_status(
    journey_id: str,
    db: Session = Depends(get_db)):

    """Get status for a specific journey by its ID."""
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    
    if not journey:
        raise HTTPException(404, f"Journey {journey_id} not found")
    
    route = db.query(Route).filter(Route.id == journey.route_id).first()
    
    # Get destination stop
    destination = None
    if journey.end_stop_id:
        dest_stop = db.query(Stop).filter(Stop.id == journey.end_stop_id).first()
        if dest_stop:
            destination = dest_stop.name
    
    # Calculate minutes remaining from predicted arrival
    minutes_remaining = None
    if journey.predicted_arrival:
        delta = journey.predicted_arrival - datetime.now(timezone.utc)
        minutes_remaining = max(0, int(delta.total_seconds() / 60))
    
    return {
        "journey_id": journey.id,
        "service_id": journey.service_id,
        "route_id": journey.route_id,
        "route_number": route.name if route else journey.route_id,
        "destination": destination,
        "status": journey.status,
        "predicted_arrival": journey.predicted_arrival.isoformat() if journey.predicted_arrival else None,
        "minutes_remaining": minutes_remaining,
        "start_stop_id": journey.start_stop_id,
        "end_stop_id": journey.end_stop_id,
        "created_at": journey.created_at.isoformat(),
        "confidence": journey.confidence
    }

@router.get("/status/stop/{stop_id}")
def journeys_for_stop(
    stop_id: str,
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500, description="Max number of trips"),
    hours: int = Query(24, ge=1, le=168, description="Look back hours")):

    """Return trips that passed through a stop recently."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    journeys = (
        db.query(Journey)
        .join(RouteStop, Journey.route_id == RouteStop.route_id)
        .filter(RouteStop.stop_id == stop_id)
        .filter(Journey.created_at >= cutoff)
        .order_by(desc(Journey.created_at), Journey.id)
        .distinct(Journey.created_at, Journey.id)
        .limit(limit)
        .all()
    )
    
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
        "returned_trips": len(journeys),
        "trips": [
            {
                "id": j.id,
                "route_id": j.route_id,
                "status": j.status,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "predicted_arrival": j.predicted_arrival,
                "minutes_remaining": minutes_left(j.predicted_arrival)
            }
            for j in journeys 
        ]
    }
        

@router.get("/status/{route_id}")
def single_route(
    route_id: str,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Max number of trips")):

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

    recent_journeys = (
        db.query(Journey)
        .filter(Journey.route_id == route_id)
        .order_by(desc(Journey.created_at))
        .limit(limit)
        .all()
    )

    return {
        "route_id": route_id,
        "route_name": route.name or route_id,
        "current_status": latest_j.status if latest_j else None,
        "predicted_arrival": latest_j.predicted_arrival,
        "minutes_remaining": minutes_left(latest_j.predicted_arrival) if latest_j else None,
        "updated_user_submitted": latest_j.created_at.isoformat() if latest_j else None,
        "total_journeys_today": total_today,
        "recent_trips": [
            {
                "id": j.id,
                "status": j.status,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "minutes_remaining": minutes_left(j.predicted_arrival)
            }
            for j in recent_journeys
        ]
    }


@router.get("/active")
def get_active_journeys(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=50)):
    """
    Get all currently active journeys (in progress, delayed, arrived)"""
    #todo, change to schema also
    active_statuses = ["STARTED", "ON_BUS", "ARRIVED", "DELAYED", "en_route", "on_route"]
    
    journeys = (
        db.query(Journey)
        .filter(Journey.status.in_(active_statuses))
        .filter(Journey.ended_at.is_(None))
        .order_by(desc(Journey.created_at))
        .limit(limit)
        .all()
    )
    
    result = []
    for j in journeys:
        route = db.query(Route).filter(Route.id == j.route_id).first()
        start_stop = db.query(Stop).filter(Stop.id == j.start_stop_id).first()
        
        # Calculate minutes remaining
        minutes_remaining = None
        if j.predicted_arrival:
            if isinstance(j.predicted_arrival, datetime):
                delta = j.predicted_arrival - datetime.now(timezone.utc)
                minutes_remaining = max(0, int(delta.total_seconds() / 60))
        
        result.append({
            "journey_id": j.id,
            "route_number": route.name if route else j.route_id,
            "status": j.status,
            "start_stop": start_stop.name if start_stop else "Unknown",
            "minutes_remaining": minutes_remaining,
            "created_at": j.created_at.isoformat()
        })
    
    return result