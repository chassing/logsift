"""Shared utilities for logdelve."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

_TIME_UNITS: dict[str, str] = {
    "s": "seconds",
    "m": "minutes",
    "minute": "minutes",
    "minutes": "minutes",
    "h": "hours",
    "hour": "hours",
    "hours": "hours",
    "d": "days",
    "day": "days",
    "days": "days",
    "w": "weeks",
    "week": "weeks",
    "weeks": "weeks",
}


def parse_time(value: str) -> datetime:
    """Parse time value. Supports:
    - Relative: 5m, 1h, 2d, 30s, 1week
    - Time only: 7:55, 14:30:00 (today in UTC)
    - ISO 8601: 2024-01-15T10:30:00Z
    """
    stripped = value.strip()

    # Relative time: 5m, 1h, 2days, etc.
    match = re.match(r"^(\d+)\s*([a-z]+)$", stripped.lower())
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        if unit not in _TIME_UNITS:
            msg = f"Unknown time unit: {unit}"
            raise ValueError(msg)
        delta = timedelta(**{_TIME_UNITS[unit]: amount})
        return datetime.now(tz=UTC) - delta

    # Time only: 7:55, 14:30, 14:30:00
    time_match = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", stripped)
    if time_match:
        today = datetime.now(tz=UTC).date()
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        second = int(time_match.group(3) or 0)
        return datetime(today.year, today.month, today.day, hour, minute, second, tzinfo=UTC)

    # ISO 8601
    return datetime.fromisoformat(stripped)
