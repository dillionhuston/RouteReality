# utils/fetch_time.py
# pulls scheduled times from the CIF file for stops
# still using the raw text parse since DB import is being worked on

from datetime import datetime, time, timezone, timedelta
from pathlib import Path
import re
from typing import List, Optional, Tuple

from app.utils.logger.logger import get_logger

logger = get_logger(__name__)

# hardcoded for now - move to env/config later
CIF_FILE = Path("app/data/MPH_Metro_5_Jan_2026.cif")


def parse_time(time_str: str) -> Optional[time]:
    """'1430' → time(14, 30) or None if junk"""
    try:
        if len(time_str) != 4 or not time_str.isdigit():
            return None
        hour = int(time_str[:2])
        minute = int(time_str[2:])
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return time(hour, minute)
    except (ValueError, IndexError):
        pass
    return None


def fetch_all_scheduled_times_for_stop(stop_id: str) -> List[time]:
    """
    Scan the CIF file for all times attached to this stop code.
    Returns sorted unique times (or empty list if nothing found).
    """
    if not CIF_FILE.is_file():
        logger.warning(f"CIF file gone: {CIF_FILE}")
        return []

    try:
        with open(CIF_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        pattern = rf'{re.escape(stop_id)}(\d{{4}})'
        matches = re.findall(pattern, content)

        times = []
        for t_str in matches:
            t = parse_time(t_str)
            if t:
                times.append(t)

        unique_sorted = sorted(set(times))
        # print(f"Found {len(unique_sorted)} times for stop {stop_id}")
        return unique_sorted

    except Exception as e:
        logger.error(f"Failed reading CIF for {stop_id}: {e}")
        return []


def fetch_scheduled_time(route_id: str, stop_id: str) -> Optional[time]:
    """Legacy/simple version - just returns the first time found (used in some places)"""
    times = fetch_all_scheduled_times_for_stop(stop_id)
    if times:
        return times[0]  # earliest or first match - whatever
    return None


def get_closest_scheduled_time_to_now(
    route_id: str,
    stop_id: str,
    reference_time: Optional[datetime] = None) -> Tuple[Optional[time], Optional[int], bool]:
    """
    Finds the next scheduled time after reference_time (now by default).
    Returns (time, minutes_until, is_tomorrow)
    """
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)

    all_times = fetch_all_scheduled_times_for_stop(stop_id)
    if not all_times:
        # print(f"No schedule for {stop_id}")
        return None, None, False

    ref_date = reference_time.date()
    ref_time = reference_time.time()

    import bisect
    idx = bisect.bisect_right(all_times, ref_time)

    if idx < len(all_times):
        # next one today
        next_time = all_times[idx]
        full_dt = datetime.combine(ref_date, next_time, tzinfo=timezone.utc)
        mins = int((full_dt - reference_time).total_seconds() / 60)
        return next_time, max(0, mins), False

    # nothing left today → first tomorrow
    if all_times:
        next_time = all_times[0]
        tomorrow = ref_date + timedelta(days=1)
        full_dt = datetime.combine(tomorrow, next_time, tzinfo=timezone.utc)
        mins = int((full_dt - reference_time).total_seconds() / 60)
        return next_time, max(0, mins), True

    return None, None, False 