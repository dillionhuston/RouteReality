from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.Database import get_db
from app.dependencies.get_current_user import get_current_user_optional
from app.models.Route import Route, RouteStop
from app.models.StopArrivalAnchors import StopArrivalAnchors
from typing import List, Optional
from app.models.User import User
from app.schemas.route import RouteAtStop

import random

router = APIRouter(prefix="/stops", tags=["stops"])

@router.get("/{stop_id}/routes", response_model=List[RouteAtStop])
def get_routes_for_stop(
    stop_id: str, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)):  # Optional auth
    """
    Return list of route IDs and route numbers that serve this stop. """
    route_stops = db.query(RouteStop).filter(RouteStop.stop_id == stop_id).all()
    if not route_stops:
        raise HTTPException(404, "No routes serve this stop")
    
    result = []
    for rs in route_stops:
        route = db.query(Route).filter(Route.id == rs.route_id).first()
        if route:
            result.append(RouteAtStop(
                route_id=route.id,
                route_number=route.name,
                direction=rs.direction
            ))
    
    return result

@router.get("/{stop_id}/arrivals")
def get_arrivals_for_stop(stop_id: str, db: Session = Depends(get_db)):
    """Return all current arrivals for provided stopId"""
    route_stops = db.query(RouteStop).filter(RouteStop.stop_id == stop_id).all()
    if not route_stops:
        raise HTTPException(404, "No routes serve this stop")

    now = datetime.now(timezone.utc)
    arrivals = []

    for rs in route_stops:
        route = db.query(Route).filter(Route.id == rs.route_id).first()
        if not route:
            continue

        # Get last stop (destination)
        stops_in_order = (
            db.query(RouteStop)
            .filter(RouteStop.route_id == route.id)
            .order_by(RouteStop.sequence)
            .all()
        )
        destination = stops_in_order[-1].stop.name if stops_in_order else route.name

        # 1. Find the soonest future anchor for this route at this stop
        future_anchor = (
            db.query(StopArrivalAnchors)
            .filter(
                StopArrivalAnchors.stop_id == stop_id,
                StopArrivalAnchors.route_id == route.id,
                StopArrivalAnchors.best_arrival_time > now,
            )
            .order_by(StopArrivalAnchors.best_arrival_time.asc())
            .first()
        )

        if future_anchor:
            eta = future_anchor.best_arrival_time
            confidence = future_anchor.confidence
            source = "live_data"
        else:
            # 2. No future anchor, revert to synthetic fallback
            mins = random.randint(1, 30)
            eta = now + timedelta(minutes=mins)
            confidence = 0.3
            source = "synthetic_fallback"

        arrivals.append({
            "route_number": route.name,
            "destination": destination,
            "predicted_eta": eta.isoformat(),
            "status": "on_time",
            "confidence": round(confidence, 2),
            "delay_minutes": round((eta - now).total_seconds() / 60, 1),
            "source": source,
            "route_id": route.id,
        })

    arrivals.sort(key=lambda x: x["predicted_eta"])
    return {
        "stop_id": stop_id,
        "timestamp": now.isoformat(),
        "arrivals": arrivals[:15],
    }