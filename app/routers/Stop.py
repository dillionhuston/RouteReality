from datetime import datetime, timezone, timedelta
import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.Database import get_db
from app.repositories.router_repository import RouteRepository
from app.dependencies.dependency import get_route_repository
from app.schemas.route import RouteAtStop

router = APIRouter(prefix="/stops", tags=["Stops"])


@router.get("/{stop_id}/routes", response_model=list[RouteAtStop])
async def get_routes_for_stop(
    stop_id: str,
    route_repo: RouteRepository = Depends(get_route_repository)):

    route_stops = await route_repo.GetRouteStopsForStop(stop_id)
    if not route_stops:
        raise HTTPException(404, "No routes serve this stop")

    result = []
    for rs in route_stops:
        route = await route_repo.GetRouteID(rs.route_id)
        if route:
            result.append(RouteAtStop(
                route_id=route.id,
                route_number=route.name,
                direction=rs.direction,
            ))

    return result


@router.get("/{stop_id}/arrivals")
async def get_arrivals_for_stop(
    stop_id: str,
    route_repo: RouteRepository = Depends(get_route_repository)):
    route_stops = await route_repo.GetRouteStopsForStop(stop_id)
    if not route_stops:
        raise HTTPException(404, "No routes serve this stop")

    now = datetime.now(timezone.utc)
    arrivals = []

    for rs in route_stops:
        route = await route_repo.GetRouteID(rs.route_id)
        if not route:
            continue

        stops_in_order = await route_repo.GetRouteStopsInOrder(route.id)
        destination = stops_in_order[-1].stop.name if stops_in_order else route.name

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