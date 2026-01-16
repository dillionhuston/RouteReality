from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload

from app.models.Database import SessionLocal, engine, get_db
from app.models.BusRoute import Route
from app.models.Stop import Stop
from app.models.RouteStop import RouteStop
from app.schemas.route import StopsPerRoute
from app.schemas.route import RouteOut


router = APIRouter(prefix="/route", tags=["Route"])


# This is used for populating the drop down menu for the frontend
@router.get("/routes", response_model=List[RouteOut])
def get_routes(db: Session = Depends(get_db)):
    """Return a list of available  routes"""

    routes = db.query(Route).all()  
    if not routes:
        raise HTTPException(
            status_code=404,
            detail="Could not return a list of routes"
        )
    
    return [
        {
            "id": route.id,
            "name": route.name
        }
        for route in routes
    ]


@router.get("/routes/{route_id}/stops", response_model=List[StopsPerRoute])
def get_stops_per_route(route_id: str, db: Session = Depends(get_db)):
    """Return a list of stops using the provided route id"""

    route_stops = (
        db.query(RouteStop)
        .options(joinedload(RouteStop.stop))  # fetch all data upfront rather than lazy loading
        .filter(RouteStop.route_id == route_id)
        .order_by(RouteStop.sequence)
        .all()
    )

    # Add error checking to make sure the route exists in the datbase
    if not route_stops:
        raise HTTPException(
            status_code=404,
            detail="No stops found for this route"    
        )

    return [
        {
            "id": route_stops.id,
            "name": route_stops.id
        }
        for rs in route_stops
    ]
        
    
