from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.Database import get_db
from app.schemas.journey import StartJourney, AddJourneyEvent
from app.Services.journeyService.journey_service import JourneyService
from app.Services.journeyService.eventHandler import JourneyEventHandler
from app.utils.logger.logger import get_logger
from app.Services.push_service.push_service import send_notifications_to_service
from app.routers.Broadcast import broadcast_service_update
from app.dependencies.get_current_user import get_current_user_optional
from app.models.User import User
from app.dependencies.dependency import get_journey_service, get_journey_event_handler

logger = get_logger(__name__)

COOLDOWN_SECONDS = 180
last_request_time: dict[UUID, datetime] = {}

router = APIRouter(prefix="/journeys", tags=["Journey"])

@router.post("/start")
async def start_journey(
    journey: StartJourney,
    current_user: User = Depends(get_current_user_optional),
    service: JourneyService = Depends(get_journey_service)):

    if not journey.start_stop_id or not journey.end_stop_id:
        raise HTTPException(
            status_code=400,
            detail="Need both start and end stop to begin journey"
        )
    try:
        new_j = await service.start_journey(data=journey)
        if new_j is None:
            raise ValueError("JourneyService returned None")
        logger.info(f"New journey started: {new_j['journey_id']} route={journey.route_id}")
        return new_j
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error(f"Failed to start journey: {ve}")
        raise HTTPException(status_code=500, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error starting journey: {e}")
        raise HTTPException(status_code=500, detail="Could not start journey due to server error")


@router.post("/{journey_id}/event")
async def add_journey_event(
    journey_id: UUID,
    event: AddJourneyEvent,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
    event_handler: JourneyEventHandler = Depends(get_journey_event_handler)):

    now = datetime.now(timezone.utc)
    last_request_time[journey_id] = now

    updated = await event_handler.add_event(
        event_type=event.event.value,
        journey_id=str(journey_id),
        user_id=current_user.id if current_user and not current_user.is_anonymous else None,
    )

    if not updated:
        logger.warning(f"Couldn't find active journey for {journey_id}")
        raise HTTPException(status_code=404, detail="Journey not found or already finished")

    logger.info(f"Added {event.event} to journey {journey_id}")

    try:
        notify_events = {"ARRIVED", "DELAYED", "STOP_REACHED"}
        if event.event.value in notify_events:
            service_id = getattr(updated, 'service_id', None) or getattr(updated, 'route_id', None)
            if service_id:
                titles = {
                    "ARRIVED": "Bus Arrived",
                    "DELAYED": "Bus Delayed",
                    "STOP_REACHED": "Trip Complete"
                }
                bodies = {
                    "ARRIVED": "Your bus has arrived at the stop.",
                    "DELAYED": "Your bus is running late.",
                    "STOP_REACHED": "You've reached your destination."
                }
                title = titles.get(event.event.value, "Bus Update")
                body = bodies.get(event.event.value, f"Your bus status: {event.event.value}")
                url = f"/tracking?journey={journey_id}"
                sent = await send_notifications_to_service(db, service_id, title, body, url)  # <-- await
                logger.info(f"Push notifications sent to {sent} subscribers for service {service_id}")
            else:
                logger.warning(f"No service_id/route_id found for journey {journey_id}, cannot send push")
    except Exception as e:
        logger.error(f"Failed to send push notifications for journey {journey_id}: {e}")

    try:
        minutes_remaining = None
        if updated.predicted_arrival:
            delta = updated.predicted_arrival - datetime.now(timezone.utc)
            minutes_remaining = max(0, int(delta.total_seconds() / 60))

        payload = {
            "current_status": updated.status,
            "predicted_arrival": updated.predicted_arrival.isoformat() if updated.predicted_arrival else None,
            "minutes_remaining": minutes_remaining,
            "message": f"Status updated to {updated.status}"
        }
        logger.info(f"Broadcasting to service {updated.service_id}: {payload}")
        await broadcast_service_update(updated.service_id, payload)
    except Exception as e:
        logger.error(f"WebSocket broadcast failed: {e}")

    return {
        "journey_id": str(updated.id),
        "current_status": updated.status,
        "predicted_arrival": updated.predicted_arrival,
        "last_event": event.event.value,
        "updated_at": updated.created_at,
        "message": f"Got it - recorded {event.event}"
    }