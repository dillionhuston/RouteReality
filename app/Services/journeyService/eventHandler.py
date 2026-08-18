from uuid import uuid4
from datetime import datetime, timezone, timedelta, date
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.journey_repository import JourneyRepository
from app.repositories.event_repository import EventRepository
from app.repositories.user_stats_repository import UserStatsRepository
from app.models.Event import Event
from app.models.Journey import Journey
from app.models.UserStats import UserStats
from app.utils.logger.logger import get_logger
from app.routers.Broadcast import broadcast_service_update
from app.Services.push_service.push_service import send_notifications_to_service

logger = get_logger(__name__)

class JourneyEventHandler:
    def __init__(
        self,
        journey_repo: JourneyRepository,
        event_repo: EventRepository,
        user_stats_repo: UserStatsRepository):

        self.journey_repo = journey_repo
        self.event_repo = event_repo
        self.user_stats_repo = user_stats_repo

    async def add_event(
        self,
        event_type: str,
        journey_id: str,
        user_id: str):
        
        handlers = {
            "ARRIVED": self._handle_arrived,
            "DELAYED": self._handle_delayed,
            "STOP_REACHED": self._handle_stop_reached,
        }

        handler = handlers.get(event_type)
        if handler is None:
            logger.warning(f"Unsupported event type: {event_type}")
            raise HTTPException(400, f"Unsupported event type: {event_type}")
        return await handler(journey_id, user_id)

    async def _handle_arrived(self, journey_id: str, user_id: str):

        journey = await self.journey_repo.GetActiveJourney(journey_id)
        if not journey:
            raise HTTPException(404, f"Journey {journey_id} not found")
        if journey.status not in ["STARTED", "DELAYED"]:
            raise HTTPException(400, f"Cannot mark as ARRIVED from status: {journey.status}")

        journey = await self.journey_repo.UpdateJourneyStatus(journey, "ARRIVED")

        now = datetime.now(timezone.utc)
        event = Event(
            id=str(uuid4()),                          
            journey_id=journey_id,
            type="ARRIVED",
            stop_id=journey.start_stop_id,
            user_id=user_id,
            reported_time=now,                       
            created_at=now,
        )
        await self.event_repo.CreateEvent(event)

        if user_id:
            await self._update_user_stats(user_id, journey)

        await self._broadcast_and_push(journey, "ARRIVED", "Bus Arrived", "The bus has arrived at the stop.")
        return journey

    async def _handle_delayed(self, journey_id: str, user_id: str):

        journey = await self.journey_repo.GetActiveJourney(journey_id)
        if not journey:
            raise HTTPException(404, f"Journey {journey_id} not found")
        if journey.status not in ["STARTED", "ARRIVED"]:
            raise HTTPException(400, f"Cannot mark as DELAYED from status: {journey.status}")

        journey = await self.journey_repo.AddDelay(journey, 10)

        now = datetime.now(timezone.utc)
        event = Event(
            id=str(uuid4()),                         
            journey_id=journey_id,
            type="DELAYED",
            stop_id=journey.start_stop_id,
            user_id=user_id,
            reported_time=now,                      
            created_at=now,
        )
        await self.event_repo.CreateEvent(event)

        if user_id:
            await self._update_user_stats(user_id, journey)

        await self._broadcast_and_push(journey, "DELAYED", "Bus Delayed", "The bus has been delayed by 10 minutes.")
        return journey

    async def _handle_stop_reached(self, journey_id: str, user_id: str):

        journey = await self.journey_repo.GetActiveJourney(journey_id)
        if not journey:
            raise HTTPException(404, f"Journey {journey_id} not found")
        if journey.status not in ["ARRIVED", "DELAYED"]:
            raise HTTPException(400, f"Cannot mark stop reached from status: {journey.status}")

        journey = await self.journey_repo.UpdateJourneyStatus(journey, "STOP_REACHED", ended_at=datetime.now(timezone.utc))

        now = datetime.now(timezone.utc)
        event = Event(
            id=str(uuid4()),
            journey_id=journey_id,
            type="STOP_REACHED",
            stop_id=journey.end_stop_id or journey.start_stop_id,
            user_id=user_id,
            reported_time=now,                      
            created_at=now,
        )
        await self.event_repo.CreateEvent(event)

        if user_id:
            await self._update_user_stats(user_id, journey)

        await self._broadcast_and_push(journey, "STOP_REACHED", "Trip Complete", "You've reached your destination.")
        return journey

    async def _update_user_stats(self, user_id: str, journey: Journey):

        stats = await self.user_stats_repo.GetUserStats(user_id)
        if not stats:
            stats = UserStats(user_id=user_id)
            stats = await self.user_stats_repo.CreateUserStats(stats)

        points_earned = 5
        stats.points += points_earned
        stats.total_reports += 1

        if journey.predicted_arrival:
            diff_min = abs((datetime.now(timezone.utc) - journey.predicted_arrival).total_seconds() / 60)
            if diff_min <= 3:
                stats.accurate_reports += 1

        today = date.today()
        if stats.last_report_date:
            days_diff = (today - stats.last_report_date).days
            if days_diff == 1:
                stats.streak_current += 1
            elif days_diff > 1:
                stats.streak_current = 1
        else:
            stats.streak_current = 1

        if stats.streak_current > stats.streak_best:
            stats.streak_best = stats.streak_current
        stats.last_report_date = today

        #TODO I HAVE TO MOVE THIS INTO A SERVICE, JUST DONE THIS TO GET IT DONE FAST 
        badges = set(stats.earned_badges.split(',') if stats.earned_badges else [])
        if stats.total_reports == 1:
            badges.add("first_report")
        if stats.streak_current >= 3:
            badges.add("streak_3")
        if stats.streak_current >= 7:
            badges.add("streak_7")
        if stats.streak_current >= 30:
            badges.add("streak_30")
        if stats.accurate_reports >= 10:
            badges.add("accurate_10")
        if stats.accurate_reports >= 50:
            badges.add("accurate_50")
        if stats.points >= 100:
            badges.add("100_points")
        if stats.points >= 1000:
            badges.add("1000_points")
        stats.earned_badges = ','.join(sorted(badges)) if badges else None

        await self.user_stats_repo.UpdateUserStats(stats)
        logger.info(f"User {user_id} earned {points_earned} points. Total: {stats.points}")

    async def _broadcast_and_push(self, journey: Journey, status: str, title: str, body: str):

        predicted = journey.predicted_arrival
        if predicted and predicted.tzinfo is None:
            predicted = predicted.replace(tzinfo=timezone.utc)
        
        payload = {
            "current_status": status,
            "predicted_arrival": predicted.isoformat() if predicted else None,
            "minutes_remaining": max(0, int((predicted - datetime.now(timezone.utc)).total_seconds() / 60)) if predicted else None,
            "message": body,
        }
        try:
            await broadcast_service_update(journey.service_id, payload)
        except Exception as e:
            logger.warning(f"Broadcast failed: {e}")

        try:
            url = f"/tracking?journey={journey.id}"
            await send_notifications_to_service(
                self.journey_repo.db,
                journey.service_id,
                title,
                body,
                url
            )
        except Exception as e:
            logger.warning(f"Push notification failed: {e}")