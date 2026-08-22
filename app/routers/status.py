from fastapi import APIRouter, Depends, Query
from datetime import datetime, timezone

from app.repositories.journey_repository import JourneyRepository
from app.repositories.router_repository import RouteRepository
from app.dependencies.dependency import get_journey_repository, get_route_repository
from app.exceptions.exceptions import JourneyNotFoundError, RouteNotFoundError

router = APIRouter(prefix="/journeys/status", tags=["Journey Status"])


def ensure_timezone_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def minutes_left(pred: datetime | None) -> int | None:
    if not pred:
        return None
    try:
        pred = ensure_timezone_aware(pred)
        if pred is None:
            return None
        delta = pred - datetime.now(timezone.utc)
        mins = int(delta.total_seconds() // 60)
        return max(mins, 0) if mins > -60 else None
    except Exception:
        return None


@router.get("/journey/{journey_id}")
async def journey_status(
    journey_id: str,
    journey_repo: JourneyRepository = Depends(get_journey_repository),
    route_repo: RouteRepository = Depends(get_route_repository)) -> dict:

    journey = await journey_repo.GetJourneyById(journey_id)
    if not journey:
        raise JourneyNotFoundError(detail=f"Journey {journey_id} not found")

    route = await route_repo.GetRouteID(journey.route_id)
    destination = None
    if journey.end_stop_id:
        dest_stop = await route_repo.GetStopById(journey.end_stop_id)
        if dest_stop:
            destination = dest_stop.name

    predicted = ensure_timezone_aware(journey.predicted_arrival)
    minutes_remaining = None
    if predicted:
        delta = predicted - datetime.now(timezone.utc)
        minutes_remaining = max(0, int(delta.total_seconds() / 60))

    return {
        "journey_id": journey.id,
        "service_id": journey.service_id,
        "route_id": journey.route_id,
        "route_number": route.name if route else journey.route_id,
        "destination": destination,
        "status": journey.status,
        "predicted_arrival": predicted.isoformat() if predicted else None,
        "minutes_remaining": minutes_remaining,
        "start_stop_id": journey.start_stop_id,
        "end_stop_id": journey.end_stop_id,
        "created_at": journey.created_at.isoformat(),
        "confidence": journey.confidence,
    }


@router.get("/stop/{stop_id}")
async def journeys_for_stop(
    stop_id: str,
    journey_repo: JourneyRepository = Depends(get_journey_repository),
    limit: int = Query(100, ge=1, le=500),
    hours: int = Query(24, ge=1, le=168)) -> dict:

    journeys, total, active = await journey_repo.GetJourneysForStop(stop_id, limit, hours)

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
                "predicted_arrival": ensure_timezone_aware(j.predicted_arrival),
                "minutes_remaining": minutes_left(j.predicted_arrival),
            }
            for j in journeys
        ],
    }


@router.get("/{route_id}")
async def single_route(
    route_id: str,
    journey_repo: JourneyRepository = Depends(get_journey_repository),
    route_repo: RouteRepository = Depends(get_route_repository),
    limit: int = Query(50, ge=1, le=200))->dict:

    route = await route_repo.GetRouteID(route_id)
    if not route:
        raise RouteNotFoundError(detail=f"Route '{route_id}' not found")

    latest = await journey_repo.GetLatestJourneyByRoute(route_id)
    total_today = await journey_repo.GetRouteJourneyCountToday(route_id)
    recent = await journey_repo.GetRecentJourneysByRoute(route_id, limit)

    predicted = ensure_timezone_aware(latest.predicted_arrival) if latest else None

    return {
        "route_id": route_id,
        "route_name": route.name or route_id,
        "current_status": latest.status if latest else None,
        "predicted_arrival": predicted.isoformat() if predicted else None,
        "minutes_remaining": minutes_left(latest.predicted_arrival) if latest else None,
        "updated_user_submitted": latest.created_at.isoformat() if latest else None,
        "total_journeys_today": total_today,
        "recent_trips": [
            {
                "id": j.id,
                "status": j.status,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "minutes_remaining": minutes_left(j.predicted_arrival),
            }
            for j in recent
        ],
    }


@router.get("/active")
async def get_active_journeys(
    journey_repo: JourneyRepository = Depends(get_journey_repository),
    route_repo: RouteRepository = Depends(get_route_repository),
    limit: int = Query(20, ge=1, le=50)):

    journeys = await journey_repo.GetActiveJourneys(limit)

    result = []
    for j in journeys:
        route = await route_repo.GetRouteID(j.route_id)
        start_stop = await route_repo.GetStopById(j.start_stop_id)

        predicted = ensure_timezone_aware(j.predicted_arrival)
        minutes_remaining = None
        if predicted:
            delta = predicted - datetime.now(timezone.utc)
            minutes_remaining = max(0, int(delta.total_seconds() / 60))

        result.append({
            "journey_id": j.id,
            "route_number": route.name if route else j.route_id,
            "status": j.status,
            "start_stop": start_stop.name if start_stop else "Unknown",
            "minutes_remaining": minutes_remaining,
            "created_at": j.created_at.isoformat(),
        })

    return result