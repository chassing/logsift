"""Log line parsing: timestamp extraction and content classification."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from logsift.models import ContentType, LogLine

# Month name mapping for syslog-style timestamps
_MONTH_MAP: dict[str, int] = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}

# Syslog: "Jan 15 10:30:00" or "Jan  5 10:30:00"
_SYSLOG_RE = re.compile(
    r"^(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(?P<day>\d{1,2})\s+(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\s+"
)

# Apache CLF: "[15/Jan/2024:10:30:00 +0000]"
_APACHE_RE = re.compile(
    r"^\[(?P<day>\d{2})/(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/(?P<year>\d{4}):(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\s+[+-]\d{4}\]\s+"
)

# ISO 8601 with space separator: "2024-01-15 10:30:00" or "2024-01-15 10:30:00.123"
_ISO_SPACE_RE = re.compile(r"^(?P<dt>\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+")

# Simple date-time with slashes: "2024/01/15 10:30:00"
_SLASH_DATE_RE = re.compile(
    r"^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})\s+(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\s+"
)


def _try_iso(raw: str) -> tuple[datetime | None, str]:
    """Try to extract an ISO 8601 timestamp from the start of the line."""
    m = _ISO_SPACE_RE.match(raw)
    if m is None:
        return None, raw
    dt_str = m.group("dt")
    try:
        ts = datetime.fromisoformat(dt_str)
    except ValueError:
        return None, raw
    return ts, raw[m.end() :]


def _try_syslog(raw: str) -> tuple[datetime | None, str]:
    """Try to extract a syslog-style timestamp."""
    m = _SYSLOG_RE.match(raw)
    if m is None:
        return None, raw
    now = datetime.now(tz=UTC)
    ts = datetime(
        year=now.year,
        month=_MONTH_MAP[m.group("month")],
        day=int(m.group("day")),
        hour=int(m.group("hour")),
        minute=int(m.group("min")),
        second=int(m.group("sec")),
    )
    return ts, raw[m.end() :]


def _try_apache(raw: str) -> tuple[datetime | None, str]:
    """Try to extract an Apache CLF timestamp."""
    m = _APACHE_RE.match(raw)
    if m is None:
        return None, raw
    ts = datetime(
        year=int(m.group("year")),
        month=_MONTH_MAP[m.group("month")],
        day=int(m.group("day")),
        hour=int(m.group("hour")),
        minute=int(m.group("min")),
        second=int(m.group("sec")),
    )
    return ts, raw[m.end() :]


def _try_slash_date(raw: str) -> tuple[datetime | None, str]:
    """Try to extract a slash-separated date-time."""
    m = _SLASH_DATE_RE.match(raw)
    if m is None:
        return None, raw
    ts = datetime(
        year=int(m.group("year")),
        month=int(m.group("month")),
        day=int(m.group("day")),
        hour=int(m.group("hour")),
        minute=int(m.group("min")),
        second=int(m.group("sec")),
    )
    return ts, raw[m.end() :]


def extract_timestamp(raw: str) -> tuple[datetime | None, str]:
    """Extract a timestamp from the start of a log line.

    Returns (timestamp, remainder) where remainder is the content
    after the timestamp. If no timestamp is found, returns (None, raw).
    """
    for parser in (_try_iso, _try_syslog, _try_apache, _try_slash_date):
        ts, remainder = parser(raw)
        if ts is not None:
            return ts, remainder
    return None, raw


def classify_content(content: str) -> tuple[ContentType, dict[str, Any] | None]:
    """Classify content as JSON or plain text.

    Returns (content_type, parsed_json). parsed_json is None for text content.
    """
    stripped = content.strip()
    if stripped.startswith("{"):
        try:
            parsed: dict[str, Any] = json.loads(stripped)
            return ContentType.JSON, parsed
        except (json.JSONDecodeError, ValueError):
            pass
    return ContentType.TEXT, None


def parse_line(line_number: int, raw: str) -> LogLine:
    """Parse a raw log line into a LogLine model."""
    timestamp, content = extract_timestamp(raw)
    content_type, parsed_json = classify_content(content)
    return LogLine(
        line_number=line_number,
        raw=raw,
        timestamp=timestamp,
        content_type=content_type,
        content=content,
        parsed_json=parsed_json,
    )
