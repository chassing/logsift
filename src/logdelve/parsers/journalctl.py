"""systemd journalctl JSON output parser."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import override

from logdelve.models import ContentType, LogLevel
from logdelve.parsers.base import (
    LogParser,
    ParseResult,
    classify_content,
    extract_log_level,
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
        content_type, parsed_json = classify_content(raw)
        if content_type != ContentType.JSON or parsed_json is None:
            return None

        # Must have at least __REALTIME_TIMESTAMP or _SOURCE_REALTIME_TIMESTAMP
        ts_str = parsed_json.get("__REALTIME_TIMESTAMP") or parsed_json.get("_SOURCE_REALTIME_TIMESTAMP")
        if ts_str is None:
            return None

        # __REALTIME_TIMESTAMP is microseconds since epoch
        try:
            ts = datetime.fromtimestamp(int(ts_str) / 1_000_000, tz=UTC)
        except (ValueError, OSError):
            return None

        # Extract component from SYSLOG_IDENTIFIER or _COMM
        component = parsed_json.get("SYSLOG_IDENTIFIER") or parsed_json.get("_COMM")

        # Extract log level from PRIORITY
        log_level = None
        priority = parsed_json.get("PRIORITY")
        if priority is not None:
            log_level = _PRIORITY_MAP.get(str(priority))

        # If no level from PRIORITY, try MESSAGE text
        if log_level is None:
            message = parsed_json.get("MESSAGE", "")
            if isinstance(message, str) and message:
                log_level = extract_log_level(message, None)

        return ParseResult(
            timestamp=ts,
            content=raw,
            content_type=ContentType.JSON,
            parsed_json=parsed_json,
            log_level=log_level,
            component=component,
        )
