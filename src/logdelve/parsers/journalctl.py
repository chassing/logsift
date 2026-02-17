"""systemd journalctl JSON output parser."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, override

from logdelve.models import ContentType, LogLevel
from logdelve.parsers.base import (
    LogParser,
    ParseResult,
)

# journalctl PRIORITY field mapping (syslog severity levels)
_PRIORITY_MAP: dict[str, LogLevel] = {
    "0": LogLevel.FATAL,  # emerg
    "1": LogLevel.FATAL,  # alert
    "2": LogLevel.FATAL,  # crit
    "3": LogLevel.ERROR,  # err
    "4": LogLevel.WARN,  # warning
    "5": LogLevel.INFO,  # notice
    "6": LogLevel.INFO,  # info
    "7": LogLevel.DEBUG,  # debug
}


class JournalctlParser(LogParser):
    """Parses journalctl -o json output.

    Each line is a JSON object with well-known systemd fields:
    __REALTIME_TIMESTAMP, _HOSTNAME, SYSLOG_IDENTIFIER, PRIORITY, MESSAGE.
    """

    @property
    def name(self) -> str:
        return "journalctl"

    @property
    def description(self) -> str:
        return "systemd journalctl JSON output (journalctl -o json)"

    @override
    def try_parse(self, raw: str) -> ParseResult | None:
        stripped = raw.strip()
        if not stripped.startswith("{"):
            return None
        try:
            data: dict[str, Any] = json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            return None

        # Must have at least __REALTIME_TIMESTAMP or _SOURCE_REALTIME_TIMESTAMP
        ts_str = data.get("__REALTIME_TIMESTAMP") or data.get("_SOURCE_REALTIME_TIMESTAMP")
        if ts_str is None:
            return None

        # __REALTIME_TIMESTAMP is microseconds since epoch
        try:
            ts = datetime.fromtimestamp(int(ts_str) / 1_000_000, tz=UTC)
        except (ValueError, OSError):
            return None

        message = data.get("MESSAGE", "")
        if isinstance(message, list):
            # journalctl sometimes returns MESSAGE as list of byte values
            message = str(message)

        # Extract component from SYSLOG_IDENTIFIER or _COMM
        component = data.get("SYSLOG_IDENTIFIER") or data.get("_COMM")

        # Extract log level from PRIORITY
        log_level = None
        priority = data.get("PRIORITY")
        if priority is not None:
            log_level = _PRIORITY_MAP.get(str(priority))

        # If no level from PRIORITY, try common level fields in MESSAGE
        if log_level is None and message:
            from logdelve.parsers.base import extract_log_level  # noqa: PLC0415

            log_level = extract_log_level(message, None)

        return ParseResult(
            timestamp=ts,
            content=message,
            content_type=ContentType.JSON,
            parsed_json=data,
            log_level=log_level,
            component=component,
        )
