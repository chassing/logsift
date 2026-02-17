"""Base parser interface, shared utilities, and parser registry."""

# ruff: noqa: PLC0415
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

from logdelve.models import ContentType, LogLevel, LogLine

# Log level normalization mapping
LEVEL_MAP: dict[str, LogLevel] = {
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

# Month name to number mapping (shared by apache and syslog parsers)
MONTH_MAP: dict[str, int] = {
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
                if value in LEVEL_MAP:
                    return LEVEL_MAP[value]

    # Check text patterns: [LEVEL], level=value, LEVEL word
    for pattern in (_LEVEL_BRACKET_RE, _LEVEL_KV_RE, _LEVEL_WORD_RE):
        m = pattern.search(content)
        if m:
            value = m.group("level").lower().strip()
            if value in LEVEL_MAP:
                return LEVEL_MAP[value]

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


# ---- Parser registry and auto-detection ----


class ParserName(StrEnum):
    """Available parser names for CLI selection."""

    AUTO = "auto"
    ISO = "iso"
    SYSLOG = "syslog"
    APACHE = "apache"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    JOURNALCTL = "journalctl"
    PYTHON = "python"
    LOGFMT = "logfmt"


def _build_registry() -> dict[ParserName, type[LogParser]]:
    """Build the parser registry."""
    from logdelve.parsers.apache import ApacheParser
    from logdelve.parsers.auto import AutoParser
    from logdelve.parsers.docker import DockerParser
    from logdelve.parsers.iso import IsoParser
    from logdelve.parsers.journalctl import JournalctlParser
    from logdelve.parsers.kubernetes import KubernetesParser
    from logdelve.parsers.logfmt import LogfmtParser
    from logdelve.parsers.python_logging import PythonLoggingParser
    from logdelve.parsers.syslog import SyslogParser

    return {
        ParserName.AUTO: AutoParser,
        ParserName.ISO: IsoParser,
        ParserName.SYSLOG: SyslogParser,
        ParserName.APACHE: ApacheParser,
        ParserName.DOCKER: DockerParser,
        ParserName.KUBERNETES: KubernetesParser,
        ParserName.JOURNALCTL: JournalctlParser,
        ParserName.PYTHON: PythonLoggingParser,
        ParserName.LOGFMT: LogfmtParser,
    }


_registry: dict[ParserName, type[LogParser]] | None = None


def _get_registry() -> dict[ParserName, type[LogParser]]:
    global _registry  # noqa: PLW0603
    if _registry is None:
        _registry = _build_registry()
    return _registry


def get_parser(name: ParserName = ParserName.AUTO) -> LogParser:
    """Get a parser instance by name."""
    registry = _get_registry()
    return registry[name]()


# Auto-detection priority: most specific formats first
_DETECTION_ORDER: tuple[ParserName, ...] = (
    ParserName.DOCKER,
    ParserName.KUBERNETES,
    ParserName.JOURNALCTL,
    ParserName.PYTHON,
    ParserName.APACHE,
    ParserName.SYSLOG,
    ParserName.LOGFMT,
    ParserName.ISO,
)


def detect_parser(sample_lines: Sequence[str], sample_size: int = 20) -> LogParser:
    """Auto-detect the best parser by sampling lines.

    Tries each parser against the sample. The parser that successfully
    parses the most lines wins, provided it exceeds 50% match rate.
    Falls back to AutoParser for mixed-format files.
    """
    registry = _get_registry()
    lines = [line for line in sample_lines[:sample_size] if line.strip()]
    if not lines:
        return get_parser(ParserName.AUTO)

    best_name = ParserName.AUTO
    best_score = 0

    for parser_name in _DETECTION_ORDER:
        parser = registry[parser_name]()
        score = sum(1 for line in lines if parser.try_parse(line) is not None)
        if score > best_score:
            best_score = score
            best_name = parser_name

    # Require >50% match rate to commit to a specific parser
    if best_score > len(lines) // 2:
        return registry[best_name]()

    return get_parser(ParserName.AUTO)
