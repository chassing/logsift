"""ISO 8601 and slash-date timestamp parser (generic catch-all)."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import override

from logdelve.parsers.base import (
    LogParser,
    ParseResult,
    classify_content,
    extract_component_from_json,
    extract_log_level,
)

# ISO 8601: "2024-01-15T10:30:00Z", "2024-01-15 10:30:00.123", "2024-01-15T10:30:00+02:00"
_ISO_SPACE_RE = re.compile(r"^(?P<dt>\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+")

# Simple date-time with slashes: "2024/01/15 10:30:00"
_SLASH_DATE_RE = re.compile(
    r"^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})\s+(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\s+"
)


class IsoParser(LogParser):
    """Parses lines with ISO 8601 or slash-date timestamps."""

    @property
    def name(self) -> str:
        return "iso"

    @property
    def description(self) -> str:
        return "ISO 8601 and slash-date timestamps (generic)"

    @override
    def try_parse(self, raw: str) -> ParseResult | None:
        ts, content = _try_iso(raw)
        if ts is None:
            ts, content = _try_slash_date(raw)
        if ts is None:
            return None
        content_type, parsed_json = classify_content(content)
        log_level = extract_log_level(content, parsed_json)
        component = extract_component_from_json(parsed_json)
        return ParseResult(
            timestamp=ts,
            content=content,
            content_type=content_type,
            parsed_json=parsed_json,
            log_level=log_level,
            component=component,
        )


def _try_iso(raw: str) -> tuple[datetime | None, str]:
    """Try to extract an ISO 8601 timestamp from the start of the line."""
    m = _ISO_SPACE_RE.match(raw)
    if m is None:
        return None, raw
    try:
        ts = datetime.fromisoformat(m.group("dt"))
    except ValueError:
        return None, raw
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
        tzinfo=UTC,
    )
    return ts, raw[m.end() :]
