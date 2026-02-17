"""Auto parser - tries all format-specific parsers per line."""

from __future__ import annotations

from logdelve.parsers.base import LogParser, ParseResult


class AutoParser(LogParser):
    """Tries all parsers in sequence per line. Equivalent to original parser.py behavior."""

    @property
    def name(self) -> str:
        return "auto"

    @property
    def description(self) -> str:
        return "Auto-detect format per line (default)"

    def __init__(self) -> None:
        from logdelve.parsers.apache import ApacheParser
        from logdelve.parsers.docker import DockerParser
        from logdelve.parsers.iso import IsoParser
        from logdelve.parsers.journalctl import JournalctlParser
        from logdelve.parsers.kubernetes import KubernetesParser
        from logdelve.parsers.logfmt import LogfmtParser
        from logdelve.parsers.python_logging import PythonLoggingParser
        from logdelve.parsers.syslog import SyslogParser

        self._parsers: list[LogParser] = [
            DockerParser(),
            KubernetesParser(),
            JournalctlParser(),
            PythonLoggingParser(),
            ApacheParser(),
            SyslogParser(),
            LogfmtParser(),
            IsoParser(),
        ]

    def try_parse(self, raw: str) -> ParseResult | None:
        """Try each parser in order, return first success."""
        for parser in self._parsers:
            result = parser.try_parse(raw)
            if result is not None:
                return result
        return None
