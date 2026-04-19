#!/usr/bin/env python3
"""
Schedule helpers.

Compute the next scheduled sequence start based on a weekly schedule (list of
7 booleans, index 0 = Monday .. 6 = Sunday) and a start_at time "HH:MM".
"""

from datetime import datetime, timedelta
from typing import List, Optional


def _parse_start_at(start_at: str) -> Optional[tuple]:
    """Parse an 'HH:MM' string. Returns (hour, minute) or None if invalid."""
    if not isinstance(start_at, str) or ":" not in start_at:
        return None
    try:
        h_str, m_str = start_at.split(":", 1)
        hour = int(h_str)
        minute = int(m_str)
    except ValueError:
        return None
    if not (0 <= hour < 24 and 0 <= minute < 60):
        return None
    return hour, minute


def compute_next_sequence(
    now: datetime,
    schedule: Optional[List[bool]],
    start_at: Optional[str],
) -> Optional[datetime]:
    """
    Compute the next datetime at which a sequence will start.

    Args:
        now: Current local datetime.
        schedule: List of 7 booleans (Monday..Sunday). Any other shape returns None.
        start_at: "HH:MM" string.

    Returns:
        The next datetime a sequence is scheduled, or None if none is planned.
    """
    if not schedule or not isinstance(schedule, list) or len(schedule) != 7:
        return None
    if not any(bool(d) for d in schedule):
        return None

    parsed = _parse_start_at(start_at or "")
    if parsed is None:
        return None
    hour, minute = parsed

    today_start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    for offset in range(0, 8):
        candidate = today_start + timedelta(days=offset)
        weekday = candidate.weekday()
        if not schedule[weekday]:
            continue
        if offset == 0 and candidate <= now:
            continue
        return candidate

    return None
