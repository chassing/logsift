"""Log line parsing: backward-compatible entry point.

This module delegates to the parsers package. Direct imports of
parse_line, classify_content, extract_timestamp, extract_log_level,
and extract_component continue to work unchanged.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from logdelve.models import LogLine
from logdelve.parsers.base import LogParser
from logdelve.parsers.base import classify_content as classify_content
from logdelve.parsers.base import extract_log_level as extract_log_level

# ---- Timestamp extraction (kept for backward compat) ----

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

_ISO_SPACE_RE = re.compile(r"^(?P<dt>\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+")
_SYSLOG_RE = re.compile(
    r"^(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(?P<day>\d{1,2})\s+"
    r"(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\s+"
)
_APACHE_RE = re.compile(
    r"^\[(?P<day>\d{2})/(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/"
    r"(?P<year>\d{4}):(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\s+[+-]\d{4}\]\s+"
)
_SLASH_DATE_RE = re.compile(
    r"^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})\s+(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\s+"
)

# Component prefix patterns
_DOCKER_COMPOSE_RE = re.compile(r"^(?P<comp>[\w.-]+)\s+\|\s+")
_K8S_BRACKET_RE = re.compile(r"^\[(?P<comp>[a-z0-9][\w.-]+)\]\s*")
_K8S_PREFIX_RE = re.compile(r"^(?P<comp>[a-z0-9][\w.-]+)\s+(?P<cont>[a-z0-9][\w.-]+)\s+\d{4}-")
_COMPONENT_JSON_KEYS = ("service", "component", "app", "source", "container", "pod")


def _try_iso(raw: str) -> tuple[datetime | None, str]:
    m = _ISO_SPACE_RE.match(raw)
    if m is None:
        return None, raw
    try:
        ts = datetime.fromisoformat(m.group("dt"))
    except ValueError:
        return None, raw
    return ts, raw[m.end() :]


def _try_syslog(raw: str) -> tuple[datetime | None, str]:
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


def _strip_component_prefix(raw: str) -> tuple[str | None, str]:
    """Strip a component prefix from the line and return (component, remainder)."""
    m = _DOCKER_COMPOSE_RE.match(raw)
    if m:
        return m.group("comp"), raw[m.end() :]
    m = _K8S_BRACKET_RE.match(raw)
    if m:
        return m.group("comp"), raw[m.end() :]
    m = _K8S_PREFIX_RE.match(raw)
    if m:
        return m.group("comp"), raw[m.start("cont") :]
    return None, raw


def extract_component(raw: str, parsed_json: dict[str, Any] | None) -> str | None:
    """Extract component/service name from the raw line or JSON data."""
    comp, _ = _strip_component_prefix(raw)
    if comp is not None:
        return comp
    if parsed_json is not None:
        for key in _COMPONENT_JSON_KEYS:
            if key in parsed_json and isinstance(parsed_json[key], str):
                return str(parsed_json[key])
    return None


def parse_line(line_number: int, raw: str) -> LogLine:
    """Parse a raw log line into a LogLine model.

    Delegates to the AutoParser from the parsers package.
    """
    return _get_default_parser().parse_line(line_number, raw)


_default_parser = None


def _get_default_parser() -> LogParser:
    """Lazy-load the default AutoParser."""
    global _default_parser
    if _default_parser is None:
        from logdelve.parsers import ParserName, get_parser

        _default_parser = get_parser(ParserName.AUTO)
    return _default_parser
