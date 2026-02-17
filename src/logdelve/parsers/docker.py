"""Docker Compose log format parser."""

# ruff: noqa: PLC0415
from __future__ import annotations

import re

from logdelve.parsers.base import (
    LogParser,
    ParseResult,
    classify_content,
    extract_log_level,
)

# Docker Compose: "service-name  | "
_DOCKER_COMPOSE_RE = re.compile(r"^(?P<comp>[\w.-]+)\s+\|\s+")


class DockerParser(LogParser):
    """Parses Docker Compose format: 'service-name  | <rest of line>'."""

    @property
    def name(self) -> str:
        return "docker"

    @property
    def description(self) -> str:
        return "Docker Compose (service-name | message)"

    def __init__(self) -> None:
        from logdelve.parsers.iso import IsoParser
        from logdelve.parsers.syslog import SyslogParser

        self._timestamp_parsers = [IsoParser(), SyslogParser()]

    def try_parse(self, raw: str) -> ParseResult | None:
        m = _DOCKER_COMPOSE_RE.match(raw)
        if m is None:
            return None
        component = m.group("comp")
        remainder = raw[m.end() :]

        # Try to extract timestamp from remainder using sub-parsers
        for parser in self._timestamp_parsers:
            result = parser.try_parse(remainder)
            if result is not None:
                result.component = component
                return result

        # No timestamp found, classify the remainder directly
        content_type, parsed_json = classify_content(remainder)
        log_level = extract_log_level(remainder, parsed_json)
        return ParseResult(
            timestamp=None,
            content=remainder,
            content_type=content_type,
            parsed_json=parsed_json,
            log_level=log_level,
            component=component,
        )
