"""Syslog RFC 3164 parser."""

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

_SYSLOG_RE = re.compile(
    r"^(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(?P<day>\d{1,2})\s+"
    r"(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\s+"
)

# Syslog content: "hostname program[pid]: message"
_SYSLOG_HOST_RE = re.compile(r"^(?P<host>[a-zA-Z][\w.-]+)\s+(?P<prog>[\w./-]+?)(?:\[(?P<pid>\d+)\])?:\s+")


class SyslogParser(LogParser):
    """Parses syslog RFC 3164 format: 'Mon DD HH:MM:SS hostname program[pid]: message'."""

    @property
    def name(self) -> str:
        return "syslog"

    @property
    def description(self) -> str:
        return "Syslog RFC 3164 (Mon DD HH:MM:SS hostname program: msg)"

    @override
    def try_parse(self, raw: str) -> ParseResult | None:
        m = _SYSLOG_RE.match(raw)
        if m is None:
            return None
        now = datetime.now(tz=UTC)
        ts = datetime(
            year=now.year,
            month=MONTH_MAP[m.group("month")],
            day=int(m.group("day")),
            hour=int(m.group("hour")),
            minute=int(m.group("min")),
            second=int(m.group("sec")),
            tzinfo=UTC,
        )
        content = raw[m.end() :]
        # Extract hostname + program[pid] and use program as component
        component = None
        m_host = _SYSLOG_HOST_RE.match(content)
        if m_host:
            prog = m_host.group("prog")
            pid = m_host.group("pid")
            component = f"{prog}[{pid}]" if pid else prog
            content = content[m_host.end() :]
        content_type, parsed_json = classify_content(content)
        log_level = extract_log_level(content, parsed_json)
        return ParseResult(
            timestamp=ts,
            content=content,
            content_type=content_type,
            parsed_json=parsed_json,
            log_level=log_level,
            component=component,
        )
