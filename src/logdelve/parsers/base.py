"""Base parser interface and shared parsing utilities."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime

from logdelve.models import ContentType, LogLevel, LogLine

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

# Text patterns for log level detection
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


@dataclass(slots=True)
class ParseResult:
    """Intermediate result from a parser's parse attempt."""

    timestamp: datetime | None
    content: str
    content_type: ContentType
    parsed_json: dict[str, Any] | None = None
    log_level: LogLevel | None = None
    component: str | None = None


class LogParser(ABC):
    """Abstract base class for log format parsers.

    Each parser handles one log format family. It is responsible for
    detecting whether a line matches its format and extracting all
    structured fields.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for this parser (e.g., 'syslog')."""

    @property
    @abstractmethod
    def description(self) -> str:
        """One-line description shown in CLI help."""

    @abstractmethod
    def try_parse(self, raw: str) -> ParseResult | None:
        """Attempt to parse a raw log line.

        Returns a ParseResult if this parser can handle the line,
        or None if the line does not match this format.
        """

    def parse_line(self, line_number: int, raw: str) -> LogLine:
        """Parse a raw log line into a LogLine model.

        Calls try_parse() and falls back to a bare LogLine if it returns None.
        """
        result = self.try_parse(raw)
        if result is None:
            content_type, parsed_json = classify_content(raw)
            log_level = extract_log_level(raw, parsed_json)
            return LogLine(
                line_number=line_number,
                raw=raw,
                timestamp=None,
                content_type=content_type,
                content=raw,
                parsed_json=parsed_json,
                log_level=log_level,
                component=None,
            )
        # Default to INFO for lines with a timestamp but no detected level
        if result.log_level is None and result.timestamp is not None:
            result.log_level = LogLevel.INFO
        return LogLine(
            line_number=line_number,
            raw=raw,
            timestamp=result.timestamp,
            content_type=result.content_type,
            content=result.content,
            parsed_json=result.parsed_json,
            log_level=result.log_level,
            component=result.component,
        )


# ---- Shared utilities used by all plugins ----


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

    Checks JSON fields first, then text patterns, then heuristics.
    """
    # Check JSON fields
    if parsed_json is not None:
        for key in _LEVEL_JSON_KEYS:
            if key in parsed_json:
                value = str(parsed_json[key]).lower().strip()
                if value in _LEVEL_MAP:
                    return _LEVEL_MAP[value]

    # Check text patterns: [LEVEL], level=value, LEVEL word
    for pattern in (_LEVEL_BRACKET_RE, _LEVEL_KV_RE, _LEVEL_WORD_RE):
        m = pattern.search(content)
        if m:
            value = m.group("level").lower().strip()
            if value in _LEVEL_MAP:
                return _LEVEL_MAP[value]

    # Content-based heuristic for lines without explicit level
    lower = content.lower()
    if any(kw in lower for kw in ("fail", "refused", "denied", "timeout", "abort", "segfault", "panic")):
        return LogLevel.ERROR
    if any(kw in lower for kw in ("deprecated", "warning:", "warn:", "cannot", "unable")):
        return LogLevel.WARN

    return None


def extract_component_from_json(parsed_json: dict[str, Any] | None) -> str | None:
    """Extract component name from JSON fields."""
    if parsed_json is not None:
        for key in _COMPONENT_JSON_KEYS:
            if key in parsed_json and isinstance(parsed_json[key], str):
                return str(parsed_json[key])
    return None
