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


_TIME_ONLY_RE = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")


def parse_time(value: str, reference_date: datetime | None = None) -> datetime:
    """Parse time value.

    Supports:
    - Relative shorthand: 5m, 1h, 2d, 30s, 1week
    - Natural language: "last friday", "2 days ago", "yesterday 7:58"
    - Time only: 7:55, 14:30:00 (uses reference_date if provided, otherwise today)
    - ISO 8601: 2024-01-15T10:30:00Z
    - Flexible dates: "2026-02-13 7:58", "Feb 13 2026"

    Args:
        value: Time string to parse.
        reference_date: Date to use for time-only input (e.g., "14:30").
            If None, uses today. Useful when navigating log files from a specific date.
    """
    stripped = value.strip()

    # Relative time shorthand: 5m, 1h, 2days, etc.
    match = re.match(r"^(\d+)\s*([a-z]+)$", stripped.lower())
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        if unit in _TIME_UNITS:
            delta = timedelta(**{_TIME_UNITS[unit]: amount})
            ref = reference_date or datetime.now(tz=UTC)
            return ref - delta

    # Time-only input with reference date
    if reference_date is not None and _TIME_ONLY_RE.match(stripped):
        parts = stripped.split(":")
        hour, minute = int(parts[0]), int(parts[1])
        second = int(parts[2]) if len(parts) >= 3 else 0  # noqa: PLR2004
        return reference_date.replace(hour=hour, minute=minute, second=second, microsecond=0)

    # dateparser handles everything else: ISO, natural language, relative, etc.
    settings: dict[str, object] = {
        "TIMEZONE": "UTC",
        "RETURN_AS_TIMEZONE_AWARE": True,
        "PREFER_DATES_FROM": "past",
    }
    if reference_date is not None:
        settings["RELATIVE_BASE"] = reference_date.replace(tzinfo=None)

    result = dateparser.parse(stripped, settings=settings)
    if result is not None:
        return result

    msg = f"Cannot parse time: {value!r}"
    raise ValueError(msg)
