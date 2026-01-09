from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload

from app.models.Database import SessionLocal, engine, get_db
from app.models.Route import Route
from app.models.RouteStop import RouteStop

from app.schemas.route import RouteOut
from app.schemas.route import StopPerRoute


router = APIRouter(prefix="/route", tags=["Route"])


# GET /route/routes - Retrieve all routes
@router.get("/routes", response_model=List[RouteOut])  
def get_routes(db: Session = Depends(get_db)):
    routes = db.query(Route).all()
    return routes # pydantic convert to sql object



#GET /route/routes - Fetch all stops along a route using {route_id}
@router.get("/routes/{route_id}/stops", response_model=List[StopPerRoute])
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

    #just let pydantic do all the wor
    return route_stops