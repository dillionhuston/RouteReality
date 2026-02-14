# services/prediction/logic.py
# this is where we guess when the bus will show up
# still rough but way better than just spitting timetable times

from datetime import datetime, timezone, timedelta, time
from typing import List, Optional

from sqlalchemy.orm import Session

from app.Services.Prediction.data import get_user_journeys, get_recent_user_events


def weighted_average(times: List[datetime]) -> Optional[datetime]:
    """Average past arrivals but trust newer ones more"""
    if not times:
        return None

    # newest first, max 10
    times = times[:10]
    weights = list(range(len(times), 0, -1))  # 10,9,8...1

    total_w = sum(weights)
    weighted_sum = sum(w * t.timestamp() for w, t in zip(weights, times))

    avg_ts = weighted_sum / total_w
    return datetime.fromtimestamp(avg_ts, tz=timezone.utc)


def adjust_timetable_time(
    static_time: time,
    ref: datetime,
    is_tomorrow: bool = False,
    max_drift_min: int = 12) -> tuple[datetime, float]:
    """Turn timetable time-of-day into real datetime, push forward if already missed"""
    date = ref.date()
    if is_tomorrow:
        date += timedelta(days=1)

    sched = datetime.combine(date, static_time, tzinfo=timezone.utc)

    if sched >= ref:
        return sched, 0.55  # still in future, ok confidence

    # already gone → drift forward a bit
    late_min = (ref - sched).total_seconds() / 60
    drift = min(late_min, max_drift_min)
    adjusted = ref + timedelta(minutes=drift + 2)  # +2 min buffer
    conf = max(0.25, 0.55 - (drift / max_drift_min) * 0.3)

    return adjusted, conf


def predict_bus_time(
    static_time: Optional[time] = None,
    static_is_tomorrow: bool = False,
    user_events: List[dict] = None,
    past_arrivals: List[datetime] = None,
    now: Optional[datetime] = None) -> tuple[Optional[datetime], float]:
    """
    Main prediction logic - combines timetable + crowd history + recent events
    tries hard not to tell people "bus in -3 min" when it's already gone
    """
    if now is None:
        now = datetime.now(timezone.utc)

    if user_events is None:
        user_events = []
    if past_arrivals is None:
        past_arrivals = []

    # default fallback - something ahead
    pred_time = now + timedelta(minutes=12)
    confidence = 0.25

    # 1. Recent ARRIVED reports
    arrived = [e["time"] for e in user_events if e["type"] == "ARRIVED"]
    if arrived:
        latest_arr = max(arrived, key=lambda t: t.timestamp() if hasattr(t, 'timestamp') else t)
        if latest_arr.tzinfo is None:
            latest_arr = latest_arr.replace(tzinfo=timezone.utc)

        age_min = (now - latest_arr).total_seconds() / 60

        if age_min <= 5:  # very fresh → bus probably just left or boarding
            pred_time = latest_arr + timedelta(minutes=1)
            confidence = 0.88
            if age_min <= 2.5:
                return pred_time, confidence  # trust it a lot

        elif age_min <= 18:  # reasonable recent → bus left
            # fall through to timetable + crowd
            pass
        else:
            latest_arr = None  # too old, ignore

    #  2. Crowd historical average (recent arrivals only) 
    crowd_avg = weighted_average(past_arrivals)
    if crowd_avg:
        if crowd_avg.tzinfo is None:
            crowd_avg = crowd_avg.replace(tzinfo=timezone.utc)

        age_crowd = (now - crowd_avg).total_seconds() / 60
        if age_crowd < 90:  # not ancient
            if confidence < 0.60:
                pred_time = crowd_avg
                confidence = 0.60

    # 3. Timetable fallback (very important after a departure) 
    if static_time:
        sched, sched_conf = adjust_timetable_time(
            static_time, now, static_is_tomorrow, max_drift_min=18
        )

        # if we saw recent departure → push timetable forward more
        if 'age_min' in locals() and 5 < age_min <= 20:
            extra = min(12, max(0, age_min - 4))
            sched += timedelta(minutes=extra)
            sched_conf = max(0.45, sched_conf - 0.08)

        if sched_conf > confidence:
            pred_time = sched
            confidence = sched_conf

    # 4. Delay reports → add buffer only if prediction looks sane 
    delays = sum(1 for e in user_events if e["type"] == "DELAYED")
    if delays >= 1 and (pred_time - now).total_seconds() / 60 < 35:
        extra_min = 4 + delays * 3.5
        pred_time += timedelta(minutes=extra_min)
        confidence = min(0.90, confidence + 0.12)

    # Final safety net: no past or too close predictions
    if pred_time < now:
        pred_time = now + timedelta(minutes=2)
    elif (pred_time - now).total_seconds() / 60 < 1.5:
        pred_time = now + timedelta(minutes=2.5)

    confidence = min(0.94, max(0.18, confidence))

    return pred_time, confidence


def get_bus_prediction(
    route_id: str,
    stop_id: str,
    static_time: Optional[time] = None,
    static_is_tomorrow: bool = False,
    db: Session = None) -> tuple[Optional[datetime], float]:
    """Main entry point - grab data, run prediction, return arrival + confidence"""
    if db is None:
        raise ValueError("Need db session")

    now = datetime.now(timezone.utc)

    past_times = get_user_journeys(
        route_id=route_id,
        stop_id=stop_id,
        db=db
    )

    events = get_recent_user_events(
        route_id=route_id,
        stop_id=stop_id,
        db=db
    )

    return predict_bus_time(
        static_time=static_time,
        static_is_tomorrow=static_is_tomorrow,
        user_events=events,
        past_arrivals=past_times,
        now=now
    )