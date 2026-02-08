# services/prediction/logic.py
# this is where we actually guess when the bus shows up
# still rough around the edges but better than just using the timetable

from datetime import datetime, timezone, timedelta, time
from typing import List, Dict, Tuple, Optional

from app.Services.Prediction.data import get_user_journeys, get_recent_user_events
from sqlalchemy.orm import Session


def weighted_average(journey_times: List[datetime]) -> Optional[datetime]:
    """Average past arrivals but give more weight to recent ones."""
    if not journey_times:
        return None

    # take last 10 at most, newest first
    times = journey_times[:10]
    # weights: newest = highest (10,9,8...)
    weights = list(range(len(times), 0, -1))

    total = sum(weights)
    weighted = sum(w * t.timestamp() for w, t in zip(weights, times))

    avg_ts = weighted / total
    return datetime.fromtimestamp(avg_ts, tz=timezone.utc)


def adjust_static_time(
    static_time: time,
    reference: datetime,
    is_tomorrow: bool = False,
    max_drift: int = 12) -> Tuple[datetime, float]:
    """Turn time-of-day into real datetime + push it forward if already past."""
    ref_date = reference.date()
    if is_tomorrow:
        ref_date += timedelta(days=1)

    sched_dt = datetime.combine(ref_date, static_time, tzinfo=timezone.utc)

    if sched_dt >= reference:
        return sched_dt, 0.55  # still future, decent trust

    # already past - drift forward a bit
    late_min = (reference - sched_dt).total_seconds() / 60
    drift = min(late_min, max_drift)
    adjusted = reference + timedelta(minutes=drift + 2)
    conf = max(0.25, 0.55 - (drift / max_drift) * 0.3)

    return adjusted, conf


def predict_bus_time(
    static_time: Optional[time] = None,
    static_is_tomorrow: bool = False,
    user_events: List[Dict] = None,
    journey_times: List[datetime] = None,
    now: Optional[datetime] = None) -> Tuple[Optional[datetime], float]:
    """
    Guess when the bus actually arrives.
    Trust user reports most, then crowd history, then timetable, then guess.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if user_events is None:
        user_events = []
    if journey_times is None:
        journey_times = []

    # fallback if everything is empty
    pred = now + timedelta(minutes=10)
    conf = 0.20

    # 1. user reported their bus  arrived? trust this
    arrived = [e for e in user_events if e["type"] == "ARRIVED"]
    if arrived:
        latest = max((e["time"] for e in arrived), key=lambda t: t.timestamp())
        age_min = (now - latest).total_seconds() / 60
        if age_min < 6:  # fresh report
            # print(f"Using fresh ARRIVED from {age_min:.1f} min ago")
            return latest, 0.93
        pred = latest
        conf = 0.70

    # 2. crowd average from past journeys
    crowd = weighted_average(journey_times)
    if crowd and (now - crowd).total_seconds() < 3600:  # not ancient
        # print("Using crowd average")
        pred = crowd
        conf = max(conf, 0.55)

    # 3. timetable as backup
    if static_time:
        sched_dt, sched_conf = adjust_static_time(static_time, now, static_is_tomorrow)
        if sched_conf > conf:
            # print(f"Using timetable: {sched_dt.strftime('%H:%M')}")
            pred = sched_dt
            conf = sched_conf

    # 4. add buffer if people are reporting delays
    delay_count = sum(1 for e in user_events if e["type"] == "DELAYED")
    if delay_count > 0:
        extra = 5 + delay_count * 3  # 8, 11, 14...
        pred += timedelta(minutes=extra)
        conf = min(0.92, conf + 0.10)
        # print(f"Added {extra} min delay buffer ({delay_count} reports)")

    # never say the bus already came
    if pred < now:
        pred = now + timedelta(minutes=3)

    conf = min(0.95, max(0.15, conf))

    return pred, conf


def get_prediction(
    route_id: str,
    stop_id: str,
    static_time: Optional[time] = None,
    static_is_tomorrow: bool = False,
    session: Session = None,) -> Tuple[Optional[datetime], float]:
    """
    Main entry point.
    Grabs data, runs prediction, returns arrival + confidence.
    """
    if session is None:
        raise ValueError("Need a database session")

    now = datetime.now(timezone.utc)

    journeys = get_user_journeys(
        route_id=route_id,
        stop_id=stop_id,
        db=session,
    )

    events = get_recent_user_events(
        route_id=route_id,
        stop_id=stop_id,
        db=session,
    )

    # print(f"Got {len(journeys)} past journeys and {len(events)} recent events")

    return predict_bus_time(
        static_time=static_time,
        static_is_tomorrow=static_is_tomorrow,
        user_events=events,
        journey_times=journeys,
        now=now,
    )