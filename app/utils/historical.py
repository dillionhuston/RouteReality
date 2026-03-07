from datetime import datetime
from sqlalchemy import select
from app.models.HistoricalDelay import HistoricalDelay  

def get_historical_delay(db, route_id: str, stop_id: str, dt: datetime) -> float | None:
    """
    Get average delay for this route/stop/hour.
    Returns None if no reliable data (sample < 5).
    """
    hour = dt.hour
    result = db.execute(
        select(HistoricalDelay).where(
            HistoricalDelay.route_id == route_id,
            HistoricalDelay.stop_id == stop_id,
            HistoricalDelay.hour == hour,
            HistoricalDelay.sample_count >= 5
        ).order_by(HistoricalDelay.last_updated.desc()).limit(1)
    ).scalar_one_or_none()

    return result.avg_delay_min if result else None