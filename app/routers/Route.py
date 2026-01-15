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


# GET /route/routes - Retrieve all routes
# change shcema to routes again this is for testing, i will forget
@router.get("/routes", response_model=List[RouteOut])
def get_routes(db: Session = Depends(get_db)):

    route = db.query(Route).all()  
    return [
        {
            "id": route.id,
            "name": route.name
        }
        for stop in route
    ]


#GET /route/routes - Fetch all stops along a route using {route_id}
@router.get("/routes/{route_id}/stops", response_model=List[StopsPerRoute])
def get_stops_per_route(route_id: str, db: Session = Depends(get_db)):
    route_stops = (
        db.query(RouteStop)
        .options(joinedload(RouteStop.stop))  # fetch all data upfront rather than lazy loadibg
        .filter(RouteStop.route_id == route_id)
        .order_by(RouteStop.sequence)
        .all()
    )

    if not route_stops:
        raise HTTPException(status_code=404, detail="No stops found for this route")

    return [

        { "id": route_stops.id,
        "name": route_stops.id
        }
    ]
