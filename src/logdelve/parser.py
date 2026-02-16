"""Log line parsing: timestamp extraction, content classification, level and component detection."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from logdelve.models import ContentType, LogLevel, LogLine

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

# Log level normalization mapping
_LEVEL_MAP: dict[str, LogLevel] = {
    "trace": LogLevel.TRACE,
    "debug": LogLevel.DEBUG,
    "dbg": LogLevel.DEBUG,
    "info": LogLevel.INFO,
    "information": LogLevel.INFO,
    "warn": LogLevel.WARN,
    "warning": LogLevel.WARN,
    "error": LogLevel.ERROR,
    "err": LogLevel.ERROR,
    "fatal": LogLevel.FATAL,
    "critical": LogLevel.FATAL,
    "crit": LogLevel.FATAL,
    "panic": LogLevel.FATAL,
    "emerg": LogLevel.FATAL,
}

# JSON field names to check for log level (in priority order)
_LEVEL_JSON_KEYS = ("log_level", "level", "severity", "loglevel", "lvl")

# Text patterns for log level detection (after timestamp)
_LEVEL_BRACKET_RE = re.compile(
    r"\[(?P<level>TRACE|DEBUG|DBG|INFO|WARN|WARNING|ERROR|ERR|FATAL|CRITICAL|CRIT|PANIC|EMERG)\]",
    re.IGNORECASE,
)
_LEVEL_WORD_RE = re.compile(
    r"(?:^|\s)(?P<level>TRACE|DEBUG|DBG|INFO|WARN|WARNING|ERROR|ERR|FATAL|CRITICAL)\s",
    re.IGNORECASE,
)
_LEVEL_KV_RE = re.compile(r"(?:level|severity)=(?P<level>\w+)", re.IGNORECASE)

# JSON field names to check for component
_COMPONENT_JSON_KEYS = ("service", "component", "app", "source", "container", "pod")

# Kubernetes pod prefix: "[pod-name-abc123]" or "pod-name container"
_K8S_BRACKET_RE = re.compile(r"^\[(?P<comp>[a-z0-9][\w.-]+)\]\s*")
_K8S_PREFIX_RE = re.compile(r"^(?P<comp>[a-z0-9][\w.-]+)\s+(?P<cont>[a-z0-9][\w.-]+)\s+\d{4}-")

# Docker Compose: "service-name  | "
_DOCKER_COMPOSE_RE = re.compile(r"^(?P<comp>[\w.-]+)\s+\|\s+")


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


def extract_log_level(content: str, parsed_json: dict[str, Any] | None) -> LogLevel | None:
    """Extract log level from content or JSON data.

    Checks JSON fields first, then text patterns.
    """
    # Check JSON fields
    if parsed_json is not None:
        for key in _LEVEL_JSON_KEYS:
            if key in parsed_json:
                value = str(parsed_json[key]).lower().strip()
                if value in _LEVEL_MAP:
                    return _LEVEL_MAP[value]

    # Check text patterns: [LEVEL], LEVEL, level=value
    for pattern in (_LEVEL_BRACKET_RE, _LEVEL_KV_RE, _LEVEL_WORD_RE):
        m = pattern.search(content)
        if m:
            value = m.group("level").lower().strip()
            if value in _LEVEL_MAP:
                return _LEVEL_MAP[value]

    return None


def _strip_component_prefix(raw: str) -> tuple[str | None, str]:
    """Strip a component prefix from the line and return (component, remainder).

    Handles [name], docker compose, and k8s formats.
    Returns (None, raw) if no prefix found.
    """
    # Docker Compose: "service-name  | ..."
    m = _DOCKER_COMPOSE_RE.match(raw)
    if m:
        return m.group("comp"), raw[m.end() :]

    # Kubernetes/CloudWatch bracket: "[pod-name] ..."
    m = _K8S_BRACKET_RE.match(raw)
    if m:
        return m.group("comp"), raw[m.end() :]

    # Kubernetes prefix: "pod-name container 2024-..."
    m = _K8S_PREFIX_RE.match(raw)
    if m:
        return m.group("comp"), raw[m.start("cont") :]

    return None, raw


def extract_component(raw: str, parsed_json: dict[str, Any] | None) -> str | None:
    """Extract component/service name from the raw line or JSON data.

    Checks for Kubernetes, Docker Compose prefixes, then JSON fields.
    """
    comp, _ = _strip_component_prefix(raw)
    if comp is not None:
        return comp

    # JSON fields
    if parsed_json is not None:
        for key in _COMPONENT_JSON_KEYS:
            if key in parsed_json and isinstance(parsed_json[key], str):
                return str(parsed_json[key])

    return None


def parse_line(line_number: int, raw: str) -> LogLine:
    """Parse a raw log line into a LogLine model."""
    # Strip component prefix before timestamp extraction so
    # "[stream] 2024-01-15T..." correctly finds the timestamp
    prefix_component, remainder = _strip_component_prefix(raw)
    timestamp, content = extract_timestamp(remainder)
    content_type, parsed_json = classify_content(content)
    log_level = extract_log_level(content, parsed_json)
    # Use prefix component, or try JSON fields
    component = prefix_component
    if component is None:
        component = extract_component(raw, parsed_json)
    return LogLine(
        line_number=line_number,
        raw=raw,
        timestamp=timestamp,
        content_type=content_type,
        content=content,
        parsed_json=parsed_json,
        log_level=log_level,
        component=component,
    )
