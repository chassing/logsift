"""logfmt key=value structured log parser."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from logdelve.models import ContentType
from logdelve.parsers.base import (
    LEVEL_MAP,
    LogParser,
    ParseResult,
)

# Match key=value or key="quoted value" pairs
_LOGFMT_PAIR_RE = re.compile(r'(?P<key>[\w.]+)=(?:"(?P<qval>[^"]*)"|(?P<val>\S*))')

# Keys that contain the timestamp
_TIME_KEYS = ("time", "ts", "timestamp", "t", "datetime")

# Keys that contain the log level
_LEVEL_KEYS = ("level", "lvl", "severity", "loglevel", "log_level")

# Keys that contain the message
_MSG_KEYS = ("msg", "message", "error", "err")

# Keys that contain the component
_COMP_KEYS = ("service", "component", "app", "source", "caller", "logger", "name")

_MIN_LOGFMT_PAIRS = 2
_EPOCH_MS_THRESHOLD = 1e12


class LogfmtParser(LogParser):
    """Parses logfmt structured logs (key=value pairs).

    Example: time=2024-01-15T10:30:00Z level=info msg="request handled" service=api
    """

    @property
    def name(self) -> str:
        return "logfmt"

    @property
    def description(self) -> str:
        return "logfmt key=value structured logs"

    def try_parse(self, raw: str) -> ParseResult | None:  # noqa: C901, PLR0912
        pairs = _LOGFMT_PAIR_RE.findall(raw)
        # Need at least 2 key=value pairs to be considered logfmt
        if len(pairs) < _MIN_LOGFMT_PAIRS:
            return None

        # Build a dict from parsed pairs
        data: dict[str, str] = {}
        for key, qval, val in pairs:
            data[key] = qval or val

        # Must have a time-like key to be recognized as logfmt
        timestamp = None
        for tk in _TIME_KEYS:
            if tk in data:
                timestamp = self._parse_timestamp(data[tk])
                if timestamp is not None:
                    break

        # If no timestamp key found at all, this is not logfmt we can handle
        if not any(tk in data for tk in _TIME_KEYS):
            return None

        # Extract level
        log_level = None
        for lk in _LEVEL_KEYS:
            if lk in data:
                log_level = LEVEL_MAP.get(data[lk].lower())
                if log_level is not None:
                    break

        # Extract message
        content = ""
        for mk in _MSG_KEYS:
            if mk in data:
                content = data[mk]
                break
        if not content:
            content = raw

        # Extract component
        component = None
        for ck in _COMP_KEYS:
            if ck in data:
                component = data[ck]
                break

        return ParseResult(
            timestamp=timestamp,
            content=content,
            content_type=ContentType.TEXT,
            parsed_json=None,
            log_level=log_level,
            component=component,
        )

    @staticmethod
    def _parse_timestamp(value: str) -> datetime | None:
        """Parse a timestamp value from a logfmt field."""
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
        # Try epoch seconds/milliseconds
        try:
            num = float(value)
            if num > _EPOCH_MS_THRESHOLD:
                # Milliseconds
                return datetime.fromtimestamp(num / 1000, tz=UTC)
            return datetime.fromtimestamp(num, tz=UTC)
        except (ValueError, OSError):
            pass
        return None
