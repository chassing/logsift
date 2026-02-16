"""Shared utilities for logdelve."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import dateparser

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
    - Relative shorthand: 5m, 1h, 2d, 30s, 1week
    - Natural language: "last friday", "2 days ago", "yesterday 7:58"
    - Time only: 7:55, 14:30:00 (today in UTC)
    - ISO 8601: 2024-01-15T10:30:00Z
    - Flexible dates: "2026-02-13 7:58", "Feb 13 2026"
    """
    stripped = value.strip()

    # Relative time shorthand: 5m, 1h, 2days, etc.
    match = re.match(r"^(\d+)\s*([a-z]+)$", stripped.lower())
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        if unit in _TIME_UNITS:
            delta = timedelta(**{_TIME_UNITS[unit]: amount})
            return datetime.now(tz=UTC) - delta

    # dateparser handles everything else: ISO, natural language, relative, etc.
    result = dateparser.parse(
        stripped,
        settings={
            "TIMEZONE": "UTC",
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "past",
        },
    )
    if result is not None:
        return result

    msg = f"Cannot parse time: {value!r}"
    raise ValueError(msg)
