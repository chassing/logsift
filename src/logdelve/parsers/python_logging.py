"""Python stdlib logging format parser."""

from __future__ import annotations

import re
from datetime import datetime
from typing import override

from logdelve.parsers.base import (
    _LEVEL_MAP,
    LogParser,
    ParseResult,
    classify_content,
    extract_log_level,
)

# Python logging default format: "2024-01-15 10:30:00,123 - name - LEVEL - message"
# Also matches: "2024-01-15 10:30:00,123 name LEVEL message" (without separators)
_PYTHON_LOG_RE = re.compile(
    r"^(?P<dt>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}),(?P<ms>\d{3})\s+"
    r"(?:-\s+)?(?P<name>[\w.]+)\s+"
    r"(?:-\s+)?(?P<level>[A-Z]+)\s+"
    r"(?:-\s+)?(?P<msg>.*)$"
)


class PythonLoggingParser(LogParser):
    """Parses Python stdlib logging default format.

    Format: '2024-01-15 10:30:00,123 - name - LEVEL - message'
    The comma before milliseconds distinguishes this from generic ISO.
    """

    @property
    def name(self) -> str:
        return "python"

    @property
    def description(self) -> str:
        return "Python logging (YYYY-MM-DD HH:MM:SS,ms - name - LEVEL - msg)"

    @override
    def try_parse(self, raw: str) -> ParseResult | None:
        m = _PYTHON_LOG_RE.match(raw)
        if m is None:
            return None
        try:
            ts = datetime.fromisoformat(m.group("dt"))
            # Add milliseconds
            ms = int(m.group("ms"))
            ts = ts.replace(microsecond=ms * 1000)
        except ValueError:
            return None

        level_str = m.group("level").lower()
        log_level = _LEVEL_MAP.get(level_str)
        component = m.group("name")
        content = m.group("msg")

        content_type, parsed_json = classify_content(content)
        # If content has its own level info, prefer the explicit one from the format
        if log_level is None:
            log_level = extract_log_level(content, parsed_json)

        return ParseResult(
            timestamp=ts,
            content=content,
            content_type=content_type,
            parsed_json=parsed_json,
            log_level=log_level,
            component=component,
        )
