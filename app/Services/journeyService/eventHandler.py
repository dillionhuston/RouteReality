import asyncio
from datetime import datetime, timezone, timedelta, date
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.routers.Broadcast import broadcast_service_update
from app.utils.logger.logger import get_logger
from app.models.Journey import Journey
from app.schemas.journey import JourneyEventType
from app.Services.Prediction.service import get_prediction
from app.Services.push_service.push_service import send_notifications_to_service

from app.models.UserStats import UserStats

logger = get_logger()

_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


class JourneyEventHandler:
    """Service for handling journey lifecycle events (arrived, delayed, stop_reached, etc.)."""

    @staticmethod
    def _fire_broadcast(service_id: str, payload: dict) -> None:
        """Fire broadcast asynchronously using the main event loop."""
        if _main_loop is None:
            logger.warning("Broadcast skipped: main loop not set")
            return

        try:
            asyncio.run_coroutine_threadsafe(
                broadcast_service_update(service_id, payload),
                _main_loop
            )
        except Exception as e:
            logger.warning(f"Broadcast failed (non-critical): {e}")

    @staticmethod
    def _parse_predicted_arrival(predicted) -> datetime | None:
        """Safely parse predicted_arrival from various formats (datetime, dict, str)."""
        if predicted is None:
            return None
        if isinstance(predicted, datetime):
            return predicted
        if isinstance(predicted, dict):
            pred_str = predicted.get('predicted_arrival')
            if pred_str:
                try:
                    return datetime.fromisoformat(pred_str.replace('Z', '+00:00'))
                except Exception:
                    pass
        if isinstance(predicted, str):
            try:
                return datetime.fromisoformat(pred_str.replace('Z', '+00:00'))
            except Exception:
                pass
        return None

    @staticmethod
    def _update_user_stats(db: Session, user_id: str, was_accurate: bool = False) -> int:
        """Update user statistics after a report."""
        stats = db.query(UserStats).filter(UserStats.user_id == user_id).first()

        if not stats:
            stats = UserStats(user_id=user_id)
            db.add(stats)
            db.commit()
            db.refresh(stats)

        points_earned = 5
        stats.points += points_earned
        stats.total_reports += 1

        if was_accurate:
            stats.accurate_reports += 1

        # Update streak
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

        # Badge logic
        badges = stats.earned_badges.split(',') if stats.earned_badges else []
        badge_set = set(badges)

        if stats.total_reports == 1:
            badge_set.add("first_report")
        if stats.streak_current >= 3:
            badge_set.add("streak_3")
        if stats.streak_current >= 7:
            badge_set.add("streak_7")
        if stats.streak_current >= 30:
            badge_set.add("streak_30")
        if stats.accurate_reports >= 10:
            badge_set.add("accurate_10")
        if stats.accurate_reports >= 50:
            badge_set.add("accurate_50")
        if stats.points >= 100:
            badge_set.add("100_points")
        if stats.points >= 1000:
            badge_set.add("1000_points")

        stats.earned_badges = ','.join(sorted(badge_set)) if badge_set else None

        db.commit()
        logger.info(f"User {user_id} earned {points_earned} points. Total: {stats.points}")

        return points_earned

    @staticmethod
    def _update_prediction(journey: Journey, db: Session) -> None:
        """Refresh prediction for the journey."""
        stop_id = journey.end_stop_id or journey.start_stop_id
        if not stop_id:
            logger.warning(f"No stop available for prediction on journey {journey.id}")
            return

        try:
            predicted_iso = get_prediction(
                route_id=journey.route_id,
                stop_id=stop_id,
                static_dt=datetime.now(timezone.utc),
                db=db
            )
            if predicted_iso:
                journey.predicted_arrival = predicted_iso
        except Exception as e:
            logger.exception(f"Prediction update failed for journey {journey.id}: {e}")

    # Event Handlers 

    @staticmethod
    def arrived(journey_id: UUID, db: Session, user_id: str = None) -> Journey:
        journey = db.get(Journey, str(journey_id))
        if not journey:
            raise HTTPException(404, f"Journey {journey_id} not found")

        if journey.status not in {JourneyEventType.EVENT_TYPE_STARTED, JourneyEventType.EVENT_TYPE_DELAYED}:
            raise HTTPException(400, f"Cannot mark as ARRIVED from status: {journey.status}")

        journey.status = JourneyEventType.EVENT_TYPE_ARRIVED
        journey.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(journey)

        # User stats
        if user_id:
            try:
                pred_dt = JourneyEventHandler._parse_predicted_arrival(journey.predicted_arrival)
                was_accurate = pred_dt and abs((datetime.now(timezone.utc) - pred_dt).total_seconds() / 60) <= 3
                JourneyEventHandler._update_user_stats(db, user_id, was_accurate)
            except Exception as e:
                logger.warning(f"Failed to update user stats: {e}")

        # Broadcast
        pred_dt = JourneyEventHandler._parse_predicted_arrival(journey.predicted_arrival)
        minutes_remaining = max(0, int((pred_dt - datetime.now(timezone.utc)).total_seconds() / 60)) if pred_dt else None

        JourneyEventHandler._fire_broadcast(journey.service_id, {
            "current_status": "ARRIVED",
            "type": "BUS_ARRIVED",
            "message": "Bus has arrived at this stop",
            "minutes_remaining": minutes_remaining,
            "predicted_arrival": pred_dt.isoformat() if pred_dt else None
        })

        # Push notifications
        try:
            send_notifications_to_service(
                db=db,
                service_id=journey.service_id,
                title=f"Bus {journey.route_id} arrived",
                body="The bus has arrived at the stop.",
                url=f"/tracking?journey={journey.id}"
            )
        except Exception as e:
            logger.warning(f"Push notification failed for arrived event: {e}")

        return journey

    @staticmethod
    def delayed(journey_id: UUID, db: Session, user_id: str = None) -> Journey:
        journey = db.get(Journey, str(journey_id))
        if not journey:
            raise HTTPException(404, f"Journey {journey_id} not found")

        if journey.status not in {JourneyEventType.EVENT_TYPE_STARTED, JourneyEventType.EVENT_TYPE_ARRIVED}:
            raise HTTPException(400, f"Cannot mark as DELAYED from status: {journey.status}")

        journey.status = JourneyEventType.EVENT_TYPE_DELAYED
        journey.updated_at = datetime.now(timezone.utc)

        pred_dt = JourneyEventHandler._parse_predicted_arrival(journey.predicted_arrival)
        if pred_dt:
            journey.predicted_arrival = pred_dt + timedelta(minutes=10)
        else:
            JourneyEventHandler._update_prediction(journey, db)

        db.commit()
        db.refresh(journey)

        if user_id:
            try:
                JourneyEventHandler._update_user_stats(db, user_id, was_accurate=False)
            except Exception as e:
                logger.warning(f"Failed to update user stats: {e}")

        # Broadcast
        pred_dt = JourneyEventHandler._parse_predicted_arrival(journey.predicted_arrival)
        minutes_remaining = max(0, int((pred_dt - datetime.now(timezone.utc)).total_seconds() / 60)) if pred_dt else None

        JourneyEventHandler._fire_broadcast(journey.service_id, {
            "current_status": "DELAYED",
            "type": "BUS_DELAYED",
            "message": "Delay reported on this route",
            "minutes_remaining": minutes_remaining,
            "predicted_arrival": pred_dt.isoformat() if pred_dt else None
        })

        # Push
        try:
            send_notifications_to_service(
                db=db,
                service_id=journey.service_id,
                title=f"Bus {journey.route_id} delayed",
                body="The bus has been delayed by 10 minutes.",
                url=f"/tracking?journey={journey.id}"
            )
        except Exception as e:
            logger.warning(f"Push notification failed for delayed event: {e}")

        return journey

    @staticmethod
    def stop_reached(journey_id: UUID, db: Session, user_id: str = None) -> Journey:
        journey = db.get(Journey, str(journey_id))
        if not journey:
            raise HTTPException(404, f"Journey {journey_id} not found")

        if journey.status not in {JourneyEventType.EVENT_TYPE_ARRIVED, JourneyEventType.EVENT_TYPE_DELAYED}:
            raise HTTPException(400, f"Cannot mark stop reached from status: {journey.status}")

        journey.status = JourneyEventType.EVENT_TYPE_STOP_REACHED
        journey.ended_at = datetime.now(timezone.utc)
        journey.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(journey)

        if user_id:
            try:
                JourneyEventHandler._update_user_stats(db, user_id, was_accurate=False)
            except Exception as e:
                logger.warning(f"Failed to update user stats: {e}")

        JourneyEventHandler._fire_broadcast(journey.service_id, {
            "current_status": "STOP_REACHED",
            "type": "JOURNEY_COMPLETE",
            "message": "Journey complete! Thanks for riding.",
            "route_id": journey.route_id,
            "stop_id": journey.end_stop_id
        })

        return journey

    #  Main Dispatcher 

    @staticmethod
    def add_event(
        journey_id: UUID,
        event_type: JourneyEventType,
        db: Session,
        user_id: str = None) -> Journey:

        """Dispatch to the appropriate event handler."""
        handlers = {
            JourneyEventType.EVENT_TYPE_ARRIVED: JourneyEventHandler.arrived,
            JourneyEventType.EVENT_TYPE_DELAYED: JourneyEventHandler.delayed,
            JourneyEventType.EVENT_TYPE_STOP_REACHED: JourneyEventHandler.stop_reached,
        }

        handler = handlers.get(event_type)
        if handler is None:
            logger.warning(f"Unsupported event type: {event_type}")
            raise HTTPException(400, f"Unsupported event type: {event_type}")

        return handler(journey_id, db, user_id)