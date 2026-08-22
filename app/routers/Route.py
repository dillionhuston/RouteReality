from typing import List
from fastapi import APIRouter, Depends

from app.repositories.router_repository import RouteRepository
from app.schemas.route import StopsPerRoute, RouteOut
from app.utils.logger import logger
from app.dependencies.get_current_user import get_current_user_optional
from app.models.User import User
from app.dependencies.dependency import get_route_repository
from app.exceptions.exceptions import RouteNotFoundError

router = APIRouter(prefix="/route", tags=["Routes"])
logger = logger.get_logger()


@router.get("/routes", response_model=List[RouteOut])
async def get_routes(
    repo: RouteRepository = Depends(get_route_repository),
    current_user: User = Depends(get_current_user_optional)):

    """Return all routes with first stop lat/lon for dropdowns or maps."""
    routes = await repo.GetRoutesWithStops()

    if not routes:
        logger.warning("No routes in database")
        raise RouteNotFoundError(detail="No routes available")

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
async def get_stops_per_route(
    route_id: str,
    repo: RouteRepository = Depends(get_route_repository),
    current_user: User = Depends(get_current_user_optional)):

    """Returns stops for a route."""
    stops = await repo.GetStopsByRoute(route_id)

    if not stops:
        raise RouteNotFoundError(detail=f"No stops for route '{route_id}'")

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