from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload

from app.core.Database import get_db
from app.models.Route import Route, RouteStop
from app.schemas.route import StopsPerRoute, RouteOut
from app.utils.logger import logger

from app.dependencies.get_current_user import get_current_user, get_current_user_optional
from app.models.User import User

router = APIRouter(prefix="/route", tags=["Routes"])
logger = logger.get_logger()


@router.get("/routes",response_model=List[RouteOut])
def get_routes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)):
    """
    Returns all routes with first stop lat/lon for dropdowns or maps
    """

    routes = db.query(Route).options(
        joinedload(Route.route_stops).joinedload(RouteStop.stop)
    ).order_by(Route.name).all()

    if not routes:
        logger.warning("No routes in database")
        raise HTTPException(404, "No routes available")

    result = []
    for r in routes:
        lat = lon = None
        if r.route_stops:
            first = min(r.route_stops, key=lambda rs: rs.sequence)
            if first.stop:
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
def get_stops_per_route(
    route_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)):

    """Get all stops for a route, ordered by sequence.
       Skips stops without proper name or missing stop object
     """
    
    stops = db.query(RouteStop).options(
        joinedload(RouteStop.stop)
    ).filter(RouteStop.route_id == route_id).order_by(RouteStop.sequence).all()

    if not stops:
        raise HTTPException(404, f"No stops for route '{route_id}'")

    result = []
    seen_seq = set()
    for rs in stops:
        if not rs.stop:
            logger.warning(f"Missing stop object: {rs.stop_id}")
            continue

        name = (rs.stop.name or "???").strip()
        if not name or name == "Unknown Stop":
            logger.info(f"Skipping bad stop {rs.stop_id} name='{name}'")
            continue

        if rs.sequence in seen_seq:
            logger.info(f"Duplicate sequence {rs.sequence} on route {route_id} - keeping anyway")
        seen_seq.add(rs.sequence)

        result.append(StopsPerRoute(
            id=rs.stop_id,
            name=name,
            sequence=rs.sequence,
            direction=rs.direction or "N/A",
            latitude=rs.stop.latitude,
            longitude=rs.stop.longitude
        ))

    logger.info(f"Route {route_id} has {len(result)} valid stops")
    return result