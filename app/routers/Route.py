from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload

from app.models.Database import get_db
from app.models.Route import Route, Stop, RouteStop

from app.schemas.route import StopsPerRoute, RouteOut

from app.utils.logger import logger

router = APIRouter(prefix="/route", tags=["Routes"])


@router.get("/routes", response_model=List[RouteOut])
def get_routes(db: Session = Depends(get_db)):
    """
    Quick list of all routes + first stop lat/lon for dropdown + map pins
    """
    routes = (
        db.query(Route)
        .options(joinedload(Route.route_stops).joinedload(RouteStop.stop))
        .order_by(Route.name)
        .all()
    )

    if not routes:
        logger.warning("No routes in db wtf")
        raise HTTPException(404, "No routes available")

    result = []

    for r in routes:
        lat = None
        lon = None

        if r.route_stops:
            # get first stop by sequence
            first = min(r.route_stops, key=lambda rs: rs.sequence)
            if first and first.stop:
                lat = first.stop.latitude
                lon = first.stop.longitude

        result.append(RouteOut(
            id=r.id,
            name=r.name,
            first_stop_lat=lat,
            first_stop_lon=lon
        ))
    return result


@router.get("/{route_id}/stops", response_model=List[StopsPerRoute])
def get_stops_per_route(route_id: str, db: Session = Depends(get_db)):
    """Get all ordered stops for a route + lat/lon"""
    stops = (
        db.query(RouteStop)
        .options(joinedload(RouteStop.stop))
        .filter(RouteStop.route_id == route_id)
        .order_by(RouteStop.sequence)
        .all()
    )

    if not stops:
        raise HTTPException(404, f"No stops for route '{route_id}'")
    
    result = []
    seen_seq = set()

    for rs in stops:
        if not rs.stop:
            logger.warning(f"Missing stop object - {rs.stop_id}")
            continue
            
        name = (rs.stop.name or "???").strip()
        
        if not name or name == "Unknown Stop":
            print(f"Skipping bad stop {rs.stop_id} name='{name}'")
            continue
        
        if rs.sequence in seen_seq:
            print(f"Duplicate seq {rs.sequence} on {route_id} - keeping anyway")
        seen_seq.add(rs.sequence)
        
        result.append(StopsPerRoute(
            id=rs.stop_id,
            name=name,
            sequence=rs.sequence,
            direction=rs.direction or "N/A",
            latitude=rs.stop.latitude,     # for frotend 
            longitude=rs.stop.longitude    # for frontend
        ))
    
    print(f"Route {route_id} - {len(result)} valid stops")
    return result   