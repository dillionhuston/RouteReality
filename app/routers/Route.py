from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload

# db stuff
from app.models.Database import SessionLocal, engine, get_db
from app.models.Route import Route, Stop, RouteStop

from app.schemas.route import StopsPerRoute, RouteOut

from app.utils.logger import logger  # hope this is the right one...



logger = logger.get_logger()  # wait this was dumb af, fix later
# actually just using the imported logger for now

router = APIRouter(prefix="/route", tags=["Route"])


@router.get("/routes", response_model=List[RouteOut])
def get_routes(db: Session = Depends(get_db)):
    """Quick list of all routes for the frontend dropdown"""

    routes = db.query(Route).all()
    if not routes:
        logger.error("No routes at all in the db - wtf")
        raise HTTPException(
            status_code=404,
            detail="Could not return a list of routes"  
        )
    
    # keeping it simple stupid
    return [
        {"id": r.id, "name": r.name}
        for r in routes
    ]


@router.get("/routes/{route_id}/stops", response_model=List[StopsPerRoute])
def get_stops_per_route(route_id: str, db: Session = Depends(get_db)):
    """Get ordered stops for a route - with some basic data cleanup"""
    
    route_stops = (
        db.query(RouteStop)
        .options(joinedload(RouteStop.stop))
        .filter(RouteStop.route_id == route_id)
        .order_by(RouteStop.sequence)
        .all()
    )
    
    if not route_stops:
        logger.info(f"No stops found for {route_id} - maybe bad route id?")
        raise HTTPException(404, f"No stops found for route '{route_id}'")
    
    result = []
    seen_sequences = set()   # trying to catch the duplicate seq bug
    
    for rs in route_stops:
        if not rs.stop:
            logger.warning(f"RouteStop missing stop object - id {rs.stop_id}")
            continue
            
        stop_name = rs.stop.name if rs.stop.name else "???"
        
        if stop_name.strip() == "" or stop_name == "Unknown Stop":
            logger.warning(f"Skipping dodgy stop {rs.stop_id} - name: '{stop_name}'")
            continue
        
        # duplicate seq check (yes this happens in prod data)
        if rs.sequence in seen_sequences:
            logger.warning(f"Duplicate sequence {rs.sequence} for route {route_id} - keeping anyway")
        seen_sequences.add(rs.sequence)
        
        stop_data = {
            "id": rs.stop_id,
            "name": stop_name.strip(),  # just to be safe
            "sequence": rs.sequence,
            "direction": rs.direction if rs.direction else "N/A"
        }
        
        result.append(stop_data)
    
    # bit of debug spam, remove later?
    logger.warning(f"[DEBUG] Route {route_id} - kept {len(result)} valid stops out of {len(route_stops)}")
    
    return result