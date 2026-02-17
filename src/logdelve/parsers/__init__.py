"""Parser registry, auto-detection, and the ParserName enum."""

# ruff: noqa: PLC0415
from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from logdelve.parsers.base import LogParser


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
