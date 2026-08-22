from datetime import datetime, timezone, timedelta, time, UTC
from typing import List, Optional

from sqlalchemy.orm import Session

from app.utils.fetch_time import fetch_scheduled_time
from app.repositories.event_repository import EventRepository
from app.repositories.journey_repository import JourneyRepository
from app.exceptions.exceptions import ServiceError


def weighted_average(times):
    """Average past arrivals but trust newer ones more"""
    if not times:
        return None

    times = times[:10]
    weights = list(range(len(times), 0, -1))

    total_w = sum(weights)
    weighted_sum = sum(w * t.timestamp() for w, t in zip(weights, times))

    avg_ts = weighted_sum / total_w
    return datetime.fromtimestamp(avg_ts, tz=timezone.utc)


def adjust_timetable_time(
    static_time,
    ref,
    is_tomorrow=False,
    max_drift_min=12):
    """Turn timetable time-of-day into real datetime, push forward if already missed"""
    date = ref.date()
    if is_tomorrow:
        date += timedelta(days=1)

    sched = datetime.combine(date, static_time, tzinfo=timezone.utc)

    if sched >= ref:
        return sched, 0.55

    late_min = (ref - sched).total_seconds() / 60
    drift = min(late_min, max_drift_min)
    adjusted = sched + timedelta(minutes=drift + 2)
    conf = max(0.25, 0.55 - (drift / max_drift_min) * 0.3)

    return adjusted, conf


def predict_bus_time(
    static_time=None,
    static_is_tomorrow=False,
    user_events=None,
    past_arrivals=None,
    now=None):
    """
    Main prediction logic - combines timetable + crowd history + recent events
    tries hard not to tell people "bus in -3 min" when it's already gone
    """

    age_min = None
    if now is None:
        now = datetime.now(timezone.utc)

    if user_events is None:
        user_events = []
    if past_arrivals is None:
        past_arrivals = []

    pred_time = now + timedelta(minutes=6)
    confidence = 0.25

    arrived = [e["time"] for e in user_events if e["type"] == "ARRIVED"]
    if arrived:
        latest_arr = max(arrived, key=lambda t: t.timestamp() if hasattr(t, 'timestamp') else t)
        if latest_arr.tzinfo is None:
            latest_arr = latest_arr.replace(tzinfo=timezone.utc)

        age_min = (now - latest_arr).total_seconds() / 60

        if age_min <= 5:
            pred_time = latest_arr + timedelta(minutes=1)
            confidence = 0.88
            if age_min <= 2.5:
                return pred_time, confidence

        elif age_min <= 18:
            pass
        else:
            latest_arr = None

    crowd_avg = weighted_average(past_arrivals)
    if crowd_avg:
        if crowd_avg.tzinfo is None:
            crowd_avg = crowd_avg.replace(tzinfo=timezone.utc)

        age_crowd = (now - crowd_avg).total_seconds() / 60
        if age_crowd < 90:
            if confidence < 0.60:
                pred_time = crowd_avg
                confidence = 0.60

    if static_time:
        sched, sched_conf = adjust_timetable_time(
            static_time, now, static_is_tomorrow, max_drift_min=18
        )

        if age_min is not None and 5 < age_min <= 20:
            extra = min(12, max(0, age_min - 4))
            sched += timedelta(minutes=extra)
            sched_conf = max(0.45, sched_conf - 0.08)

        if sched_conf > confidence:
            pred_time = sched
            confidence = sched_conf

    delays = sum(1 for e in user_events if e["type"] == "DELAYED")
    if delays >= 1 and (pred_time - now).total_seconds() / 60 < 35:
        extra_min = 4 + delays * 3.5
        pred_time += timedelta(minutes=extra_min)
        confidence = min(0.90, confidence + 0.12)

    if pred_time < now:
        pred_time = now + timedelta(minutes=2)
    elif (pred_time - now).total_seconds() / 60 < 1.5:
        pred_time = now + timedelta(minutes=2.5)

    confidence = min(0.94, max(0.18, confidence))

    return pred_time, confidence


def get_bus_prediction(
    route_id,
    stop_id,
    static_time=None,
    static_is_tomorrow=False,
    db=None):
    """Main entry point - grab data, run prediction, return arrival + confidence"""
    if db is None:
        raise ServiceError(detail="Database session required")

    static = fetch_scheduled_time(route_id, stop_id)
    now = datetime.now(timezone.utc)

    past_times = JourneyRepository().GetRecentArrivedJourneys(
        route_id=route_id,
        stop_id=stop_id,
        limit=5,
        now=datetime.now(tz=UTC)
    )

    events = EventRepository.GetRecentEventsByRouteAndStop(
        route_id=route_id,
        stop_id=stop_id,
        limit=5,
        cutoff_minutes=60
    )

    return predict_bus_time(
        static_time=static_time,
        static_is_tomorrow=static_is_tomorrow,
        user_events=events,
        past_arrivals=past_times,
        now=now,
    )