"""Apache/Nginx CLF (Common Log Format) parser."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import override

from logdelve.parsers.base import (
    MONTH_MAP,
    LogParser,
    ParseResult,
    classify_content,
    extract_log_level,
)

# Apache CLF: "[15/Jan/2024:10:30:00 +0000]"
_APACHE_RE = re.compile(
    r"^\[(?P<day>\d{2})/(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/"
    r"(?P<year>\d{4}):(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\s+[+-]\d{4}\]\s+"
)


class ApacheParser(LogParser):
    """Parses Apache/Nginx Common Log Format timestamps."""

    @property
    def name(self) -> str:
        return "apache"

    @property
    def description(self) -> str:
        return "Apache/Nginx CLF ([DD/Mon/YYYY:HH:MM:SS +0000])"

    @override
    def try_parse(self, raw: str) -> ParseResult | None:
        m = _APACHE_RE.match(raw)
        if m is None:
            return None
        ts = datetime(
            year=int(m.group("year")),
            month=MONTH_MAP[m.group("month")],
            day=int(m.group("day")),
            hour=int(m.group("hour")),
            minute=int(m.group("min")),
            second=int(m.group("sec")),
            tzinfo=UTC,
        )
        content = raw[m.end() :]
        content_type, parsed_json = classify_content(content)
        log_level = extract_log_level(content, parsed_json)
        return ParseResult(
            timestamp=ts,
            content=content,
            content_type=content_type,
            parsed_json=parsed_json,
            log_level=log_level,
            component=None,
        )
